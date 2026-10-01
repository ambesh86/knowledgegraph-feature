"""The scientific confidence score, and the refusal to fake one.

The use case asks for "a final 'scientific confidence score' with supporting
reasoning". The obvious implementation — average some sub-scores, print 7.4/10 — is
the one that gets the system quietly retired after the first brief a scientist checks.
A single number over sparse evidence looks identical to a single number over strong
evidence, and the reader cannot tell which they are holding.

Three rules, each a direct reading of the document's own architecture principles:

**Below an evidence floor, there is no score.** The principle is "flag low-confidence
outputs for human review rather than suppressing uncertainty". A company with two
publications and no trials does not get 3.1/10 — it gets INSUFFICIENT EVIDENCE, which
is the true finding and the one that tells an analyst where to spend their time. A low
number invites a comparison it cannot support; an explicit refusal does not.

**Every component names the data points that produced it.** The principle is that BD
leaders "can interrogate and challenge the model's reasoning". A component that cannot
say why it scored 0.4 is not challengeable, so each carries its inputs and the signals
it counted.

**Absence is distinguished from weakness.** No patents found and patents found but
weak are different facts with different remedies — one is a search gap, the other is a
finding. Collapsing them into a low score destroys the distinction the analyst needs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from scout.models import Signal, SignalType


class ConfidenceBand(StrEnum):
    INSUFFICIENT = "insufficient_evidence"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


# Minimum corroborated evidence before ANY score is emitted. Set by what a human
# analyst would accept as a starting point rather than by what makes the demo look
# good: fewer than three independent items is a lead, not a diligence subject.
MIN_TOTAL_SIGNALS = 3
MIN_DISTINCT_SOURCES = 2

# The dimensions a "scientific confidence" score is fundamentally about. Missing
# either caps the band — see the note at the bottom of assess().
_CORE = {"clinical", "literature"}


@dataclass
class Component:
    """One scored dimension, with the evidence that produced it."""

    key: str
    label: str
    score: float | None          # None = could not be assessed, which is NOT zero
    weight: float
    finding: str                 # one line an analyst can agree or disagree with
    evidence: list[str] = field(default_factory=list)

    @property
    def assessable(self) -> bool:
        return self.score is not None

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "score": None if self.score is None else round(self.score, 3),
            "weight": self.weight,
            "assessable": self.assessable,
            "finding": self.finding,
            "evidence": self.evidence[:6],
        }


@dataclass
class ConfidenceAssessment:
    band: ConfidenceBand
    score: float | None
    components: list[Component]
    reasons: list[str]
    signals_considered: int
    distinct_sources: int
    needs_human_review: bool

    def as_dict(self) -> dict:
        return {
            "band": str(self.band),
            "score": None if self.score is None else round(self.score, 1),
            "score_out_of": 10,
            "needs_human_review": self.needs_human_review,
            "reasons": self.reasons,
            "signals_considered": self.signals_considered,
            "distinct_sources": self.distinct_sources,
            "components": [c.as_dict() for c in self.components],
            "unassessable_components": [
                c.label for c in self.components if not c.assessable
            ],
        }


def _cite(s: Signal) -> str:
    src = s.sources[0].url if getattr(s, "sources", None) else ""
    return f"{s.title[:110]}{' — ' + src if src else ''}"


def _clinical(signals: list[Signal]) -> Component:
    """Clinical maturity, from trial phase.

    Phase is the strongest single de-risking fact available from public data, which is
    why it dominates. A registered phase 3 is a different asset from a preclinical
    programme regardless of how well either is written up.
    """
    trials = [s for s in signals if s.type == SignalType.TRIAL]
    if not trials:
        return Component(
            "clinical", "Clinical data maturity", None, 0.30,
            "No registered trials found for this target — assessed as a gap in the "
            "search, not as evidence of absence.",
        )

    ladder = {"early_phase1": 0.2, "phase1": 0.35, "phase2": 0.6, "phase3": 0.85, "phase4": 1.0}
    best, best_stage = 0.0, "unstaged"
    for t in trials:
        stage = (getattr(t, "stage", "") or "").lower().replace(" ", "").replace("/", "")
        for name, value in ladder.items():
            if name in stage and value > best:
                best, best_stage = value, name
    if best == 0.0:
        # Trials exist but none declared a phase — real, and not the same as no trials.
        best, best_stage = 0.25, "phase not stated"

    return Component(
        "clinical", "Clinical data maturity", best, 0.30,
        f"{len(trials)} registered trial(s); most advanced stage {best_stage}.",
        [_cite(t) for t in trials[:4]],
    )


def _literature(signals: list[Signal]) -> Component:
    """Depth of the published evidence base."""
    pubs = [s for s in signals if s.type == SignalType.PUBLICATION]
    if not pubs:
        return Component(
            "literature", "Published evidence", None, 0.20,
            "No publications retrieved — a search gap rather than a scientific finding.",
        )
    # Saturating rather than linear: the difference between 1 and 6 papers is large,
    # between 40 and 60 is noise, and a linear scale would let a prolific-but-shallow
    # target outrank a focused one.
    score = min(1.0, len(pubs) / 12)
    return Component(
        "literature", "Published evidence", score, 0.20,
        f"{len(pubs)} publication(s) in the review window.",
        [_cite(p) for p in pubs[:4]],
    )


def _ip(signals: list[Signal]) -> Component:
    """IP position from patent filings."""
    pats = [s for s in signals if s.type == SignalType.PATENT]
    if not pats:
        return Component(
            "ip", "IP position", None, 0.20,
            "No patent records retrieved. Distinguish before relying on this: it may "
            "mean unprotected, or filed-but-unpublished (18-month delay), or simply "
            "outside the searched corpus.",
        )
    score = min(1.0, len(pats) / 8)
    return Component(
        "ip", "IP position", score, 0.20,
        f"{len(pats)} patent record(s) associated with the target.",
        [_cite(p) for p in pats[:4]],
    )


def _corroboration(signals: list[Signal]) -> Component:
    """How many independent sources tell the same story.

    Weighted meaningfully because single-source claims are how a diligence brief
    inherits an upstream error. Two independent registries agreeing is a materially
    stronger fact than one registry asserting.
    """
    sources = {s.sources[0].source for s in signals if getattr(s, "sources", None)}
    n = len(sources)
    if n == 0:
        return Component("corroboration", "Source corroboration", None, 0.15,
                         "No attributable sources on the retrieved signals.")
    score = {1: 0.25, 2: 0.55, 3: 0.8}.get(n, 1.0)
    return Component(
        "corroboration", "Source corroboration", score, 0.15,
        f"Evidence drawn from {n} independent source(s): {', '.join(sorted(str(x) for x in sources))}.",
    )


def _regulatory(signals: list[Signal]) -> Component:
    """Regulatory and corporate signal presence."""
    reg = [s for s in signals if s.type in (SignalType.REGULATORY, SignalType.CORPORATE)]
    if not reg:
        return Component(
            "regulatory", "Regulatory / corporate disclosure", None, 0.15,
            "No regulatory or corporate filings retrieved. Expected for a private "
            "company — absence here is weak evidence either way.",
        )
    return Component(
        "regulatory", "Regulatory / corporate disclosure", min(1.0, len(reg) / 4), 0.15,
        f"{len(reg)} regulatory/corporate disclosure(s) found.",
        [_cite(r) for r in reg[:4]],
    )


def assess(signals: list[Signal]) -> ConfidenceAssessment:
    """Produce the scientific confidence assessment for a target."""
    components = [
        _clinical(signals),
        _literature(signals),
        _ip(signals),
        _corroboration(signals),
        _regulatory(signals),
    ]
    sources = {s.sources[0].source for s in signals if getattr(s, "sources", None)}
    reasons: list[str] = []

    # --- the floor --------------------------------------------------------
    if len(signals) < MIN_TOTAL_SIGNALS or len(sources) < MIN_DISTINCT_SOURCES:
        reasons.append(
            f"Only {len(signals)} signal(s) across {len(sources)} source(s) — below the "
            f"floor of {MIN_TOTAL_SIGNALS} signals from {MIN_DISTINCT_SOURCES} sources "
            "required to score. A number computed from this little evidence would imply "
            "a comparison it cannot support."
        )
        reasons.append(
            "Treat as a search result, not an assessment: widen the aliases, check the "
            "legal name, or confirm the target is publicly disclosed at all."
        )
        return ConfidenceAssessment(
            ConfidenceBand.INSUFFICIENT, None, components, reasons,
            len(signals), len(sources), needs_human_review=True,
        )

    # --- weighted over ASSESSABLE components only -------------------------
    # Renormalising over what could be assessed is the honest treatment. Scoring an
    # unassessable component as zero would punish a target for a gap in our search and
    # make "we did not look there" indistinguishable from "there is nothing there".
    assessable = [c for c in components if c.assessable]
    total_weight = sum(c.weight for c in assessable)
    raw = sum((c.score or 0) * c.weight for c in assessable) / total_weight
    score10 = round(raw * 10, 1)

    missing = [c.label for c in components if not c.assessable]
    if missing:
        reasons.append(
            "Scored over the dimensions that could be assessed; "
            f"{len(missing)} could not be ({', '.join(missing)}). The score is "
            "conditional on that coverage, not a verdict on the whole target."
        )

    if raw >= 0.70:
        band = ConfidenceBand.HIGH
    elif raw >= 0.45:
        band = ConfidenceBand.MODERATE
    else:
        band = ConfidenceBand.LOW
        reasons.append("Below the moderate threshold — recommend analyst review before outreach.")

    # Coverage gates the band regardless of the arithmetic: a 0.8 built on two of five
    # dimensions is not a high-confidence assessment, it is a narrow one.
    if len(assessable) < 3 and band == ConfidenceBand.HIGH:
        band = ConfidenceBand.MODERATE
        reasons.append(
            f"Capped at moderate: only {len(assessable)} of {len(components)} dimensions "
            "could be assessed, which is too narrow a base for a high-confidence call."
        )

    # A missing CORE dimension caps the band regardless of the arithmetic.
    #
    # Renormalising over assessable components — the honest treatment of a gap in one
    # direction — has a perverse effect in the other: the fewer dimensions that can be
    # assessed, the easier a high score becomes. The first live run scored 9.1/10
    # "high" for a target whose literature dimension was empty, which is a search
    # failure presented as a strong result. Science and clinical evidence are the two
    # dimensions a scientific confidence score is actually about; missing either means
    # the assessment is incomplete, whatever the remaining dimensions say.
    missing_core = [c.label for c in components if c.key in _CORE and not c.assessable]
    if missing_core and band == ConfidenceBand.HIGH:
        band = ConfidenceBand.MODERATE
        reasons.append(
            f"Capped at moderate: no evidence was retrieved for {', '.join(missing_core)}, "
            "which is a core dimension. A high-confidence call cannot rest on the "
            "remaining dimensions while a core one is unmeasured — most often this "
            "means the search missed it, not that it does not exist."
        )

    needs_review = band in (ConfidenceBand.LOW, ConfidenceBand.INSUFFICIENT) or bool(missing)
    return ConfidenceAssessment(
        band, score10, components, reasons, len(signals), len(sources), needs_review
    )
