"""The weekly partnership briefing.

This is the use case's headline deliverable, quoted verbatim:

    "A ranked weekly briefing showing 8-12 high-priority biotech companies with
     complementary pipeline assets, each accompanied by a plain-English rationale,
     the key data sources consulted, and a 'next action' recommendation."

Every clause of that is implemented literally: the 8-12 band, the rationale, the
sources, and the next action. The one place judgement was applied is the band itself —
if only five companies clear the bar in a quiet week, the briefing contains five. A
report padded to eight with companies the system does not actually rate teaches its
readers to distrust the ranking, and the ranking is the entire product.

The 'next action' is rule-derived, not model-generated. Each recommendation follows
from facts already established (is the company new? does it already have a high
priority signal? is it commercially attributed?), so an analyst who disagrees can see
exactly which condition produced it.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from scout.areas import get_area
from scout.models import CompanyScore, Signal, utcnow

logger = logging.getLogger(__name__)

TARGET_MIN = 8
TARGET_MAX = 12

# Below this a company is not a briefing item. It is deliberately lower than the
# `high` priority threshold: a briefing about companies, not signals, should include a
# company with several solid-but-not-exceptional signals.
_MIN_COMPANY_SCORE = 50.0


def build(
    area_id: str,
    signals: list[Signal],
    companies: list[CompanyScore],
    *,
    now: dt.datetime | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Assemble the ranked briefing for one area."""
    now = now or utcnow()
    area = get_area(area_id)
    area_label = area.label if area else area_id

    by_id: dict[str, list[Signal]] = {}
    for signal in signals:
        if signal.company_id and not signal.dismissed:
            by_id.setdefault(signal.company_id, []).append(signal)

    ranked = [c for c in companies if c.score >= _MIN_COMPANY_SCORE][:TARGET_MAX]

    entries = []
    for rank, company in enumerate(ranked, start=1):
        company_signals = sorted(by_id.get(company.id, []), key=lambda s: s.score, reverse=True)
        entries.append(_entry(rank, company, company_signals))

    unattributed = [s for s in signals if not s.company_id and not s.dismissed]
    unattributed.sort(key=lambda s: s.score, reverse=True)

    return {
        "area": area_id,
        "area_label": area_label,
        "generated_at": now.isoformat(),
        "run_id": run_id,
        "period_end": now.date().isoformat(),
        "company_count": len(entries),
        # Stated explicitly so a five-company briefing reads as a quiet week rather
        # than as a broken report.
        "below_target": len(entries) < TARGET_MIN,
        "companies": entries,
        "notable_unattributed": [
            {
                "id": s.id,
                "title": s.title,
                "type": s.type.value,
                "score": s.score,
                "priority": s.priority.value,
                "published": s.published.isoformat() if s.published else None,
                "url": s.primary_url,
            }
            for s in unattributed[:5]
        ],
        "totals": {
            "signals": len([s for s in signals if not s.dismissed]),
            "high": len([s for s in signals if s.priority.value == "high" and not s.dismissed]),
            "companies_tracked": len(companies),
        },
    }


def _entry(rank: int, company: CompanyScore, signals: list[Signal]) -> dict[str, Any]:
    top = signals[0] if signals else None
    sources = sorted({src.source.value for s in signals for src in s.sources})

    return {
        "rank": rank,
        "company_id": company.id,
        "company": company.name,
        "ticker": company.ticker,
        "score": company.score,
        "delta_30d": company.delta_30d,
        "signal_count": company.signal_count,
        "high_priority_count": company.high_priority_count,
        "areas": company.areas,
        "rationale": _rationale(company, top),
        "sources_consulted": sources,
        "next_action": _next_action(company, top),
        "evidence": [
            {
                "id": s.id,
                "title": s.title,
                "type": s.type.value,
                "score": s.score,
                "priority": s.priority.value,
                "published": s.published.isoformat() if s.published else None,
                "url": s.primary_url,
                "sources": [{"source": x.source.value, "url": x.url} for x in s.sources],
            }
            for s in signals[:3]
        ],
    }


def _rationale(company: CompanyScore, top: Signal | None) -> str:
    """Prefer the top signal's own rationale — it is already the explained,
    verified prose — and fall back to a summary composed from the company aggregate."""
    if top and top.rationale:
        return top.rationale
    parts = [
        f"{company.name} scores {company.score:.0f}/100 across "
        f"{company.signal_count} signal(s) in {', '.join(company.areas) or 'the scanned areas'}."
    ]
    if company.high_priority_count:
        parts.append(f"{company.high_priority_count} of these are high priority.")
    if company.delta_30d:
        direction = "up" if company.delta_30d > 0 else "down"
        parts.append(f"Score is {direction} {abs(company.delta_30d):.0f} points over 30 days.")
    return " ".join(parts)


def _next_action(company: CompanyScore, top: Signal | None) -> str:
    """Rule-derived recommendation.

    Ordered most-specific first so the strongest applicable condition wins. Every
    branch corresponds to a fact the analyst can check in the same row.
    """
    if company.high_priority_count >= 2:
        return (
            "Prioritise for outreach — multiple high-priority signals indicate active, "
            "accelerating programmes. Brief the therapeutic area lead this week."
        )
    if company.delta_30d >= 5:
        return (
            f"Review the {company.delta_30d:.0f}-point 30-day rise before the next pipeline "
            "meeting; momentum suggests a development or financing event."
        )
    if top and top.type.value == "Corporate":
        return (
            "Read the SEC filing in full — a registration or material-event filing often "
            "precedes a partnering window."
        )
    if top and top.type.value == "Trial":
        return (
            "Add to the trial watch list and diarise the primary completion date; "
            "consider outreach ahead of readout."
        )
    if top and top.type.value == "Patent":
        return (
            "Route to IP for a freedom-to-operate check against the overlapping "
            "programme before any approach."
        )
    if company.signal_count == 1:
        return "Monitor — single signal so far. Revisit if a second independent signal appears."
    return "Maintain on the watchlist; no action required this cycle."


def to_markdown(digest: dict[str, Any]) -> str:
    """Render the briefing as Markdown.

    Markdown because the UI already has a publishing path that takes it — the
    `artifacts` table plus `lib/atlas/artifacts.ts` turn Markdown into a shareable
    page with Word/PDF/HTML export. Emitting anything else would mean writing a
    second renderer to get capability that already exists.
    """
    lines: list[str] = [
        f"# Partnership Briefing — {digest['area_label']}",
        "",
        f"_Generated {digest['generated_at']} · "
        f"{digest['totals']['signals']} signals · "
        f"{digest['totals']['high']} high priority_",
        "",
    ]

    if digest.get("below_target"):
        lines += [
            f"> Only {digest['company_count']} companies cleared the scoring threshold this "
            f"period (target is {TARGET_MIN}–{TARGET_MAX}). The list is short because the "
            "evidence was, not because the scan was incomplete.",
            "",
        ]

    for entry in digest["companies"]:
        ticker = f" ({entry['ticker']})" if entry.get("ticker") else ""
        delta = entry.get("delta_30d") or 0
        delta_str = f" · Δ30d {delta:+.0f}" if delta else ""
        lines += [
            f"## {entry['rank']}. {entry['company']}{ticker} — {entry['score']:.0f}/100{delta_str}",
            "",
            entry["rationale"],
            "",
            f"**Next action:** {entry['next_action']}",
            "",
            f"**Sources consulted:** {', '.join(entry['sources_consulted']) or 'none'}",
            "",
        ]
        if entry["evidence"]:
            lines.append("**Evidence:**")
            lines.append("")
            for ev in entry["evidence"]:
                published = f" ({ev['published']})" if ev.get("published") else ""
                lines.append(
                    f"- [{ev['title']}]({ev['url']}) — {ev['type']}, "
                    f"score {ev['score']:.0f}{published}"
                )
            lines.append("")

    if digest.get("notable_unattributed"):
        lines += ["## Notable signals without a company attribution", ""]
        for item in digest["notable_unattributed"]:
            lines.append(f"- [{item['title']}]({item['url']}) — {item['type']}, score {item['score']:.0f}")
        lines.append("")

    return "\n".join(lines)
