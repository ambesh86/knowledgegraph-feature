"""Human-in-the-loop confidence flagging.

The use case is explicit about this one: the orchestrator should "flag low-confidence
outputs for human review rather than suppressing uncertainty, preserving analyst trust
in the system."

Both halves of that sentence matter, and the second half is the harder discipline. The
tempting design is to hide weak signals — a shorter, cleaner Radar looks better. But an
analyst who later discovers the system quietly dropped something relevant stops
trusting everything it *did* show, and that trust is the whole product. So nothing is
suppressed here. Uncertain signals are ranked normally and carry a visible marker
saying why they are uncertain.

The four conditions below are all *structural* — they are properties of the evidence,
not guesses about it. Each one is something the system genuinely does not know, rather
than something it suspects.
"""
from __future__ import annotations

import datetime as dt

from scout.config import ScanConfig
from scout.models import RationaleKind, RawSignal, ReviewReason, ScoreResult

# How close to a threshold counts as "on the boundary". A signal at 74.8 and one at
# 75.2 differ by noise but land in different priority bands, and an analyst reading
# only the HIGH tier would see one and not the other.
BORDERLINE_MARGIN = 2.0


def assess(
    signal: RawSignal,
    result: ScoreResult,
    config: ScanConfig,
    *,
    source_count: int,
    rationale_kind: RationaleKind,
    llm_was_attempted: bool,
) -> list[ReviewReason]:
    """Which uncertainties, if any, this signal carries. Pure — no I/O, no clock."""
    reasons: list[ReviewReason] = []

    # 1. Sitting on a band boundary. The number is not wrong; the band is arbitrary
    #    at the margin, and the analyst should know they are near the line.
    for threshold in (config.thresholds.high, config.thresholds.med):
        if abs(result.score - threshold) <= BORDERLINE_MARGIN:
            reasons.append(ReviewReason.BORDERLINE_SCORE)
            break

    # 2. Thin on every axis at once: no corroboration, a minimal topical match, and
    #    nobody to attribute it to. In plain terms — we cannot confirm it, it barely
    #    matches the area, and we cannot tell you whose it is.
    #
    #    All three conditions are required, and that was calibrated against real data
    #    rather than guessed. The first version asked only for one source and one
    #    keyword, which fired on 65% of a live corpus: single-source is the norm (the
    #    `corroboration` factor already prices it in), so the flag marked the majority
    #    and therefore meant nothing. A marker on two rows in three is decoration an
    #    analyst learns to scroll past. Requiring the missing attribution as well
    #    brings it to ~30% and each flag points at something specific.
    specific = config.specific_keywords(signal.keywords)
    if source_count <= 1 and len(specific) <= 1 and not signal.company_name:
        reasons.append(ReviewReason.THIN_EVIDENCE)

    # 3. The LLM produced prose and `rationale._verify` rejected it — most often for
    #    a fabricated number. The template shown instead is correct, but the
    #    rejection is itself information: the model found this signal hard to
    #    describe without inventing something.
    if llm_was_attempted and rationale_kind is RationaleKind.TEMPLATE:
        reasons.append(ReviewReason.UNVERIFIED_RATIONALE)

    # 4. Undated. Collectors drop these, so it should be unreachable in practice —
    #    kept as a backstop because an undated item is precisely the kind that once
    #    appeared under a heading claiming freshness.
    if signal.published is None:
        reasons.append(ReviewReason.UNDATED)

    return reasons


def summarise(signals: list[tuple[str, list[ReviewReason]]]) -> dict[str, int]:
    """Counts per reason, for the run manifest and the Settings panel."""
    out: dict[str, int] = {}
    for _, reasons in signals:
        for reason in reasons:
            out[reason.value] = out.get(reason.value, 0) + 1
    return out


def within_window(published: dt.date | None, today: dt.date, days: int) -> bool:
    """Re-exported for callers that need the same freshness notion as the collectors."""
    if published is None:
        return False
    return 0 <= (today - published).days <= days
