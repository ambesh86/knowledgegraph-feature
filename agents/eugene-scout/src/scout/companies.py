"""Company scoring — the Watchlist.

A company's score is derived entirely from the signals attributed to it. There is no
separately-maintained company record that could drift out of agreement with the
evidence, and no manual score an analyst has to remember to update. Ask "why is this
company ranked here?" and the answer is always a list of signals you can click.

The aggregate is **best signal + a bounded corroboration bonus**. Three formulas were
tried and the first two are wrong in ways worth recording:

  * *Mean of all signals* punishes coverage. A company with one strong signal outranks
    a company with one strong signal and four routine ones, so the better-documented
    company looks worse.
  * *Top-k mean* has the same defect in milder form, and a unit test caught it: a
    company with signals scoring 90/50/50 came out at 63 while a company with a single
    90 stayed at 90. Being found out about more still made a company look weaker.
  * *Sum* rewards volume — a steady stream of routine filings climbs above a single
    Phase II readout that actually matters.

So the base is the strongest signal, and additional signals can only ever add. The
bonus counts *supporting* signals — those scoring within `_SUPPORT_BAND` of the best —
rather than raw volume, so sustained strength is rewarded and a long tail of noise is
not. Extra evidence never lowers a company's rank, which is the property a BD analyst
would assume without being told.
"""
from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict

from scout.models import CompanyScore, Signal, utcnow
from scout.text import normalize_company

logger = logging.getLogger(__name__)

# A signal counts as *supporting* the company's case if it scores within this many
# points of the best one. Wide enough that a genuinely strong second programme counts,
# narrow enough that a routine filing does not.
_SUPPORT_BAND = 15.0

# Points added per supporting signal, and the ceiling on that bonus. Deliberately
# small: it breaks ties between comparable companies, it does not let anyone out-file
# their way up the list.
_SUPPORT_BONUS_EACH = 2.0
_MAX_SUPPORT_BONUS = 6.0

# Signals older than this stop contributing. A Phase II readout from 14 months ago is
# history, not a live opportunity, and leaving it in the score would keep a dormant
# company ranked as though nothing had changed.
_RELEVANCE_WINDOW_DAYS = 400


def aggregate(
    signals: list[Signal],
    *,
    now: dt.datetime,
    previous: dict[str, float] | None = None,
) -> list[CompanyScore]:
    """Build watchlist rows from scored signals.

    `previous` maps company id to the score from the 30-day-old snapshot; it produces
    `delta_30d`. Absent (first run, or no snapshot that old yet) the delta is 0.0
    rather than a fabricated movement — an arrow implying a company "moved +6" when
    there is nothing to compare against is a lie the UI would render confidently.
    """
    by_company: dict[str, list[Signal]] = defaultdict(list)
    names: dict[str, str] = {}

    for signal in signals:
        if not signal.company_id or not signal.company_name:
            continue
        if signal.dismissed:
            continue
        if signal.published and (now.date() - signal.published).days > _RELEVANCE_WINDOW_DAYS:
            continue
        by_company[signal.company_id].append(signal)
        # Keep the longest spelling seen. "Sangamo Therapeutics, Inc." is more useful
        # in a briefing than "Sangamo", and both normalise to the same identity.
        if len(signal.company_name) > len(names.get(signal.company_id, "")):
            names[signal.company_id] = signal.company_name

    out: list[CompanyScore] = []
    for company_id, group in by_company.items():
        group.sort(key=lambda s: s.score, reverse=True)
        best = group[0]
        base = best.score

        supporting = [s for s in group[1:] if s.score >= base - _SUPPORT_BAND]
        bonus = min(_MAX_SUPPORT_BONUS, _SUPPORT_BONUS_EACH * len(supporting))

        score = round(min(100.0, base + bonus), 2)
        top = [best, *supporting][:4]
        name = names[company_id]
        prior = (previous or {}).get(company_id)

        areas = sorted({s.area for s in group})
        high = sum(1 for s in group if s.priority.value == "high")
        last_seen = max(
            (s.detected_at for s in group),
            default=now,
        )

        out.append(
            CompanyScore(
                id=company_id,
                name=name,
                normalized_name=normalize_company(name),
                ticker=_first_ticker(group),
                cik=_first_cik(group),
                areas=areas,
                score=score,
                delta_30d=round(score - prior, 2) if prior is not None else 0.0,
                signal_count=len(group),
                high_priority_count=high,
                top_signal_id=top[0].id if top else None,
                last_signal_at=last_seen,
                computed_at=now,
                breakdown={
                    "base_best_signal_score": round(base, 2),
                    "best_signal_id": best.id,
                    "supporting_signals": len(supporting),
                    "support_band": _SUPPORT_BAND,
                    "support_bonus": round(bonus, 2),
                    "total_signals": len(group),
                    "contributing_signal_ids": [s.id for s in top],
                    "has_baseline": prior is not None,
                },
            )
        )

    out.sort(key=lambda c: c.score, reverse=True)
    logger.info(f"scored {len(out)} companies from {len(signals)} signals")
    return out


def _first_ticker(signals: list[Signal]) -> str | None:
    """Tickers come only from EDGAR, where they are authoritative. Never guessed from
    a company name — a wrong ticker in a BD briefing points at someone else's stock."""
    for s in signals:
        for source in s.sources:
            if source.source.value == "sec_edgar":
                ticker = s.score_breakdown.get("ticker")
                if isinstance(ticker, str) and ticker:
                    return ticker
    return None


def _first_cik(signals: list[Signal]) -> str | None:
    for s in signals:
        cik = s.score_breakdown.get("cik")
        if isinstance(cik, str) and cik:
            return cik
    return None


def previous_scores(rows: list[dict]) -> dict[str, float]:
    """Company id -> score, read from a dated snapshot for the delta calculation."""
    out: dict[str, float] = {}
    for row in rows:
        cid, score = row.get("id"), row.get("score")
        if isinstance(cid, str) and isinstance(score, (int, float)):
            out[cid] = float(score)
    return out
