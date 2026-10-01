"""LLM-as-judge for open-ended answers — and the validation that makes it quotable.

The deterministic checks in `faithfulness.py` cover numbers, citations and
abstention. They cannot grade "is this a good answer to a question with no single
correct string", which is most of what users actually ask. That needs a model.

A model grading a model is only worth reporting if its own accuracy is known. The
order of operations here is deliberate and is the part usually skipped:

  1. a human labels a sample of answers (`--label`)
  2. the judge grades the same sample
  3. Cohen's kappa is computed against the human labels
  4. only if kappa clears the bar is the judge used to report a number

Without step 4 an "LLM judge accuracy" is an unfalsifiable claim, and a
sufficiently agreeable judge will rate anything highly — a judge that says
"correct" on a 90%-correct set agrees 90% of the time while having learned
nothing. Kappa shows that as ~0.

Two more guards against the known failure modes of this technique:

* **Self-consistency.** Each answer is graded `n` times and the majority taken.
  A single sample at temperature > 0 is noisy, and that noise lands directly in
  the headline number.
* **A rubric with an explicit "cannot tell".** Forcing a binary verdict on an
  ambiguous case manufactures agreement that is not there; those cases are
  counted and reported rather than resolved by coin flip.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

import metrics as M

# Reuses the stack's own provider config so the eval talks to the same model the
# product does. Set EVAL_JUDGE_MODEL to grade with a different one — grading with
# the model under test is a real bias and worth being able to change.
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "gpt-4o-mini")

RUBRIC = """You are grading an answer produced by a biomedical research assistant.

You will be given: the QUESTION, the EVIDENCE passages the assistant was shown,
and its ANSWER.

Grade ONLY on whether the answer is supported by the evidence provided. Do not
use outside knowledge. An answer that is true in the world but not supported by
these passages is UNSUPPORTED — the system's job is to ground its claims, and a
lucky guess is a failure of that job.

Reply with strict JSON and nothing else:
{"verdict": "supported" | "unsupported" | "cannot_tell", "reason": "<one sentence>"}

Use "cannot_tell" when the question is ambiguous or the evidence is too garbled
to judge. Do not guess between supported and unsupported to avoid it."""


@dataclass
class Verdict:
    verdict: str          # supported | unsupported | cannot_tell
    reason: str
    votes: dict           # raw tally across self-consistency samples

    @property
    def supported(self) -> bool:
        return self.verdict == "supported"


def _call(messages: list[dict], temperature: float) -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set; the judge cannot run")
    body = json.dumps({
        "model": JUDGE_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 200,
    }).encode()
    req = urllib.request.Request(
        OPENAI_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.load(resp)
    return payload["choices"][0]["message"]["content"]


def _parse(raw: str) -> tuple[str, str]:
    """Extract the verdict, tolerating a model that wraps JSON in prose or fences."""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            v = str(d.get("verdict", "")).lower().strip()
            if v in {"supported", "unsupported", "cannot_tell"}:
                return v, str(d.get("reason", ""))[:200]
        except json.JSONDecodeError:
            pass
    # An unparseable judge response is "cannot_tell", never a silent "supported".
    # Defaulting a parse failure to the favourable verdict inflates the score in
    # exactly the cases where the judge was most confused.
    return "cannot_tell", f"unparseable judge response: {raw[:80]}"


def grade(
    question: str, answer: str, passages: list[str], samples: int = 3, temperature: float = 0.0
) -> Verdict:
    """Grade one answer, taking the majority over `samples` independent calls."""
    evidence = "\n\n".join(f"[{i+1}] {p[:1200]}" for i, p in enumerate(passages[:10]))
    messages = [
        {"role": "system", "content": RUBRIC},
        {"role": "user", "content": f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence}\n\nANSWER:\n{answer}"},
    ]

    votes: dict[str, int] = {}
    reasons: dict[str, str] = {}
    for i in range(samples):
        try:
            # First sample greedy for reproducibility; later ones varied so the
            # majority reflects genuine disagreement rather than three identical
            # replays of the same draw.
            raw = _call(messages, temperature if i == 0 else max(temperature, 0.3))
            v, why = _parse(raw)
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, KeyError) as e:
            v, why = "cannot_tell", f"judge call failed: {type(e).__name__}"
        votes[v] = votes.get(v, 0) + 1
        reasons.setdefault(v, why)

    winner = max(votes, key=lambda k: votes[k])
    return Verdict(winner, reasons.get(winner, ""), votes)


# ---------------------------------------------------------------------------
# Validating the judge itself
# ---------------------------------------------------------------------------


def validate(labelled: list[dict], samples: int = 3) -> dict:
    """Measure the judge against human labels before trusting its numbers.

    `labelled` items: {question, answer, passages, human: bool}

    Reports agreement, Cohen's kappa, and — separately — how often the judge
    declined. A judge that abstains on a third of the set may show a fine kappa
    on the remainder while being useless in practice, so the abstention rate is
    quoted next to it rather than folded in.
    """
    human, machine, abstained = [], [], 0
    for item in labelled:
        v = grade(item["question"], item["answer"], item["passages"], samples=samples)
        if v.verdict == "cannot_tell":
            abstained += 1
            continue
        human.append(bool(item["human"]))
        machine.append(v.supported)

    if not human:
        return {"usable": False, "reason": "the judge declined on every labelled example"}

    kappa = M.cohen_kappa(human, machine)
    agreement = M.wilson(sum(1 for a, b in zip(human, machine) if a == b), len(human))

    # 0.6 is the conventional "substantial agreement" boundary. Below it the
    # judge's output should not be quoted as an accuracy figure to anyone.
    usable = kappa >= 0.6
    return {
        "usable": usable,
        "kappa": round(kappa, 4),
        "kappa_reading": (
            "near-human" if kappa >= 0.8 else
            "substantial" if kappa >= 0.6 else
            "moderate" if kappa >= 0.4 else "poor"
        ),
        "raw_agreement": agreement.as_dict(),
        "n_labelled": len(labelled),
        "n_graded": len(human),
        "n_abstained": abstained,
        "model": JUDGE_MODEL,
        "verdict": (
            f"kappa {kappa:.2f} — safe to quote judge-scored accuracy"
            if usable else
            f"kappa {kappa:.2f} — DO NOT report judge-scored accuracy; "
            "label more examples or improve the rubric first"
        ),
    }
