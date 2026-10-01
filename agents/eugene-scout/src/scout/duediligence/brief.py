"""Use Case 2 — Accelerated Scientific Due Diligence.

    "An on-demand agentic workflow that compresses weeks of analyst due diligence
     work into hours, producing a structured scientific assessment of a target
     partner's pipeline."

The document names four specialist sub-agents (Literature, Clinical Data, IP,
Competitive Positioning) and six brief sections. Both are implemented literally, with
the sub-agents being the Use Case 1 collectors re-pointed at a single target — see
`target.py` for why reusing them beats writing a second set.

Two deliberate departures from a naive reading of the spec, both in the direction of
being trusted by the scientists who have to act on the output:

**The brief states what it did not find.** A due-diligence document that silently
omits the sources that returned nothing is indistinguishable from one where those
sources were never consulted. Each section declares its coverage, so "no patents" and
"we did not check patents" can never be confused.

**No section is padded.** The spec says 8-10 pages. Where the evidence supports two
paragraphs, this produces two paragraphs and says so. Padding a diligence brief to a
page count is how an analyst learns to skim it, and a skimmed brief is worse than a
short one.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from scout.duediligence import confidence as conf
from scout.duediligence.target import Target
from scout.models import Signal, SignalType, utcnow

logger = logging.getLogger(__name__)


def _by_type(signals: list[Signal], *types: SignalType) -> list[Signal]:
    wanted = set(types)
    return sorted(
        (s for s in signals if s.type in wanted),
        key=lambda s: (s.score or 0),
        reverse=True,
    )


def _cite(s: Signal) -> dict:
    src = s.sources[0] if getattr(s, "sources", None) else None
    return {
        "title": s.title,
        "url": getattr(src, "url", "") if src else "",
        "source": str(getattr(src, "source", "")) if src else "",
        "published": s.published.isoformat() if getattr(s, "published", None) else None,
        "score": round(s.score, 1) if getattr(s, "score", None) is not None else None,
    }


def _section(
    key: str,
    title: str,
    signals: list[Signal],
    *,
    sources_consulted: list[str],
    empty_meaning: str,
    summary: str | None = None,
) -> dict:
    """One section, which always declares its own coverage.

    `empty_meaning` is required rather than optional: an empty section must explain
    what its emptiness implies, because "nothing found" and "nothing exists" are
    different claims and only the author of the section knows which applies.
    """
    return {
        "key": key,
        "title": title,
        "summary": summary or (
            f"{len(signals)} item(s) found." if signals else empty_meaning
        ),
        "evidence_count": len(signals),
        "sources_consulted": sources_consulted,
        "evidence": [_cite(s) for s in signals[:12]],
        "coverage_note": None if signals else empty_meaning,
    }


def build(
    target: Target,
    signals: list[Signal],
    source_reports: list[Any] | None = None,
    *,
    now: dt.datetime | None = None,
) -> dict:
    """Assemble the Due Diligence Brief for one target."""
    now = now or utcnow()
    reports = source_reports or []

    consulted = [str(getattr(r, "source", "")) for r in reports]
    failed = [
        str(getattr(r, "source", "")) for r in reports
        if getattr(r, "ok", True) is False
    ]

    trials = _by_type(signals, SignalType.TRIAL)
    pubs = _by_type(signals, SignalType.PUBLICATION)
    patents = _by_type(signals, SignalType.PATENT)
    regulatory = _by_type(signals, SignalType.REGULATORY, SignalType.CORPORATE)

    assessment = conf.assess(signals)

    sections = [
        _section(
            "scientific_rationale", "Scientific rationale", pubs,
            sources_consulted=["Europe PMC", "PubMed"],
            empty_meaning=(
                "No publications retrieved for this target in the review window. This "
                "is a gap in the literature search — possibly a private company with no "
                "publication record, or a name mismatch — not evidence that the science "
                "is unpublished."
            ),
        ),
        _section(
            "clinical_data", "Clinical data quality assessment", trials,
            sources_consulted=["ClinicalTrials.gov"],
            empty_meaning=(
                "No registered trials found. Check the sponsor's legal name before "
                "concluding the target has no clinical programme; registrations are "
                "filed under the legal entity, which is often not the trading name."
            ),
        ),
        _section(
            "ip_landscape", "IP landscape", patents,
            sources_consulted=["Europe PMC patents", "EPO"],
            empty_meaning=(
                "No patent records retrieved. Note the 18-month publication delay: a "
                "recently filed family is invisible to any public search, so absence "
                "here cannot distinguish 'unprotected' from 'not yet published'."
            ),
        ),
        _section(
            "regulatory", "Regulatory & corporate disclosure", regulatory,
            sources_consulted=["SEC EDGAR"],
            empty_meaning=(
                "No regulatory or corporate filings retrieved. Expected for a private "
                "company; EDGAR covers US-listed entities only, so this is uninformative "
                "for a private or non-US target."
            ),
        ),
    ]

    # Competitive differentiation is a comparison, and a comparison needs something to
    # compare against. Rather than have a model improvise one, the section states the
    # evidence available and defers — an invented competitive claim in a diligence
    # brief is the kind of error that survives into a term sheet.
    sections.append({
        "key": "competitive",
        "title": "Competitive differentiation",
        "summary": (
            f"{len(trials)} trial(s) and {len(patents)} patent record(s) are on file for "
            "this target. Positioning against named competitors requires a comparator "
            "set, which this workflow does not select on the analyst's behalf."
        ),
        "evidence_count": len(trials) + len(patents),
        "sources_consulted": ["ClinicalTrials.gov", "Europe PMC patents"],
        "evidence": [],
        "coverage_note": (
            "Not auto-generated. Supply a comparator list to have this section scored, "
            "or treat the clinical and IP sections as the inputs to a manual comparison."
        ),
    })

    risk_flags = _risk_flags(signals, trials, patents, failed)

    return {
        "schema": "eugene.due_diligence.v1",
        "target": {
            "id": target.id,
            "company": target.company,
            "asset": target.asset,
            "label": target.label,
            "search_terms": target.search_terms(),
        },
        "generated_at": now.isoformat(),
        "confidence": assessment.as_dict(),
        "sections": sections,
        "risk_flags": risk_flags,
        "coverage": {
            "sources_consulted": consulted,
            "sources_failed": failed,
            "signals_total": len(signals),
            # A brief built while a source was down is a different artefact from one
            # built with full coverage, and the reader is entitled to know which.
            "complete": not failed,
        },
        "next_action": _next_action(assessment, trials, failed),
    }


def _risk_flags(
    signals: list[Signal],
    trials: list[Signal],
    patents: list[Signal],
    failed: list[str],
) -> list[dict]:
    """Explicit risks, each traceable to the fact that produced it.

    Rule-derived rather than model-generated, for the same reason the Use Case 1
    'next action' is: an analyst who disagrees can see precisely which condition fired
    and argue with the condition instead of with a paragraph.
    """
    flags: list[dict] = []

    if failed:
        flags.append({
            "severity": "high",
            "flag": "Incomplete source coverage",
            "detail": f"These sources failed during the run: {', '.join(failed)}. "
                      "Sections drawing on them understate the evidence.",
        })
    if not trials:
        flags.append({
            "severity": "medium",
            "flag": "No registered clinical trials found",
            "detail": "Either preclinical, or registered under a legal name not searched.",
        })
    if not patents:
        flags.append({
            "severity": "medium",
            "flag": "No patent records found",
            "detail": "Freedom-to-operate cannot be assessed from this brief. The "
                      "18-month publication delay means recent filings are invisible.",
        })
    single_source = [
        s for s in signals if len(getattr(s, "sources", []) or []) == 1
    ]
    if signals and len(single_source) == len(signals):
        flags.append({
            "severity": "medium",
            "flag": "No corroborated signals",
            "detail": "Every item rests on a single source. Nothing in this brief has "
                      "been independently confirmed.",
        })
    # `published` is a date, not a datetime — calling .date() on it raised on the
    # first live run. Kept explicit rather than defensive: the model declares
    # `published: dt.date | None`, so this is the type, not a guess.
    today = utcnow().date()
    stale = [
        s for s in signals
        if getattr(s, "published", None) and (today - s.published).days > 365
    ]
    if signals and len(stale) == len(signals):
        flags.append({
            "severity": "low",
            "flag": "All evidence over 12 months old",
            "detail": "No recent activity found; the programme may be dormant.",
        })
    return flags


def _next_action(assessment: conf.ConfidenceAssessment, trials: list[Signal], failed: list[str]) -> str:
    """One recommended next step, following from conditions already established."""
    if failed:
        return (
            "Re-run once the failed sources recover — do not act on this brief while "
            "coverage is incomplete."
        )
    if assessment.band == conf.ConfidenceBand.INSUFFICIENT:
        return (
            "Do not progress on this evidence. Confirm the legal entity name and any "
            "asset code names, then re-run; if it is still empty, the target is likely "
            "not publicly disclosed and needs primary research."
        )
    if assessment.band == conf.ConfidenceBand.LOW:
        return "Analyst review before any outreach — the evidence base is thin."
    if trials and assessment.band == conf.ConfidenceBand.HIGH:
        return (
            "Progress to scientific review: clinical evidence is present and the "
            "assessment is well-covered. Route the clinical section to the therapeutic "
            "area lead."
        )
    return "Analyst review recommended; evidence is moderate and worth a human read."
