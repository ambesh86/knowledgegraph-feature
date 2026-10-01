"""Plain-English rationale — the only place an LLM is permitted, and it is fenced.

The use case asks for "a plain-English rationale" and for recommendations BD leaders
can interrogate. Those two requirements pull in opposite directions if an LLM is given
any real authority: prose is what a language model is good at, and a defensible
ranking is what it is bad at.

So the split is absolute:

    scoring.py   decides.  Deterministic, reproducible, unit-tested.
    rationale.py explains. Never decides, never computes, never ranks.

The model receives a score that already exists and a factor breakdown that already
exists, and is asked to write one paragraph about them. It cannot change the score, it
cannot reorder anything, and — enforced by `verify`, not by prompt instruction — any
output containing a number that was not in its input is discarded in favour of the
deterministic template.

That last guard matters more than it looks. The characteristic LLM failure here is not
refusing or rambling; it is writing "a 12-month readout showed 78% efficacy" about a
trial whose payload said neither thing. A fabricated statistic inside a confident BD
briefing is the single most expensive output this system could produce, and no amount
of prompt engineering reliably prevents it. Checking the digits does.

When no provider is configured — the common case, since this account's Bedrock access
is limited to Amazon Nova — the template path runs and the UI labels it as such.
"""
from __future__ import annotations

import logging
import os
import re

from scout.models import RationaleKind, ScoreResult, SignalType

logger = logging.getLogger(__name__)

_MAX_WORDS = 90

# Digit runs, with thousands separators and decimals. Percentages, counts, years and
# dose figures all reduce to this.
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

_SYSTEM = (
    "You are a biotech business-development analyst writing one short paragraph for a "
    "partnership briefing. You are given a signal and a scoring breakdown that has "
    "ALREADY been computed. Explain, in plain English, why this signal scored as it "
    "did and what it means for partnership interest.\n"
    "Hard rules:\n"
    "1. Use ONLY the facts provided. Introduce no company, drug, date, phase or "
    "statistic that is not in the input.\n"
    "2. Do not invent numbers. Do not estimate. Do not compute anything.\n"
    "3. Do not restate the score as a recommendation to act; the analyst decides.\n"
    "4. Two or three sentences, under 90 words, no bullet points, no preamble."
)


def build(
    *,
    title: str,
    summary: str,
    signal_type: SignalType,
    area_label: str,
    company: str | None,
    stage: str | None,
    published: str | None,
    result: ScoreResult,
    source_names: list[str],
) -> tuple[str, RationaleKind]:
    """Return (prose, provenance). Never raises — a rationale is a nice-to-have, and
    a scan must not fail because a language model was unavailable."""
    facts = _facts(
        title=title,
        summary=summary,
        signal_type=signal_type,
        area_label=area_label,
        company=company,
        stage=stage,
        published=published,
        result=result,
        source_names=source_names,
    )
    template = _template(
        signal_type=signal_type,
        area_label=area_label,
        company=company,
        stage=stage,
        result=result,
        source_names=source_names,
    )

    if not llm_enabled():
        return template, RationaleKind.TEMPLATE

    try:
        generated = _generate(facts)
    except Exception as e:  # noqa: BLE001 - degrading to the template is always valid
        logger.warning(f"rationale generation failed, using template: {type(e).__name__}: {e}")
        return template, RationaleKind.TEMPLATE

    if not generated:
        return template, RationaleKind.TEMPLATE

    ok, reason = verify(generated, facts)
    if not ok:
        logger.warning(f"rejected generated rationale ({reason}); using template")
        return template, RationaleKind.TEMPLATE

    return generated, RationaleKind.LLM


# ---------------------------------------------------------------------------
# Deterministic template — always available, always correct
# ---------------------------------------------------------------------------


def _template(
    *,
    signal_type: SignalType,
    area_label: str,
    company: str | None,
    stage: str | None,
    result: ScoreResult,
    source_names: list[str],
) -> str:
    """Compose prose mechanically from the score breakdown.

    Not a placeholder. This is the default path and it is genuinely informative: it
    names the two factors that contributed most, which is the question an analyst
    challenging a score actually asks.
    """
    ranked = sorted(result.factors, key=lambda f: f.contribution, reverse=True)
    top = [f for f in ranked if f.contribution > 0][:2]

    subject = company or f"This {signal_type.value.lower()}"
    lead = f"{subject} scored {result.score:.0f}/100 ({result.priority.value}) in {area_label}."

    reasons: list[str] = []
    for factor in top:
        reasons.append(_explain_factor(factor.name, factor.inputs))
    body = " ".join(reasons) if reasons else "No individual factor contributed strongly."

    if stage:
        body += f" Stage recorded as {stage}."

    corroboration = ""
    if len(source_names) > 1:
        corroboration = f" Corroborated across {len(source_names)} sources ({', '.join(source_names)})."
    elif source_names:
        corroboration = f" Single source: {source_names[0]}."

    return f"{lead} {body}{corroboration}".strip()


def _explain_factor(name: str, inputs: dict[str, object]) -> str:
    """One clause per factor, phrased for a reader who has not seen the weights."""
    if name == "area_fit":
        matched = inputs.get("matched") or []
        if isinstance(matched, list) and matched:
            return f"Matched {len(matched)} area terms ({', '.join(str(m) for m in matched[:4])})."
        return "Weak topical match to the area."
    if name == "stage_fit":
        return f"Development stage {inputs.get('stage')} is well aligned with partnership timing."
    if name == "recency":
        return f"Published {inputs.get('age_days')} days ago, inside the {inputs.get('window_days')}-day window."
    if name == "modality_fit":
        matched = inputs.get("matched") or []
        if isinstance(matched, list) and matched:
            return f"Modality overlaps CSL capability ({', '.join(str(m) for m in matched[:3])})."
        return "No direct modality overlap with CSL capability."
    if name == "corroboration":
        return f"Reported by {inputs.get('source_count')} independent source(s)."
    if name == "company_context":
        return (
            "Company is already tracked with prior activity."
            if inputs.get("known")
            else "Company is new to the watchlist."
        )
    return f"{name} contributed."


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


def llm_configured() -> bool:
    """Whether a generation attempt will actually be made.

    Public because `review.py` needs to distinguish "the template was used because
    the model's output was rejected" from "the template was used because there is no
    model". Only the first is a confidence signal worth flagging.
    """
    return llm_enabled()


def llm_enabled() -> bool:
    if os.environ.get("SCOUT_LLM_ENABLED", "true").lower() != "true":
        return False
    # Mirrors the provider detection in agents/eugene-agent-ws/src/query/conf/conf.py
    # so the two services agree on what "configured" means.
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    if provider in ("bedrock", "aws"):
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _facts(**kw: object) -> dict[str, object]:
    """The complete, closed set of facts the model may use. `verify` checks the
    output against exactly this, so anything omitted here is treated as fabricated."""
    result: ScoreResult = kw["result"]  # type: ignore[assignment]
    return {
        "title": kw["title"],
        "summary": kw["summary"],
        "type": kw["signal_type"].value,  # type: ignore[union-attr]
        "area": kw["area_label"],
        "company": kw["company"] or "not attributed",
        "stage": kw["stage"] or "not applicable",
        "published": kw["published"] or "unknown",
        "score": f"{result.score:.0f}",
        "priority": result.priority.value,
        "sources": ", ".join(kw["source_names"]),  # type: ignore[arg-type]
        "factors": [
            {
                "name": f.name,
                "value": f"{f.value:.2f}",
                "weight": f"{f.weight:.2f}",
                "inputs": f.inputs,
            }
            for f in result.factors
        ],
    }


def dispatch(prompt: str) -> str:
    """Send a raw prompt to whichever provider is configured.

    Split out of `_generate` so a second caller — the Use Case 2 executive summary,
    which needs its own prompt but the same provider selection — cannot drift from
    this one about what "configured" means. Imports inside the provider functions are
    local so a missing SDK degrades to a template rather than breaking startup.
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower()

    if provider in ("bedrock", "aws"):
        return _bedrock(prompt)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _anthropic(prompt)
    if os.environ.get("OPENAI_API_KEY"):
        return _openai(prompt)
    return ""


def _generate(facts: dict[str, object]) -> str:
    """Call the configured provider with the signal-rationale prompt."""
    return dispatch(_render_prompt(facts))


def _render_prompt(facts: dict[str, object]) -> str:
    factor_lines = "\n".join(
        f"  - {f['name']}: value={f['value']} weight={f['weight']} inputs={f['inputs']}"
        for f in facts["factors"]  # type: ignore[union-attr]
    )
    return (
        f"Signal: {facts['title']}\n"
        f"Detail: {facts['summary']}\n"
        f"Type: {facts['type']}\n"
        f"Therapeutic area: {facts['area']}\n"
        f"Company: {facts['company']}\n"
        f"Stage: {facts['stage']}\n"
        f"Published: {facts['published']}\n"
        f"Sources: {facts['sources']}\n"
        f"Computed score: {facts['score']}/100 (priority {facts['priority']})\n"
        f"Score factors:\n{factor_lines}\n"
    )


def _bedrock(prompt: str) -> str:
    """Amazon Bedrock via the Converse API.

    Defaults to Nova because it is the only family reachable in this account —
    Anthropic models on Bedrock here are blocked by a missing Marketplace
    subscription, so defaulting to Claude would fail every call.
    """
    import boto3

    model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    res = client.converse(
        modelId=model_id,
        system=[{"text": _SYSTEM}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.2},
    )
    return "".join(
        block.get("text", "") for block in res["output"]["message"]["content"]
    ).strip()


def _anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    res = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL_ID", "claude-haiku-4-5-20251001"),
        max_tokens=300,
        temperature=0.2,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in res.content if b.type == "text").strip()


def _openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    res = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL_ID", "gpt-4.1-mini"),
        max_completion_tokens=300,
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return (res.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Verification — the fence
# ---------------------------------------------------------------------------


def verify(text: str, facts: dict[str, object]) -> tuple[bool, str]:
    """Reject output that could mislead. Checked, not merely requested in the prompt.

    The number check is the important one. Every digit in the output must appear
    somewhere in the input, so the model can say "scored 84" or "matched 3 terms"
    (both given) but cannot say "78% response rate" (never given). Years like 2026
    pass only because the publication date supplied them.
    """
    if not text.strip():
        return False, "empty"

    words = text.split()
    if len(words) > _MAX_WORDS * 1.5:
        return False, f"too long ({len(words)} words)"

    haystack = _numeric_corpus(facts)
    for number in _NUMBER.findall(text):
        canonical = number.replace(",", "").rstrip("0").rstrip(".") or "0"
        if not any(
            canonical == c or number == c or number.replace(",", "") == c for c in haystack
        ):
            return False, f"fabricated number {number!r}"

    lowered = text.lower()
    for refusal in ("i cannot", "i'm unable", "as an ai", "i do not have"):
        if refusal in lowered:
            return False, "model refused"

    return True, ""


def _numeric_corpus(facts: dict[str, object]) -> set[str]:
    """Every number the model was legitimately given, in canonical form."""
    parts: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                walk(v)
        else:
            parts.append(str(value))

    walk(facts)
    corpus: set[str] = set()
    for chunk in parts:
        for number in _NUMBER.findall(chunk):
            plain = number.replace(",", "")
            corpus.add(plain)
            corpus.add(plain.rstrip("0").rstrip(".") or "0")
            # A score rendered "84" should also license the model writing "84.0",
            # and a factor value "0.80" should license "0.8".
            try:
                corpus.add(str(int(float(plain))))
            except ValueError:
                pass
    return corpus
