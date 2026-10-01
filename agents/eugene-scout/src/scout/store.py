"""Repository layer — the only module that knows how domain objects map onto S3.

Everything above this line thinks in `Signal`/`CompanyScore`/`ScanRun`; everything
below thinks in keys and gzipped JSONL. Keeping the translation in one place is what
lets the storage layout change (partitioning, Parquet, a different bucket) without the
pipeline or the API noticing.

Two write paths, matching the two tiers:

    stage_raw()      raw/      write-once, per run, untouched upstream payloads
    publish_area()   curated/  rewritten per scan, plus an immutable dated snapshot

`publish_area` writes the snapshot *before* the live objects. If the process dies
mid-publish, the worst case is a snapshot with no corresponding live update — harmless
and self-correcting on the next run. The reverse order could leave the live index
updated with no snapshot behind it, silently breaking the 30-day delta whose entire
basis is that a snapshot exists for every published state.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from scout.config import ScanConfig
from scout.models import CompanyScore, RawSignal, ScanRun, Signal, utcnow
from scout.storage import (
    NotFound,
    Storage,
    key_curated_companies,
    key_curated_index,
    key_curated_signals,
    key_digest,
    key_raw,
    key_run,
    key_snapshot,
    key_dd_brief,
    key_dd_brief_dated,
    key_dd_index,
)

logger = logging.getLogger(__name__)

# How far back to look for the baseline used by `delta_30d`. Snapshots are daily, but
# a scan can be skipped (weekend outage, redeploy), so the lookup walks backwards
# rather than demanding a snapshot exactly 30 days old.
_DELTA_TARGET_DAYS = 30
_DELTA_SEARCH_SPAN = 14


class Store:
    """Domain-level persistence over `Storage`."""

    def __init__(self, storage: Storage | None = None) -> None:
        self.s3 = storage or Storage()

    # -- config ------------------------------------------------------------

    def load_config(self) -> ScanConfig:
        """Read the BD-editable config, falling back to defaults on cold start.

        A malformed stored config falls back to defaults rather than refusing to
        boot: the alternative is a bad Settings-page save taking the whole scanner
        offline until someone edits an S3 object by hand.
        """
        raw = self.s3.load_config_raw()
        if raw is None:
            logger.info("no stored scan config; using defaults")
            return ScanConfig()
        try:
            return ScanConfig.model_validate(raw)
        except Exception as e:  # noqa: BLE001
            logger.error(f"stored scan config is invalid ({e}); falling back to defaults")
            return ScanConfig()

    def save_config(self, config: ScanConfig) -> ScanConfig:
        self.s3.save_config_raw(config.model_dump(mode="json"))
        logger.info(f"saved scan config v{config.version}")
        return config

    # -- staging tier ------------------------------------------------------

    def stage_raw(
        self, run_id: str, area: str, source: str, day: dt.date, signals: list[RawSignal]
    ) -> str | None:
        """Persist untouched collector output. Skips empty sets — an object containing
        zero rows is pure cost and its absence carries the same information."""
        if not signals:
            return None
        key = key_raw(run_id, area, source, day)
        rows = [s.model_dump(mode="json") for s in signals]
        uri, count = self.s3.put_jsonl_gz(key, rows)
        logger.debug(f"staged {count} raw record(s) -> {uri}")
        return uri

    def load_raw(self, run_id: str, area: str, source: str, day: dt.date) -> list[dict[str, Any]]:
        """Replay staged records. This is what makes a scoring change re-runnable
        over history without re-crawling the public APIs."""
        return self.s3.get_jsonl_gz_or_empty(key_raw(run_id, area, source, day))

    # -- curated tier ------------------------------------------------------

    def load_signals(self, area: str) -> list[Signal]:
        """Current curated signals for one area.

        Rows that fail validation are dropped with a warning rather than aborting the
        load. A single corrupt record should cost one Radar row, not the whole panel.
        """
        rows = self.s3.get_jsonl_gz_or_empty(key_curated_signals(area))
        out: list[Signal] = []
        for row in rows:
            try:
                out.append(Signal.model_validate(row))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"skipping malformed curated signal in {area}: {e}")
        return out

    def load_companies(self, area: str) -> list[CompanyScore]:
        rows = self.s3.get_jsonl_gz_or_empty(key_curated_companies(area))
        out: list[CompanyScore] = []
        for row in rows:
            try:
                out.append(CompanyScore.model_validate(row))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"skipping malformed company row in {area}: {e}")
        return out

    def publish_area(
        self,
        area: str,
        signals: list[Signal],
        companies: list[CompanyScore],
        *,
        day: dt.date,
        run_id: str,
    ) -> dict[str, Any]:
        """Write the final tier for one area: snapshot, then signals, companies, index.

        Returns the index object, which the serving layer loads into memory.
        """
        signal_rows = [s.model_dump(mode="json") for s in signals]
        company_rows = [c.model_dump(mode="json") for c in companies]

        # Immutable dated copy first — see the module docstring on ordering.
        self.s3.put_jsonl_gz(key_snapshot(area, day), signal_rows)

        self.s3.put_jsonl_gz(key_curated_signals(area), signal_rows)
        self.s3.put_jsonl_gz(key_curated_companies(area), company_rows)

        index = _build_index(area, signals, companies, day=day, run_id=run_id)
        self.s3.put_json(key_curated_index(area), index)

        manifest = set(self.s3.load_area_manifest())
        if area not in manifest:
            manifest.add(area)
            self.s3.save_area_manifest(sorted(manifest))

        logger.info(
            f"published area={area}: {len(signals)} signal(s), {len(companies)} company row(s)"
        )
        return index

    def load_index(self, area: str) -> dict[str, Any] | None:
        try:
            return self.s3.get_json(key_curated_index(area))
        except NotFound:
            return None

    def known_areas(self) -> list[str]:
        return self.s3.load_area_manifest()

    # -- deltas ------------------------------------------------------------

    def baseline_company_scores(self, area: str, today: dt.date) -> dict[str, float]:
        """Company scores from roughly 30 days ago, for `delta_30d`.

        Walks outward from the target date because daily snapshots are best-effort,
        not guaranteed. Returns empty when nothing suitable exists, which callers
        render as a delta of zero rather than inventing movement.
        """
        target = today - dt.timedelta(days=_DELTA_TARGET_DAYS)
        for offset in range(0, _DELTA_SEARCH_SPAN + 1):
            for candidate in {target + dt.timedelta(days=offset), target - dt.timedelta(days=offset)}:
                if candidate >= today:
                    continue
                rows = self.s3.get_jsonl_gz_or_empty(key_snapshot(area, candidate))
                if not rows:
                    continue
                from scout.companies import aggregate

                signals = []
                for row in rows:
                    try:
                        signals.append(Signal.model_validate(row))
                    except Exception:  # noqa: BLE001,S112
                        continue
                if not signals:
                    continue
                as_of = dt.datetime.combine(candidate, dt.time(), tzinfo=dt.UTC)
                historical = aggregate(signals, now=as_of, previous=None)
                logger.info(f"delta baseline for {area} taken from {candidate.isoformat()}")
                return {c.id: c.score for c in historical}
        logger.info(f"no delta baseline available for {area}; deltas will be zero")
        return {}

    # -- runs --------------------------------------------------------------

    def save_run(self, run: ScanRun) -> None:
        payload = run.model_dump(mode="json")
        self.s3.put_json(key_run(run.run_id), payload)
        self.s3.save_latest_run(run.summary())

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        try:
            return self.s3.get_json(key_run(run_id))
        except NotFound:
            return None

    def latest_run(self) -> dict[str, Any] | None:
        return self.s3.load_latest_run()

    def recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for run_id in self.s3.list_run_ids(limit=limit):
            run = self.load_run(run_id)
            if run:
                out.append(_run_summary(run))
        return out

    # -- digests -----------------------------------------------------------

    def save_digest(self, area: str, day: dt.date, digest: dict[str, Any]) -> str:
        return self.s3.put_json(key_digest(area, day), digest)

    def load_digest(self, area: str, day: dt.date) -> dict[str, Any] | None:
        try:
            return self.s3.get_json(key_digest(area, day))
        except NotFound:
            return None
    # -- due diligence (Use Case 2) -----------------------------------------

    def save_brief(self, target_id: str, brief: dict[str, Any], day: dt.date | None = None) -> str:
        """Persist a brief at its stable address AND as a dated record.

        Both writes matter and they are not redundant: the stable key is what a link
        in an email or a UI route points at, and the dated key is what makes the brief
        auditable six months later when someone asks what was known at the time.
        """
        day = day or utcnow().date()
        uri = self.s3.put_json(key_dd_brief(target_id), brief)
        self.s3.put_json(key_dd_brief_dated(target_id, day), brief)

        # Maintain the target index. Read-modify-write is safe here because diligence
        # is analyst-triggered and low-frequency; the scan path, which is concurrent,
        # deliberately uses a different mechanism.
        index = self.s3.get_json_or(key_dd_index(), {"targets": []})
        entries = [t for t in index.get("targets", []) if t.get("id") != target_id]
        entries.insert(0, {
            "id": target_id,
            "company": (brief.get("target") or {}).get("company"),
            "asset": (brief.get("target") or {}).get("asset"),
            "label": (brief.get("target") or {}).get("label"),
            "generated_at": brief.get("generated_at"),
            "confidence_band": (brief.get("confidence") or {}).get("band"),
            "confidence_score": (brief.get("confidence") or {}).get("score"),
            "signals_total": (brief.get("coverage") or {}).get("signals_total"),
        })
        self.s3.put_json(key_dd_index(), {"targets": entries[:500]})
        return uri

    def load_brief(self, target_id: str) -> dict[str, Any] | None:
        return self.s3.get_json_or(key_dd_brief(target_id), None)

    def load_brief_dated(self, target_id: str, day: dt.date) -> dict[str, Any] | None:
        return self.s3.get_json_or(key_dd_brief_dated(target_id, day), None)

    def list_briefs(self) -> list[dict[str, Any]]:
        return (self.s3.get_json_or(key_dd_index(), {"targets": []}) or {}).get("targets", [])


# ---------------------------------------------------------------------------
# Index construction
# ---------------------------------------------------------------------------


def _build_index(
    area: str,
    signals: list[Signal],
    companies: list[CompanyScore],
    *,
    day: dt.date,
    run_id: str,
) -> dict[str, Any]:
    """The per-area object the API serves from.

    It carries the full signal and company rows, not just pointers. That is what makes
    a single GET sufficient to answer every Radar and Watchlist query, and it is
    affordable precisely because the corpus is small — a few hundred KB gzipped per
    area. If it ever stops being small, this is the seam where pagination or a real
    query engine goes.
    """
    counts = {"high": 0, "med": 0, "watch": 0}
    by_type: dict[str, int] = {}
    for s in signals:
        counts[s.priority.value] = counts.get(s.priority.value, 0) + 1
        by_type[s.type.value] = by_type.get(s.type.value, 0) + 1

    return {
        "area": area,
        "generated_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "snapshot_date": day.isoformat(),
        "run_id": run_id,
        "signal_count": len(signals),
        "company_count": len(companies),
        "priority_counts": counts,
        "type_counts": by_type,
        "signals": [s.model_dump(mode="json") for s in signals],
        "companies": [c.model_dump(mode="json") for c in companies],
    }


def _run_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Compact a stored run manifest for list views. The full source_reports payload
    is large and the Settings panel only needs which sources failed."""
    reports = run.get("source_reports") or []
    return {
        "run_id": run.get("run_id"),
        "trigger": run.get("trigger"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "areas": run.get("areas") or [],
        "signals_new": run.get("signals_new", 0),
        "signals_kept": run.get("signals_kept", 0),
        "companies_scored": run.get("companies_scored", 0),
        "error": run.get("error"),
        "sources": [
            {
                "source": r.get("source"),
                "area": r.get("area"),
                "ok": r.get("ok"),
                "fetched": r.get("fetched", 0),
                "kept": r.get("kept", 0),
                "duration_ms": r.get("duration_ms", 0),
                "error": r.get("error"),
            }
            for r in reports
        ],
    }

