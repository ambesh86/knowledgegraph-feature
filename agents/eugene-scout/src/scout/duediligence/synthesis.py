"""The executive summary — the one part of the brief a model writes.

    "The orchestrator synthesises all sub-agent outputs using a Claude model to
     resolve conflicting signals and produce a coherent narrative."

Everything else in the brief is deterministic: counts, phases, dates, scores, risk
flags. That is deliberate, and it is what makes this section safe to add. The model is
given facts that were already computed and verified, asked to narrate them, and its
output is then checked against those same facts before anyone sees it.

The check is `rationale.verify`, reused rather than reimplemented. Its number rule is
the important one: **every digit in the generated text must appear somewhere in the
input facts.** A model may write "10 registered trials" or "phase 3" because both were
supplied; it cannot write "62% response rate" because that number was never given. In
a due-diligence document destined for a partnership decision, an invented efficacy
figure is the failure that matters, and it is the one a prompt instruction alone will
not reliably prevent. It fires in practice — an earlier live run logged
`rejected generated rationale (fabricated number '74')`.

When the model is unavailable, refuses, or fabricates, the section falls back to a
deterministic summary of the same facts. The brief always has an executive summary;
what varies is whether it was written by a model, and the brief says which.
"""
from __future__ import annotations

import json
import logging

from scout import rationale
from scout.models import RationaleKind

logger = logging.getLogger(__name__)

_PROMPT = """You are writing the executive summary of a scientific due-diligence brief
for a pharmaceutical business-development team assessing a potential partner.

FACTS (the only information you may use):
{facts}

Write 3-5 sentences covering, in this order:
  1. what the target is and the scale of evidence found
  2. the strongest evidence, naming the source type
  3. the most important gap or conflict in the evidence
  4. what the confidence band means for the next step

Rules:
- Use ONLY numbers that appear in the FACTS above. Do not compute new ones, do not
  estimate, do not round into a figure that is not there.
- If a dimension had no evidence, say the search found none — never that none exists.
- No recommendation to invest or not invest. You are summarising evidence, not
  deciding.
- Plain professional English. No bullet points, no headings, no preamble."""


def _facts_from(brief: dict) -> dict:
    """Flatten the brief into the facts the model may use.

    This dict is doing double duty: it is the prompt content AND the corpus that
    `verify` checks generated numbers against. Anything omitted here becomes a number
    the model is forbidden to use, which is why the counts are included explicitly
    rather than left implicit in the evidence lists.
    """
    conf = brief.get("confidence") or {}
    coverage = brief.get("coverage") or {}
    target = brief.get("target") or {}

    sections = {}
    for sec in brief.get("sections", []):
        sections[sec["title"]] = {
            "items_found": sec.get("evidence_count", 0),
            "sources_consulted": sec.get("sources_consulted", []),
            "gap": sec.get("coverage_note"),
        }

    return {
        "target": target.get("label"),
        "company": target.get("company"),
        "asset": target.get("asset"),
        "total_evidence_items": coverage.get("signals_total"),
        "sources_consulted": coverage.get("sources_consulted", []),
        "sources_failed": coverage.get("sources_failed", []),
        "confidence_band": conf.get("band"),
        "confidence_score_out_of_10": conf.get("score"),
        "dimensions": {
            c["label"]: {
                "score": c.get("score"),
                "finding": c.get("finding"),
                "assessable": c.get("assessable"),
            }
            for c in conf.get("components", [])
        },
        "dimensions_not_assessable": conf.get("unassessable_components", []),
        "sections": sections,
        "risk_flags": [f["flag"] for f in brief.get("risk_flags", [])],
        "caveats": conf.get("reasons", []),
    }


def _template(brief: dict) -> str:
    """Deterministic summary. Always correct, always available."""
    conf = brief.get("confidence") or {}
    coverage = brief.get("coverage") or {}
    target = (brief.get("target") or {}).get("label", "the target")
    band = str(conf.get("band", "unknown")).replace("_", " ")
    total = coverage.get("signals_total", 0)
    sources = coverage.get("sources_consulted", [])
    missing = conf.get("unassessable_components", [])
    flags = [f["flag"] for f in brief.get("risk_flags", [])]

    parts = [
        f"Due diligence on {target} retrieved {total} evidence item(s) across "
        f"{len(sources)} source(s): {', '.join(sources) if sources else 'none'}."
    ]
    if conf.get("score") is not None:
        parts.append(
            f"The scientific confidence assessment is {band} "
            f"({conf['score']}/10), weighted across the dimensions that could be assessed."
        )
    else:
        parts.append(
            f"No confidence score was computed: the evidence is {band}, which means "
            "the retrieved material is below the threshold this assessment requires."
        )
    if missing:
        parts.append(
            f"{len(missing)} dimension(s) could not be assessed ({', '.join(missing)}); "
            "the search found no evidence there, which is not the same as there being none."
        )
    if flags:
        parts.append(f"Flagged for analyst attention: {'; '.join(flags[:3])}.")
    return " ".join(parts)


def summarise(brief: dict) -> tuple[str, str]:
    """Return (summary_text, provenance) where provenance is 'llm' or 'template'.

    Never raises. A due-diligence brief that fails to render because a language model
    was unreachable would be a worse outcome than one with a plainer summary.
    """
    facts = _facts_from(brief)
    fallback = _template(brief)

    if not rationale.llm_enabled():
        return fallback, str(RationaleKind.TEMPLATE)

    try:
        generated = rationale.dispatch(
            _PROMPT.format(facts=json.dumps(facts, indent=2, default=str))
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"synthesis failed, using template: {type(e).__name__}: {e}")
        return fallback, str(RationaleKind.TEMPLATE)

    if not generated:
        return fallback, str(RationaleKind.TEMPLATE)

    ok, reason = rationale.verify(generated, facts)
    if not ok:
        # Loud rather than silent: a rejected synthesis means the model tried to
        # introduce a fact nobody gave it, which is worth seeing in the logs even
        # though the reader is protected from it.
        logger.warning(f"rejected generated executive summary ({reason}); using template")
        return fallback, str(RationaleKind.TEMPLATE)

    return generated, str(RationaleKind.LLM)
