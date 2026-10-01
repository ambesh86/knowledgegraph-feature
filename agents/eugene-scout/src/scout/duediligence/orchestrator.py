"""Fan the collectors out against a single target and assemble the brief.

The Use Case 1 orchestrator sweeps therapeutic areas on a schedule. This one sweeps a
named company or asset on demand. The difference is the scope, not the machinery: the
same five collectors, the same never-raise contract, the same rate limiters shared
process-wide so an on-demand brief cannot stampede the public APIs while a scheduled
scan is running.

Concurrency is bounded and the sources run in parallel, because the use case's promise
is "24-48 hours instead of 2-4 weeks" and a serial fan-out would spend most of its
wall-clock waiting on the slowest registry.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from scout import config as cfg
from scout.collectors import REGISTRY, build as build_collector
from scout.dedupe import dedupe_identity, group_corroborated
from scout.duediligence import brief as brief_builder
from scout.duediligence import synthesis
from scout.duediligence.target import Target
from scout.enrich import enrich
from scout.models import RawSignal, Signal, SourceId, SourceReport, utcnow
from scout.orchestrator import Orchestrator
from scout.store import Store

logger = logging.getLogger(__name__)

# A due-diligence window is deliberately wider than the Radar's. The scanner asks
# "what changed recently"; diligence asks "what is known", and a pivotal phase 3 from
# three years ago is exactly what the analyst needs to see.
DEFAULT_WINDOW_DAYS = 1825  # 5 years
DEFAULT_LIMIT_PER_SOURCE = 40


def _collect_one(
    source: SourceId, target: Target, window_days: int, limit: int
) -> tuple[list[RawSignal], SourceReport]:
    area = target.as_area()
    settings = cfg.SourceSettings(
        enabled=True,
        window_days=window_days,
        limit_per_area=limit,
    )
    collector = build_collector(source)
    return collector.collect(area, settings, utcnow().date())


def run_due_diligence(
    company: str,
    asset: str | None = None,
    aliases: list[str] | None = None,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    limit_per_source: int = DEFAULT_LIMIT_PER_SOURCE,
    sources: list[SourceId] | None = None,
    max_workers: int = 5,
    persist: bool = True,
) -> dict:
    """Run the full workflow for one target and return the brief."""
    started = time.monotonic()
    target = Target(company=company, asset=asset, aliases=aliases or [])
    store = Store()
    run_id = f"dd-{target.id}-{int(started)}"

    # Honour the deployment's own source enablement. EPO in particular ships
    # disabled because it was written against the published contract but never
    # verified against a live response; a diligence brief must not quietly depend
    # on an unverified source.
    # A source MISSING from the stored config must fall back to its shipped default,
    # not to "enabled". EPO is absent from the persisted config and ships disabled;
    # defaulting the missing case to True ran it anyway on the first live test, which
    # is precisely the "quietly depends on an unverified source" outcome this filter
    # exists to prevent.
    cfg_now = store.load_config()
    def _enabled(source: SourceId) -> bool:
        setting = cfg_now.sources.get(source.value) or cfg.DEFAULT_SOURCES.get(source.value)
        return bool(getattr(setting, "enabled", False))

    wanted = sources or [s for s in REGISTRY if _enabled(s)]

    logger.info(
        f"due diligence starting: target={target.label!r} "
        f"sources={[str(s) for s in wanted]} window={window_days}d"
    )

    raw: list[RawSignal] = []
    reports: list[SourceReport] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_collect_one, s, target, window_days, limit_per_source): s
            for s in wanted
        }
        for fut, source in futures.items():
            try:
                items, report = fut.result()
                raw.extend(items)
                reports.append(report)
            except Exception as e:  # noqa: BLE001
                # The collectors already promise not to raise; this is the backstop for
                # a failure in the fan-out itself. One dead source must never cost the
                # analyst the whole brief.
                logger.exception(f"collector {source} failed outside its own guard")
                reports.append(
                    SourceReport(source=source, area=target.as_area().id, ok=False,
                                 fetched=0, kept=0, error=f"{type(e).__name__}: {e}")
                )

    # Reuse the Use Case 1 pipeline verbatim — enrich, relevance gate, identity
    # dedupe, corroboration grouping, score — rather than reimplementing it. A second
    # scoring path would drift from the first the day someone fixed a bug in only one,
    # and then a due-diligence brief and the Radar would disagree about the same
    # company for reasons nobody could explain.
    area = target.as_area()
    config = store.load_config()
    today = utcnow().date()
    now = utcnow()

    enriched = [enrich(s, area, config) for s in raw]

    # The Use Case 1 relevance gate is deliberately NOT applied here.
    #
    # That gate rejects a record when no area keyword appears in its text, and it
    # exists because a broad therapeutic-area query pulls in off-topic results — an
    # oncology trial matching "inhibitor" in a hemophilia sweep. A company-scoped
    # query has the opposite premise: the source has already matched the target in
    # fields the gate never reads, such as sponsor, affiliation and funding.
    #
    # Measured on the first live run: Europe PMC returned 50 records for Alnylam and
    # the gate rejected all of them, because papers about the company's drug
    # (vutrisiran) do not contain the word "Alnylam" in title or abstract. Applying it
    # would have produced a brief asserting that a heavily-published company has no
    # publications — the single most damaging thing this workflow could get wrong.
    #
    # The trade is that relevance now rests on the upstream query, so the brief says
    # so rather than implying a second check happened.
    relevant = enriched
    groups = group_corroborated(dedupe_identity(relevant))

    scout_orch = Orchestrator(store)
    signals: list[Signal] = []
    for group in groups:
        try:
            signals.append(
                scout_orch._build_signal(  # noqa: SLF001 - see note below
                    group, area=area, config=config, today=today, now=now,
                    run_id=run_id,
                    # A diligence run carries no history: `existing` and
                    # `known_companies` exist to score novelty against previous
                    # scans, and "is this new to the Radar" is not a question this
                    # workflow asks. Empty is the correct value, not a shortcut.
                    existing={}, known_companies={},
                )
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"could not build signal from group: {type(e).__name__}: {e}")

    signals.sort(key=lambda s: (s.score or 0), reverse=True)
    doc = brief_builder.build(target, signals, reports)

    # Executive summary last: it narrates the finished brief, so it must run after the
    # confidence assessment and the risk flags exist. Provenance is recorded next to
    # the prose — a model-written paragraph and a computed one are different claims,
    # the same distinction the Radar already surfaces on every rationale.
    summary_text, summary_kind = synthesis.summarise(doc)
    doc["executive_summary"] = {"text": summary_text, "provenance": summary_kind}

    doc["coverage"]["relevance"] = (
        "source-attributed: records are included because the source matched the target "
        "(sponsor, affiliation, assignee), not because the target's name appears in the "
        "record text"
    )
    doc["timing_ms"] = int((time.monotonic() - started) * 1000)

    if persist:
        # Failing to store must not lose the brief the caller is waiting on: it is
        # returned either way, and a storage outage degrades durability rather than
        # the request.
        try:
            store.save_brief(target.id, doc)
            doc["stored"] = True
        except Exception as e:  # noqa: BLE001
            logger.error(f"could not persist brief for {target.id}: {type(e).__name__}: {e}")
            doc["stored"] = False
            doc["storage_error"] = f"{type(e).__name__}: {e}"

    logger.info(
        f"due diligence complete: target={target.label!r} signals={len(signals)} "
        f"confidence={doc['confidence']['band']} summary={summary_kind} "
        f"in {doc['timing_ms']}ms"
    )
    return doc
