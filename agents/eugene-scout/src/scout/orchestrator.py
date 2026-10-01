"""Scan orchestration — collect, stage, score, publish.

This is the "orchestrator agent" of the use case, implemented as deterministic control
flow rather than as an LLM planning loop. The steps are fixed, the order matters, and
nothing about the sequence benefits from being re-decided on every run: an agent that
occasionally chooses to skip deduplication is not more capable, it is less reliable.

Pipeline, per area:

    collect (4 sources, concurrent)   → RawSignal[]  + SourceReport[]
    stage to S3 raw/                  → write-once audit copy, before any judgement
    enrich                            → company attribution, keyword re-match
    relevance gate                    → drop topically-adjacent noise
    identity dedupe                   → collapse re-fetches within the run
    cross-source merge                → corroboration groups
    score                             → pure function, no I/O
    rationale                         → prose only; LLM fenced, template fallback
    carry forward                     → preserve first_seen and dismissals
    company aggregate                 → watchlist rows with 30-day deltas
    publish to S3 curated/            → snapshot, signals, companies, index

Staging happens **before** enrichment or scoring, deliberately. The raw tier must
record what the upstream actually said, not what this pipeline concluded about it —
otherwise a bug in enrichment silently corrupts the archive that exists to let us
recover from bugs in enrichment.

Failure policy: a source failing degrades that source. An *area* failing degrades that
area. Only a failure to publish anything at all marks the run failed. A morning
briefing missing its patent column is useful; no briefing is not.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from scout import config as cfg
from scout.areas import Area, enabled_areas
from scout.collectors import build as build_collector
from scout.companies import aggregate as aggregate_companies
from scout.config import ScanConfig
from scout.dedupe import dedupe_identity, group_corroborated, primary_of
from scout.enrich import company_id_for, enrich, is_relevant
from scout.models import (
    RationaleKind,
    RawSignal,
    RunStatus,
    ScanRun,
    Signal,
    SignalSource,
    SourceId,
    SourceReport,
    utcnow,
)
from scout.graph import GraphClient
from scout.rationale import build as build_rationale
from scout.rationale import llm_configured
from scout.review import assess as assess_review
from scout.scoring import score as score_signal, signal_type_for
from scout.store import Store

logger = logging.getLogger(__name__)


def new_run_id(now: dt.datetime | None = None) -> str:
    """Timestamp-prefixed so lexical ordering of S3 prefixes is chronological, which
    is what lets `list_run_ids` sort without reading every manifest.

    The suffix is not decoration. The timestamp has second precision, and two runs
    starting within the same second — a cron firing while an operator clicks Rescan —
    would otherwise share an id and overwrite each other's manifest. The suffix breaks
    ties within one second without disturbing the sort.

    Eight hex characters, not four. Four (65,536 values) is ample for the two or three
    runs that could realistically collide in production, but it is narrow enough that
    drawing a couple of hundred ids hits a birthday collision about a quarter of the
    time — which showed up as a flaky test. Widening it costs nothing and removes the
    question entirely.
    """
    stamp = (now or utcnow()).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


class Orchestrator:
    def __init__(self, store: Store | None = None, graph: GraphClient | None = None) -> None:
        self.store = store or Store()
        # One client per orchestrator so its term cache and its "graph is down"
        # latch are shared across every area in a run.
        self.graph = graph if graph is not None else GraphClient()

    def run(
        self,
        *,
        trigger: str = "manual",
        areas: list[str] | None = None,
        today: dt.date | None = None,
        run_id: str | None = None,
    ) -> ScanRun:
        started = utcnow()
        today = today or started.date()
        run_id = run_id or new_run_id(started)
        config = self.store.load_config()

        selected = self._select_areas(config, areas)
        run = ScanRun(
            run_id=run_id,
            trigger=trigger,  # type: ignore[arg-type]
            status=RunStatus.RUNNING,
            started_at=started,
            areas=[a.id for a in selected],
        )
        self.store.save_run(run)
        logger.info(f"run {run_id} started ({trigger}) over {len(selected)} area(s)")

        if not selected:
            run.status = RunStatus.FAILED
            run.error = "no areas enabled"
            run.finished_at = utcnow()
            self.store.save_run(run)
            return run

        published_any = False
        for area in selected:
            try:
                stats = self._run_area(area, config, today=today, run_id=run_id, run=run)
                published_any = True
                run.signals_fetched += stats["fetched"]
                run.signals_kept += stats["kept"]
                run.signals_new += stats["new"]
                run.signals_updated += stats["updated"]
                run.companies_scored += stats["companies"]
                run.signals_needing_review += stats["needs_review"]
                run.graph_entities_linked += stats["graph_linked"]
            except Exception as e:  # noqa: BLE001 - one area must not sink the run
                logger.exception(f"area {area.id} failed")
                run.source_reports.append(
                    SourceReport(
                        source=SourceId.TRIALS,
                        area=area.id,
                        ok=False,
                        error=f"area pipeline failed: {type(e).__name__}: {e}"[:500],
                    )
                )

        failed_sources = [r for r in run.source_reports if not r.ok]
        if not published_any:
            run.status = RunStatus.FAILED
            run.error = "every area failed"
        elif failed_sources:
            run.status = RunStatus.DEGRADED
        else:
            run.status = RunStatus.OK

        run.finished_at = utcnow()
        self.store.save_run(run)
        logger.info(
            f"run {run_id} {run.status.value}: kept={run.signals_kept} new={run.signals_new} "
            f"companies={run.companies_scored} in {run.duration_ms}ms"
        )
        return run

    # -- per area ----------------------------------------------------------

    def _run_area(
        self,
        area: Area,
        config: ScanConfig,
        *,
        today: dt.date,
        run_id: str,
        run: ScanRun,
    ) -> dict[str, int]:
        raw, reports = self._collect(area, config, today=today)
        run.source_reports.extend(reports)

        # Stage before judging. See the module docstring.
        for source in SourceId:
            batch = [s for s in raw if s.source == source]
            self.store.stage_raw(run_id, area.id, source.value, today, batch)

        enriched = [enrich(s, area, config) for s in raw]

        relevant: list[RawSignal] = []
        rejected = 0
        for signal in enriched:
            keep, reason = is_relevant(signal, config)
            if keep:
                relevant.append(signal)
            else:
                rejected += 1
                logger.debug(f"gate rejected {signal.external_id}: {reason}")
        if rejected:
            logger.info(f"{area.id}: relevance gate rejected {rejected} record(s)")

        deduped = dedupe_identity(relevant)
        groups = group_corroborated(deduped)

        existing = {s.id: s for s in self.store.load_signals(area.id)}
        known_companies = self._known_companies(existing)

        signals: list[Signal] = []
        now = utcnow()
        for group in groups:
            signals.append(
                self._build_signal(
                    group,
                    area=area,
                    config=config,
                    today=today,
                    now=now,
                    run_id=run_id,
                    existing=existing,
                    known_companies=known_companies,
                )
            )

        new_count = sum(1 for s in signals if s.first_seen_run == run_id)
        updated = len(signals) - new_count

        baseline = self.store.baseline_company_scores(area.id, today)
        companies = aggregate_companies(signals, now=now, previous=baseline)

        self.store.publish_area(
            area.id, signals, companies, day=today, run_id=run_id
        )

        return {
            "fetched": sum(r.fetched for r in reports),
            "kept": len(signals),
            "new": new_count,
            "updated": updated,
            "companies": len(companies),
            "needs_review": sum(1 for s in signals if s.needs_review),
            "graph_linked": sum(len(s.graph_entities) for s in signals),
        }

    # -- collection --------------------------------------------------------

    def _collect(
        self, area: Area, config: ScanConfig, *, today: dt.date
    ) -> tuple[list[RawSignal], list[SourceReport]]:
        """Fan out across sources concurrently.

        Threads rather than asyncio: the collectors use `requests`, and the whole
        stack (ingestion, ADE) already standardises on blocking HTTP. Introducing an
        async client here would mean two HTTP idioms in one codebase for no measured
        gain — the fan-out is four requests wide and latency-bound, not CPU-bound.
        """
        sources = [s for s in SourceId if config.is_enabled(s)]
        if not sources:
            return [], []

        signals: list[RawSignal] = []
        reports: list[SourceReport] = []

        with ThreadPoolExecutor(max_workers=min(cfg.max_workers(), len(sources))) as pool:
            futures = {
                pool.submit(
                    build_collector(source).collect, area, config.source_for(source), today
                ): source
                for source in sources
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    batch, report = future.result()
                except Exception as e:  # noqa: BLE001 - belt and braces; collectors already catch
                    logger.exception(f"collector {source.value} raised past its own guard")
                    reports.append(
                        SourceReport(
                            source=source, area=area.id, ok=False,
                            error=f"{type(e).__name__}: {e}"[:500],
                        )
                    )
                    continue
                signals.extend(batch)
                reports.append(report)

        return signals, reports

    # -- signal assembly ---------------------------------------------------

    def _build_signal(
        self,
        group: list[RawSignal],
        *,
        area: Area,
        config: ScanConfig,
        today: dt.date,
        now: dt.datetime,
        run_id: str,
        existing: dict[str, Signal],
        known_companies: dict[str, int],
    ) -> Signal:
        primary = primary_of(group)
        signal_id = primary.content_hash

        company_name = next((s.company_name for s in group if s.company_name), None)
        company_id = company_id_for(company_name) if company_name else None
        prior_count = known_companies.get(company_id or "", 0)

        result = score_signal(
            primary,
            area,
            config,
            today=today,
            corroboration_count=len(group),
            company_known=bool(company_id and prior_count > 0),
            company_signal_count=prior_count,
        )

        sources = [
            SignalSource(
                source=s.source,
                external_id=s.external_id,
                url=s.url,
                published=s.published,
            )
            for s in sorted(group, key=lambda s: s.source.value)
        ]

        prior = existing.get(signal_id)

        # Rationale is only generated for signals that will actually be read. A
        # watch-tier signal nobody opens does not justify an LLM call, and generating
        # thousands per night would dominate both runtime and cost.
        if result.priority.value in ("high", "med"):
            rationale, kind = build_rationale(
                title=primary.title,
                summary=primary.summary,
                signal_type=signal_type_for(primary.source),
                area_label=area.label,
                company=company_name,
                stage=primary.stage,
                published=primary.published.isoformat() if primary.published else None,
                result=result,
                source_names=[s.source.value for s in sources],
            )
            llm_attempted = llm_configured()
        else:
            rationale, kind = "", RationaleKind.TEMPLATE
            llm_attempted = False

        # Knowledge-graph annotation. Terms come from the matched keywords and the
        # trial interventions — the two places an asset or indication is actually
        # named. Deliberately NOT fed into the score; see graph.py.
        graph_entities = self.graph.link(
            [*primary.keywords, *(primary.payload.get("interventions") or [])[:3]]
        )

        review_reasons = assess_review(
            primary,
            result,
            config,
            source_count=len(group),
            rationale_kind=kind,
            llm_was_attempted=llm_attempted,
        )

        return Signal(
            id=signal_id,
            area=area.id,
            type=signal_type_for(primary.source),
            title=primary.title,
            summary=primary.summary,
            rationale=rationale,
            rationale_kind=kind,
            score=result.score,
            score_breakdown={
                **result.breakdown(),
                **_identity_extras(group),
            },
            priority=result.priority,
            company_name=company_name,
            company_id=company_id,
            stage=primary.stage,
            matched_keywords=sorted(set(primary.keywords)),
            published=primary.published,
            # Preserved across runs: a signal seen last week that is still current is
            # not "detected today". Resetting this would make the "since you last
            # looked" counter report the entire corpus as new every single night.
            detected_at=prior.detected_at if prior else now,
            first_seen_run=prior.first_seen_run if prior else run_id,
            last_seen_run=run_id,
            sources=sources,
            graph_entities=graph_entities,
            # Flagged, never suppressed — an analyst who finds the system quietly
            # dropped something stops trusting everything it did show.
            needs_review=bool(review_reasons),
            review_reasons=review_reasons,
            # An analyst's dismissal is a decision, and a scan must not silently
            # undo it by republishing the signal as fresh.
            dismissed=prior.dismissed if prior else False,
        )

    @staticmethod
    def _known_companies(existing: dict[str, Signal]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for signal in existing.values():
            if signal.company_id:
                counts[signal.company_id] = counts.get(signal.company_id, 0) + 1
        return counts

    def _select_areas(self, config: ScanConfig, areas: list[str] | None) -> list[Area]:
        wanted = areas or config.enabled_areas or None
        return enabled_areas(wanted)


def _identity_extras(group: list[RawSignal]) -> dict[str, Any]:
    """Source identifiers worth surfacing in the breakdown panel — ticker and CIK are
    what let an analyst pivot straight to EDGAR, and `companies.py` reads them back
    out for the watchlist row."""
    extras: dict[str, Any] = {}
    for signal in group:
        if signal.source == SourceId.EDGAR:
            if signal.payload.get("ticker"):
                extras["ticker"] = signal.payload["ticker"]
            if signal.payload.get("cik"):
                extras["cik"] = signal.payload["cik"]
        if signal.source == SourceId.TRIALS and signal.payload.get("nct_id"):
            extras["nct_id"] = signal.payload["nct_id"]
        if signal.source == SourceId.PATENTS and signal.payload.get("publication_number"):
            extras["publication_number"] = signal.payload["publication_number"]
    return extras
