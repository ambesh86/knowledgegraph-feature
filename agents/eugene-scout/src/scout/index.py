"""In-memory query index — what replaces the database we chose not to have.

S3 is the system of record, but S3 cannot answer "high-priority trials in hemophilia
from the last week, ranked". This module holds the curated index objects in process
memory and does that filtering in Python.

That is a legitimate design at this scale and a bad one past it, so the boundary is
worth stating: a few thousand signals across all areas is a few MB of dicts, filtered
in well under a millisecond. If the corpus grew by two orders of magnitude the honest
answer would be a query engine, and this module is the seam where one would go.

Concurrency: the index is rebuilt wholesale after each scan and swapped in atomically
by rebinding a single attribute. Readers therefore never observe a half-updated index,
and no lock is needed on the read path — which matters because reads are every Radar
page load and writes are once a night.
"""
from __future__ import annotations

import datetime as dt
import logging
import threading
from typing import Any

from scout.models import Priority, SignalType
from scout.store import Store

logger = logging.getLogger(__name__)


class AreaIndex:
    """Immutable view of one area's curated data."""

    __slots__ = ("area", "generated_at", "run_id", "signals", "companies",
                 "priority_counts", "type_counts")

    def __init__(self, payload: dict[str, Any]) -> None:
        self.area: str = payload.get("area", "")
        self.generated_at: str | None = payload.get("generated_at")
        self.run_id: str | None = payload.get("run_id")
        self.signals: list[dict[str, Any]] = payload.get("signals") or []
        self.companies: list[dict[str, Any]] = payload.get("companies") or []
        self.priority_counts: dict[str, int] = payload.get("priority_counts") or {}
        self.type_counts: dict[str, int] = payload.get("type_counts") or {}


class SignalIndex:
    """Process-wide index across every area."""

    def __init__(self, store: Store | None = None) -> None:
        self._store = store or Store()
        self._areas: dict[str, AreaIndex] = {}
        self._loaded_at: dt.datetime | None = None
        self._lock = threading.Lock()  # guards refresh, not reads

    # -- lifecycle ---------------------------------------------------------

    def refresh(self, areas: list[str] | None = None) -> int:
        """Reload from S3. Called at startup and after every scan.

        Builds the replacement dict fully before swapping it in, so a failure
        mid-refresh leaves the previous index serving rather than a partial one.
        """
        with self._lock:
            wanted = areas if areas is not None else self._store.known_areas()
            rebuilt: dict[str, AreaIndex] = dict(self._areas)
            for area in wanted:
                payload = self._store.load_index(area)
                if payload is None:
                    logger.info(f"no curated index yet for area={area}")
                    continue
                rebuilt[area] = AreaIndex(payload)
            self._areas = rebuilt
            self._loaded_at = dt.datetime.now(dt.UTC).replace(microsecond=0)
            total = sum(len(a.signals) for a in self._areas.values())
            logger.info(f"index refreshed: {len(self._areas)} area(s), {total} signal(s)")
            return total

    @property
    def loaded_at(self) -> str | None:
        return self._loaded_at.isoformat() if self._loaded_at else None

    @property
    def areas(self) -> list[str]:
        return sorted(self._areas)

    def is_empty(self) -> bool:
        return not any(a.signals for a in self._areas.values())

    # -- queries -----------------------------------------------------------

    def query_signals(
        self,
        *,
        areas: list[str] | None = None,
        signal_type: str | None = None,
        priority: str | None = None,
        company_id: str | None = None,
        since: dt.date | None = None,
        search: str | None = None,
        include_dismissed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
        """Filter, rank and page. Returns (rows, total_matching, priority_counts).

        `priority_counts` is computed over the *type/date/search-filtered* set but
        before the priority filter itself is applied — otherwise the filter chips
        would show "0 medium" the moment you selected "high", which is both useless
        and confusing.
        """
        selected = self._select_areas(areas)
        rows: list[dict[str, Any]] = []
        for area in selected:
            rows.extend(self._areas[area].signals)

        if not include_dismissed:
            rows = [r for r in rows if not r.get("dismissed")]
        if signal_type and signal_type.lower() != "all":
            rows = [r for r in rows if r.get("type") == signal_type]
        if company_id:
            rows = [r for r in rows if r.get("company_id") == company_id]
        if since:
            iso = since.isoformat()
            rows = [r for r in rows if (r.get("published") or "") >= iso]
        if search:
            needle = search.lower().strip()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("title", "")).lower()
                    or needle in str(r.get("summary", "")).lower()
                    or needle in str(r.get("company_name") or "").lower()
                ]

        counts = {"high": 0, "med": 0, "watch": 0}
        for r in rows:
            key = str(r.get("priority", "watch"))
            counts[key] = counts.get(key, 0) + 1

        if priority and priority.lower() != "all":
            rows = [r for r in rows if r.get("priority") == priority]

        # Score first, then recency. Two signals of equal strategic weight are
        # usefully ordered by which happened more recently.
        rows.sort(
            key=lambda r: (float(r.get("score") or 0), str(r.get("published") or "")),
            reverse=True,
        )
        total = len(rows)
        start = max(0, offset)
        return rows[start:start + max(1, limit)], total, counts

    def get_signal(self, signal_id: str) -> dict[str, Any] | None:
        for area in self._areas.values():
            for row in area.signals:
                if row.get("id") == signal_id:
                    return row
        return None

    def query_companies(
        self,
        *,
        areas: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Watchlist rows.

        A company active in two areas has a row in each area's index; they are merged
        on id, keeping the higher-scoring row and unioning the areas. Returning both
        would show the same company twice with different scores, which reads as a bug
        regardless of how defensible each number is on its own.
        """
        selected = self._select_areas(areas)
        merged: dict[str, dict[str, Any]] = {}
        for area in selected:
            for row in self._areas[area].companies:
                cid = str(row.get("id") or "")
                if not cid:
                    continue
                existing = merged.get(cid)
                if existing is None:
                    merged[cid] = dict(row)
                    continue
                if float(row.get("score") or 0) > float(existing.get("score") or 0):
                    merged[cid] = {**row, "areas": existing.get("areas") or []}
                combined = set(merged[cid].get("areas") or []) | set(row.get("areas") or [])
                merged[cid]["areas"] = sorted(combined)
                merged[cid]["signal_count"] = (
                    int(existing.get("signal_count") or 0) + int(row.get("signal_count") or 0)
                )

        rows = list(merged.values())
        if search:
            needle = search.lower().strip()
            rows = [r for r in rows if needle in str(r.get("name", "")).lower()]
        rows.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
        total = len(rows)
        start = max(0, offset)
        return rows[start:start + max(1, limit)], total

    def stats(self, areas: list[str] | None = None) -> dict[str, Any]:
        """Headline numbers for the Today view."""
        selected = self._select_areas(areas)
        signals = [r for a in selected for r in self._areas[a].signals if not r.get("dismissed")]
        counts = {"high": 0, "med": 0, "watch": 0}
        for r in signals:
            counts[str(r.get("priority", "watch"))] = counts.get(str(r.get("priority", "watch")), 0) + 1
        generated: list[str] = [
            g for g in (self._areas[a].generated_at for a in selected) if g
        ]
        return {
            "areas": selected,
            "signal_count": len(signals),
            "priority_counts": counts,
            "company_count": len({r.get("company_id") for r in signals if r.get("company_id")}),
            "generated_at": max(generated) if generated else None,
        }

    def freshness(self, areas: list[str] | None = None) -> dict[str, Any]:
        """How current the corpus is, per source, from the data itself.

        Every date here is **extracted from the upstream records**, not asserted by
        this service: `latest_published` is the newest publication date any signal
        from that source actually carries. That distinction is the whole point — a
        panel can truthfully say "scanned 20 minutes ago" while showing literature
        whose newest item is three weeks old, and an analyst reading only the scan
        time would draw the wrong conclusion about how current the field is.

        So both are reported: when we last *looked*, and how recent the newest thing
        we *found* is. They answer different questions and neither substitutes for
        the other.
        """
        selected = self._select_areas(areas)
        rows = [r for a in selected for r in self._areas[a].signals if not r.get("dismissed")]

        per_source: dict[str, dict[str, Any]] = {}
        for row in rows:
            published = row.get("published")
            for src in row.get("sources") or []:
                name = str(src.get("source") or "")
                if not name:
                    continue
                entry = per_source.setdefault(
                    name, {"source": name, "latest_published": None, "signal_count": 0}
                )
                entry["signal_count"] += 1
                # Prefer the citation's own date; fall back to the merged signal's.
                candidate = src.get("published") or published
                if candidate and (
                    entry["latest_published"] is None or candidate > entry["latest_published"]
                ):
                    entry["latest_published"] = candidate

        newest = max((r.get("published") or "" for r in rows), default="") or None
        oldest = min((r.get("published") or "9999" for r in rows), default="") or None

        return {
            "today": dt.datetime.now(dt.UTC).date().isoformat(),
            "index_loaded_at": self.loaded_at,
            "areas": selected,
            "signal_count": len(rows),
            "newest_signal_date": newest,
            "oldest_signal_date": None if oldest == "9999" else oldest,
            "sources": sorted(per_source.values(), key=lambda s: s["source"]),
        }

    def new_since(self, areas: list[str] | None, since: dt.datetime) -> dict[str, int]:
        """How much has appeared since a timestamp — powers "since you last looked".

        Counted on `detected_at` (when this scanner first saw it), not `published`.
        A paper published last week that we only indexed this morning is genuinely new
        *to the analyst*, which is the question the panel is answering.
        """
        selected = self._select_areas(areas)
        iso = since.isoformat()
        new_signals = 0
        new_high = 0
        for area in selected:
            for row in self._areas[area].signals:
                if row.get("dismissed"):
                    continue
                if str(row.get("detected_at") or "") > iso:
                    new_signals += 1
                    if row.get("priority") == "high":
                        new_high += 1
        return {"new_signals": new_signals, "new_high_priority": new_high}

    # -- helpers -----------------------------------------------------------

    def _select_areas(self, areas: list[str] | None) -> list[str]:
        if not areas:
            return sorted(self._areas)
        return [a for a in areas if a in self._areas]


def valid_type(value: str | None) -> str | None:
    """Validate a `type` filter against the enum, ignoring unknown values.

    Ignoring rather than erroring: a stale bookmark carrying an old filter should
    show the unfiltered Radar, not a 400 page.
    """
    if not value or value.lower() == "all":
        return None
    for member in SignalType:
        if member.value.lower() == value.lower():
            return member.value
    return None


def valid_priority(value: str | None) -> str | None:
    if not value or value.lower() == "all":
        return None
    for member in Priority:
        if member.value.lower() == value.lower():
            return member.value
    return None
