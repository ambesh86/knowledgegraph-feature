"""Nightly scheduler for the ingestion pipeline.

Runs the sweep at 01:00 daily and exposes a manual trigger so a run can be forced
without waiting for the small hours.

A container service rather than a host crontab: it ships with the stack, survives
a machine rebuild, and is visible to `docker compose ps` like everything else. A
crontab line on the host is invisible to the compose file and quietly lost the
first time the box is reprovisioned.

Only one run may be in flight at a time. Extraction is CPU-saturating, and two
overlapping sweeps would compete for the same cores while doing identical work.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks, FastAPI
from fastapi.concurrency import run_in_threadpool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingestion-scheduler")

CRON_HOUR = int(os.environ.get("INGESTION_HOUR", "1"))
CRON_MINUTE = int(os.environ.get("INGESTION_MINUTE", "0"))
TIMEZONE = os.environ.get("INGESTION_TZ", "UTC")

_lock = asyncio.Lock()
_state: dict[str, Any] = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_result": None,
    "runs": 0,
}


async def _execute(trigger: str) -> dict[str, Any]:
    if _lock.locked():
        logger.info(f"{trigger}: a run is already in flight; skipping")
        return {"status": "skipped", "reason": "run already in progress"}

    async with _lock:
        from pipeline import orchestrator

        _state["running"] = True
        _state["last_started"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        logger.info(f"{trigger}: starting ingestion sweep")
        try:
            # Blocking, CPU/network-bound — keep it off the event loop.
            result = await run_in_threadpool(orchestrator.run)
        except Exception as e:
            logger.exception("ingestion run failed")
            result = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}
        finally:
            _state["running"] = False
            _state["last_finished"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            _state["runs"] += 1
        _state["last_result"] = result
        return result


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        _execute,
        CronTrigger(hour=CRON_HOUR, minute=CRON_MINUTE, timezone=TIMEZONE),
        args=["cron"],
        id="nightly_ingestion",
        max_instances=1,
        coalesce=True,       # a missed window runs once, not once per miss
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(f"scheduled nightly ingestion at {CRON_HOUR:02d}:{CRON_MINUTE:02d} {TIMEZONE}")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    lifespan=lifespan,
    title="Eugene Ingestion Scheduler",
    description="Nightly research-evidence ingestion: discover → extract → index → rank.",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "OK",
        "service": "eugene-ingestion",
        "schedule": f"{CRON_HOUR:02d}:{CRON_MINUTE:02d} {TIMEZONE} daily",
        **_state,
    }


@app.post("/ingest/run")
async def trigger(background: BackgroundTasks) -> dict[str, Any]:
    """Force a sweep now. Returns immediately; poll /health for the result."""
    if _lock.locked():
        return {"status": "busy", "reason": "a run is already in progress"}
    background.add_task(_execute, "manual")
    return {"status": "queued", "note": "poll /health for progress and result"}


@app.post("/ingest/dry-run")
async def dry_run() -> dict[str, Any]:
    """Discovery only — no extraction, no writes. Shows what a sweep would fetch."""
    from pipeline import orchestrator

    return await run_in_threadpool(orchestrator.run, None, True)


async def _centrality(trigger: str) -> dict[str, Any]:
    from pipeline.steps import centrality_step

    _state["running"] = True
    try:
        result = await run_in_threadpool(centrality_step.run)
    except Exception as e:
        logger.exception("centrality refresh failed")
        result = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}
    finally:
        _state["running"] = False
    _state["last_result"] = result
    _state["last_finished"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    logger.info(f"{trigger}: centrality refresh finished")
    return result


@app.post("/ingest/centrality")
async def centrality_only(background: BackgroundTasks) -> dict[str, Any]:
    """Refresh ranking without touching documents (M5). Async.

    The reason M5 exists: parsing is the expensive stage, ranking is the cheap
    one, so decoupling them lets the whole corpus be retuned without re-parsing.

    Backgrounded because it is still minutes-scale on a real graph, and a
    synchronous version died mid-computation the moment a client timed out —
    losing the work with nothing written back.
    """
    if _lock.locked() or _state["running"]:
        return {"status": "busy", "reason": "a run is already in progress"}
    background.add_task(_centrality, "manual")
    return {"status": "queued", "note": "poll /health for the result"}
