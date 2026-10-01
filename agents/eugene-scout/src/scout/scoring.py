"""Deterministic scoring — the auditability contract.

`score()` is a pure function. No network, no clock, no LLM, no randomness. The same
signal and the same config produce the same number forever, and every number carries
the inputs that produced it.

This is not fastidiousness, it is the product requirement. The PDF asks for
recommendations that "BD leaders can interrogate and challenge". A ranking an LLM
produced cannot be interrogated — asked twice, it answers differently, and asked why,
it invents a reason. A weighted sum over six named factors can be challenged
factor-by-factor, replayed against last month's weights, and unit-tested. The LLM's
job (rationale.py) starts only after the number exists, and it is confined to writing
prose about a decision it did not make.

Normalisation detail worth stating plainly: the score is divided by the total weight
of the factors that **applied**, not by the total weight configured. A literature hit
has no development stage; scoring `stage_fit = 0` for it would systematically punish
an entire source for lacking a property it cannot have, and would make papers
uncompetitive with trials no matter how relevant they were.
"""
from __future__ import annotations

import datetime as dt
import math
import re

from scout.areas import Area
from scout.config import ScanConfig
from scout.models import Priority, RawSignal, ScoreFactor, ScoreResult, SignalType, SourceId

# A factor returning None means "not applicable to this signal" and is excluded from
# both numerator and denominator. Distinct from 0.0, which means "applicable, scored
# badly" — the difference is what stops undated papers outranking Phase II trials.
type FactorValue = tuple[float, dict[str, object]] | None

_WORD = re.compile(r"[a-z0-9]+")


def score(
    signal: RawSignal,
    area: Area,
    config: ScanConfig,
    *,
    today: dt.date,
    corroboration_count: int = 1,
    company_known: bool = False,
    company_signal_count: int = 0,
) -> ScoreResult:
    """Score one signal. Pure: every input is an argument, including `today`."""
    weights = config.weights
    computed: list[ScoreFactor] = []

    for name, weight, value in (
        ("area_fit", weights.area_fit, _area_fit(signal, area)),
        ("stage_fit", weights.stage_fit, _stage_fit(signal, config)),
        ("recency", weights.recency, _recency(signal, config, today)),
        ("modality_fit", weights.modality_fit, _modality_fit(signal, config)),
        ("corroboration", weights.corroboration, _corroboration(corroboration_count)),
        ("company_context", weights.company_context,
         _company_context(signal, company_known, company_signal_count)),
    ):
        if value is None or weight <= 0:
            continue
        raw, inputs = value
        computed.append(
            ScoreFactor(name=name, value=_clamp01(raw), weight=weight, inputs=inputs)
        )

    total_weight = sum(f.weight for f in computed)
    if total_weight <= 0:
        # Every factor was inapplicable or zero-weighted. Score 0 rather than divide
        # by zero, and let the priority bands put it at the bottom where it belongs.
        final = 0.0
    else:
        final = 100.0 * sum(f.contribution for f in computed) / total_weight

    final = round(max(0.0, min(100.0, final)), 2)
    return ScoreResult(
        score=final,
        priority=config.thresholds.priority_for(final),
        factors=tuple(computed),
    )


# ---------------------------------------------------------------------------
# Factors
# ---------------------------------------------------------------------------


def _area_fit(signal: RawSignal, area: Area) -> FactorValue:
    """How strongly the signal's text matches the area's declared keywords.

    Saturating rather than linear: three matched keywords is a confident topical
    match, and a record that happens to repeat six of them is not twice as relevant.
    Without saturation, long trial descriptions would outrank short precise ones
    purely by surface area.
    """
    matched = sorted(set(signal.keywords))
    if not area.keywords:
        return None
    hits = len(matched)
    value = 1.0 - math.exp(-hits / 1.5) if hits else 0.0
    return value, {"matched": matched, "match_count": hits,
                   "area_keywords": len(area.keywords)}


def _stage_fit(signal: RawSignal, config: ScanConfig) -> FactorValue:
    """Development stage relevance.

    Not applicable to literature and patents, which carry no stage — those return
    None and drop out of the normalisation entirely.
    """
    if not signal.stage:
        return None
    stage = signal.stage.strip().upper()
    value = config.stage_scores.get(stage)
    if value is None:
        # An unrecognised stage is genuinely unknown, so it scores neutral rather
        # than zero. Scoring it zero would penalise a registry adding a new phase
        # enum, which is upstream's prerogative and not evidence of irrelevance.
        return 0.5, {"stage": stage, "known": False}
    return value, {"stage": stage, "known": True}


def _recency(signal: RawSignal, config: ScanConfig, today: dt.date) -> FactorValue:
    """Linear decay across that source's own window.

    Per-source normalisation matters: a 400-day-old patent is fresh for a corpus with
    a multi-year grant lag, while a 400-day-old paper is not news at all. Comparing
    both against one global window would make patents permanently uncompetitive.
    """
    if signal.published is None:
        return None
    window = max(1, config.source_for(signal.source).window_days)
    age_days = max(0, (today - signal.published).days)
    value = max(0.0, 1.0 - (age_days / window))
    return value, {"age_days": age_days, "window_days": window,
                   "published": signal.published.isoformat()}


def _modality_fit(signal: RawSignal, config: ScanConfig) -> FactorValue:
    """Overlap with CSL's own capability set.

    This is the difference between "interesting science" and "a partnership CSL could
    actually execute". A bispecific antibody programme is actionable; a small-molecule
    programme in the same indication is a competitor to watch, not a partner to build
    with, and it should not rank alongside one.
    """
    if not config.modalities:
        return None
    haystack = " ".join(
        [signal.title, signal.summary, str(signal.payload.get("interventions", ""))]
    ).lower()
    matched = sorted({m for m in config.modalities if m in haystack})
    if not matched:
        return 0.0, {"matched": [], "modalities_checked": len(config.modalities)}
    value = 1.0 - math.exp(-len(matched) / 1.2)
    return value, {"matched": matched, "modalities_checked": len(config.modalities)}


def _corroboration(count: int) -> FactorValue:
    """How many independent sources carry the same story.

    One source is the norm and scores the baseline rather than zero — most real
    signals appear in exactly one place, and treating that as a defect would flatten
    the whole ranking. Two or more is genuine corroboration and is rewarded steeply,
    because independent confirmation is the strongest evidence this system can
    produce on its own.
    """
    n = max(1, count)
    value = {1: 0.35, 2: 0.80}.get(n, 1.0)
    return value, {"source_count": n}


def _company_context(
    signal: RawSignal, company_known: bool, company_signal_count: int
) -> FactorValue:
    """Whether this is a company the BD team already has a relationship with.

    Deliberately modest weight and deliberately two-sided. A known company with
    accumulating activity is a live opportunity; but an unattributed signal returns
    None rather than 0, so a paper with no corporate author is not punished for it.
    Weighting this too heavily would turn the Radar into a mirror of the existing
    watchlist and defeat the entire "before it becomes widely known" premise.
    """
    if not signal.company_name:
        return None
    if not company_known:
        # A new name is the point of the exercise. It scores solidly, not maximally —
        # novelty is promising, not yet evidence.
        return 0.6, {"company": signal.company_name, "known": False, "prior_signals": 0}
    value = min(1.0, 0.7 + 0.1 * min(3, company_signal_count))
    return value, {"company": signal.company_name, "known": True,
                   "prior_signals": company_signal_count}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp01(v: float) -> float:
    if math.isnan(v) or math.isinf(v):
        # A NaN reaching the weighted sum would silently poison the entire ranking
        # into NaN, and every comparison against it would quietly return False.
        return 0.0
    return max(0.0, min(1.0, v))


def signal_type_for(source: SourceId) -> SignalType:
    """Map a source onto the UI's SignalType union.

    Returns the enum, not its string value: `Signal.type` and the rationale builder
    both want a `SignalType`, and handing them a bare `str` type-checks fine against
    a StrEnum comparison while failing at runtime on `.value`.
    """
    return {
        SourceId.TRIALS: SignalType.TRIAL,
        SourceId.LITERATURE: SignalType.PUBLICATION,
        SourceId.PATENTS: SignalType.PATENT,
        SourceId.EPO: SignalType.PATENT,
        SourceId.EDGAR: SignalType.CORPORATE,
    }[source]


def tokens(text: str) -> set[str]:
    """Lowercase word set, used by dedupe's title similarity."""
    return set(_WORD.findall(text.lower()))


def priority_of(value: float, config: ScanConfig) -> Priority:
    return config.thresholds.priority_for(value)
