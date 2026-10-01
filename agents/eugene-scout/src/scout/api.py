"""FastAPI service and scheduler.

The scheduler is an APScheduler cron inside this container rather than EventBridge,
matching the pattern `ingestion/scheduler/service.py` already established: it ships
with the stack, survives a machine rebuild, is visible to `docker compose ps`, and
behaves identically on a laptop and on EC2. `POST /scan` is the manual trigger, and it
is deliberately shaped so an EventBridge target could call it later with no code
change — the AWS-native path stays open without being required today.

Two schedules:
  * daily  — the scan (default 02:00 UTC, after ingestion's 01:00 so it sees the
             night's newly indexed papers rather than racing them)
  * weekly — the ranked partnership briefing (default Monday)

Single-flight is enforced with an `asyncio.Lock`. Two overlapping scans would issue
duplicate requests to rate-limited public APIs and race each other writing the same
curated S3 keys, so a second trigger while one is running returns `skipped` rather
than queueing.

All handlers are read-only against an in-memory index; the scan itself is blocking,
CPU-and-network bound work and runs in a threadpool so it never occupies the event
loop that has to keep serving the Radar.
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
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from scout import __version__
from scout import config as cfg
from scout import digest as digest_builder
from scout.areas import areas_for_ui_area, enabled_areas, load_areas
from scout.config import ScanConfig
from scout.index import SignalIndex, valid_priority, valid_type
from scout.models import utcnow
from scout.notify import Notifier, send_test
from scout.orchestrator import Orchestrator
from scout.duediligence import run_due_diligence
from scout.store import Store

from scout import logging_setup
from scout.security import auth_status, docs_enabled, require_token, warn_if_unauthenticated

logging_setup.configure()
logger = logging.getLogger("scout.api")

_lock = asyncio.Lock()
_state: dict[str, Any] = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_result": None,
    "runs": 0,
}

store = Store()
index = SignalIndex(store)
orchestrator = Orchestrator(store)


# ---------------------------------------------------------------------------
# Scan execution
# ---------------------------------------------------------------------------


async def _refresh_index() -> None:
    """Re-read the curated index from S3 on a timer (serve-only instances).

    Failures are logged and swallowed: a transient S3 error must leave the
    previous index serving rather than take the Radar down. `index.refresh`
    already builds the replacement fully before swapping it in.
    """
    try:
        areas = await run_in_threadpool(index.refresh)
        logger.info(f"index refreshed from S3: {areas} area(s)")
    except Exception as e:  # noqa: BLE001 - never let a refresh failure kill the scheduler
        logger.error(f"scheduled index refresh failed: {type(e).__name__}: {e}")


async def execute_scan(trigger: str, areas: list[str] | None = None) -> dict[str, Any]:
    """Run one scan under the single-flight lock, then refresh the serving index."""
    if _lock.locked():
        logger.info(f"{trigger}: a scan is already in flight; skipping")
        return {"status": "skipped", "reason": "scan already in progress"}

    async with _lock:
        _state["running"] = True
        _state["last_started"] = utcnow().isoformat()
        logger.info(f"{trigger}: starting scan")
        try:
            run = await run_in_threadpool(
                lambda: orchestrator.run(trigger=trigger, areas=areas)
            )
            summary = run.summary()

            # Refresh before notifying: if a recipient clicks through immediately, the
            # signal must already be queryable.
            await run_in_threadpool(index.refresh)

            config = await run_in_threadpool(store.load_config)
            notified = 0
            for area_id in run.areas:
                signals = await run_in_threadpool(store.load_signals, area_id)
                area = load_areas().get(area_id)
                report = await run_in_threadpool(
                    lambda s=signals, a=area: Notifier(store.s3).dispatch(
                        s,
                        run_id=run.run_id,
                        min_score=config.notify_min_score,
                        area_label=a.label if a else area_id,
                    )
                )
                notified += int(report.get("sent") or 0)
            summary["notifications_sent"] = notified
        except Exception as e:  # noqa: BLE001
            logger.exception("scan failed")
            summary = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}
        finally:
            _state["running"] = False
            _state["last_finished"] = utcnow().isoformat()
            _state["runs"] += 1
        _state["last_result"] = summary
        return summary


async def execute_weekly_digest(trigger: str = "cron") -> dict[str, Any]:
    """Build and persist the ranked briefing for every scanned area."""
    logger.info(f"{trigger}: building weekly digests")
    today = utcnow().date()
    out: dict[str, Any] = {}
    for area_id in await run_in_threadpool(store.known_areas):
        signals = await run_in_threadpool(store.load_signals, area_id)
        companies = await run_in_threadpool(store.load_companies, area_id)
        payload = digest_builder.build(area_id, signals, companies)
        await run_in_threadpool(store.save_digest, area_id, today, payload)
        out[area_id] = payload["company_count"]
    return {"status": "ok", "areas": out, "date": today.isoformat()}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = AsyncIOScheduler(timezone=cfg.timezone())

    if cfg.scan_enabled():
        scheduler.add_job(
            execute_scan,
            CronTrigger(hour=cfg.cron_hour(), minute=cfg.cron_minute(), timezone=cfg.timezone()),
            args=["cron"],
            id="daily_scan",
            max_instances=1,
            # A missed window runs once, not once per miss — a container down for six
            # hours must not wake up and fire six scans at the public APIs.
            coalesce=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            execute_weekly_digest,
            CronTrigger(
                day_of_week=cfg.weekly_digest_dow(),
                hour=cfg.cron_hour(),
                minute=cfg.cron_minute() + 30,
                timezone=cfg.timezone(),
            ),
            args=["cron"],
            id="weekly_digest",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=7200,
        )
        logger.info(
            f"scheduled daily scan at {cfg.cron_hour():02d}:{cfg.cron_minute():02d} "
            f"{cfg.timezone()}; weekly digest on day {cfg.weekly_digest_dow()}"
        )
    else:
        # Serve-only. Another instance — one that has internet — owns scanning and
        # writes to this same bucket. All this one has to do is notice.
        #
        # The timer is not optional: without it this process serves whatever it
        # read at boot for as long as it stays up, so a scan that ran an hour ago
        # would be invisible until the next restart. That failure is silent, which
        # makes it worse than a crash.
        scheduler.add_job(
            _refresh_index,
            IntervalTrigger(minutes=cfg.index_refresh_minutes()),
            id="index_refresh",
            max_instances=1,
            coalesce=True,
        )
        logger.info(
            f"SCAN DISABLED — serve-only. Reloading the curated index from S3 every "
            f"{cfg.index_refresh_minutes()}m; scanning is owned by another instance."
        )

    warn_if_unauthenticated()
    scheduler.start()

    # Warm the index from S3 so the first request after a restart is served from
    # memory rather than waiting on a cold read.
    try:
        await run_in_threadpool(index.refresh)
    except Exception as e:  # noqa: BLE001 - a cold or unreachable bucket must not block boot
        logger.error(f"initial index load failed: {type(e).__name__}: {e}")

    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    lifespan=lifespan,
    # Applied at the app level rather than per-route: a new endpoint is then
    # authenticated by default, and forgetting to add a decorator cannot silently
    # open a hole.
    dependencies=[Depends(require_token)],
    # FastAPI mounts the docs routes outside the dependency chain, so they cannot be
    # token-protected. Serving an unauthenticated OpenAPI schema is free
    # reconnaissance, so they are off whenever auth is on.
    docs_url="/docs" if docs_enabled() else None,
    redoc_url="/redoc" if docs_enabled() else None,
    openapi_url="/openapi.json" if docs_enabled() else None,
    title="Eugene Scout",
    version=__version__,
    description=(
        "Real-time pipeline intelligence & partnership opportunity scanning. "
        "CSL BD AWS Bioinformatics Agentic Workflow — Use Case 1."
    ),
)


# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------


app.middleware("http")(logging_setup.request_context_middleware)


@app.get("/health")
async def health(response: Response) -> dict[str, Any]:
    """Liveness plus dependency reachability.

    Returns 503 when S3 is unreachable so an orchestrator restarts the container,
    but still returns a body explaining which dependency failed.
    """
    s3_ok = await run_in_threadpool(store.s3.health)
    ok = s3_ok
    if not ok:
        response.status_code = 503
    return {
        "status": "ok" if ok else "degraded",
        "version": __version__,
        "s3": {
            "bucket": store.s3.bucket,
            "reachable": s3_ok,
            # Whether the scoped least-privilege credential took effect, visible
            # without exec'ing into the container.
            "identity": cfg.s3_identity_source(),
        },
        "index": {"areas": index.areas, "loaded_at": index.loaded_at},
        "scan": {
            "running": _state["running"],
            "runs": _state["runs"],
            # Which half of the split this instance is. Without this an operator
            # looking at a Radar with no fresh signals cannot tell whether the
            # scanner is broken or simply lives somewhere else.
            "enabled": cfg.scan_enabled(),
            "mode": "scan+serve" if cfg.scan_enabled() else "serve-only",
            "index_refresh_minutes": None if cfg.scan_enabled() else cfg.index_refresh_minutes(),
        },
        "auth": auth_status(),
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    latest = await run_in_threadpool(store.latest_run)
    return {
        "running": _state["running"],
        "last_started": _state["last_started"],
        "last_finished": _state["last_finished"],
        "last_result": _state["last_result"],
        "runs_this_process": _state["runs"],
        "latest_run": latest,
        "index": {
            "areas": index.areas,
            "loaded_at": index.loaded_at,
            "empty": index.is_empty(),
        },
        "schedule": {
            "daily_hour": cfg.cron_hour(),
            "daily_minute": cfg.cron_minute(),
            "timezone": cfg.timezone(),
            "weekly_day_of_week": cfg.weekly_digest_dow(),
        },
        "auth": auth_status(),
        "sources_available": {
            "clinicaltrials": True,
            "europepmc_lit": True,
            "europepmc_pat": bool(os.environ.get("USPTO_API_KEY")),
            "sec_edgar": True,
        },
    }


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    areas: list[str] | None = None
    trigger: str = "manual"


@app.post("/scan")
async def scan(payload: ScanRequest | None = Body(default=None)) -> dict[str, Any]:
    """Trigger a scan synchronously.

    Synchronous rather than fire-and-forget because the caller — the Settings page's
    Rescan button — needs to know whether it worked. A scan is seconds, not minutes:
    measured at ~5s for one area across all four sources.
    """
    # A serve-only instance has no internet by design. Refusing here with an
    # explanation beats attempting the scan and returning a wall of connection
    # timeouts that reads like a broken scanner rather than a deliberate split.
    if not cfg.scan_enabled():
        raise HTTPException(
            status_code=409,
            detail=(
                "This instance is serve-only (SCOUT_SCAN_ENABLED=false). It has no "
                "route to the public internet and reads curated results from S3. "
                "Run the scan on the instance that does have internet; this one "
                "will pick up the results at its next index refresh."
            ),
        )

    request = payload or ScanRequest()
    return await execute_scan(request.trigger or "manual", request.areas)


@app.post("/digest/rebuild")
async def rebuild_digest() -> dict[str, Any]:
    return await execute_weekly_digest(trigger="manual")


@app.post("/index/refresh")
async def refresh_index() -> dict[str, Any]:
    total = await run_in_threadpool(index.refresh)
    return {"status": "ok", "signals": total, "areas": index.areas}


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _parse_iso_datetime(raw: str) -> dt.datetime:
    """Parse an ISO-8601 timestamp from a query string, tolerantly.

    `+` is a legal offset character in ISO-8601 and *also* means "space" in a URL
    query string. A client that sends `since=2026-08-07T12:00:00+00:00` without
    percent-encoding — which is what `Date.toISOString()` plus naive string
    concatenation produces — arrives here as `...12:00:00 00:00`. Rejecting that with
    a 400 would break the "since you last looked" panel for a mistake almost every
    caller makes, so the space form is repaired rather than refused.
    """
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    elif " " in text[10:]:
        # Only the offset separator can legitimately be a space this late in the
        # string; the date/time separator is 'T' at index 10.
        head, _, tail = text.rpartition(" ")
        text = f"{head}+{tail}"
    parsed = dt.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _resolve_areas(area: str | None, ui_area: str | None) -> list[str] | None:
    """Area selection precedence: explicit `area` wins, then the caller's UI profile
    area mapped through the taxonomy bridge, then everything."""
    if area:
        return [a.strip() for a in area.split(",") if a.strip()]
    if ui_area:
        return areas_for_ui_area(ui_area)
    return None


@app.get("/signals")
async def get_signals(
    area: str | None = Query(default=None, description="Comma-separated scan area ids"),
    ui_area: str | None = Query(default=None, description="UI profile focus area"),
    type: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO date lower bound on publication"),
    q: str | None = Query(default=None, description="Free-text filter"),
    include_dismissed: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    since_date: dt.date | None = None
    if since:
        try:
            since_date = dt.date.fromisoformat(since[:10])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid since date: {since!r}") from None

    rows, total, counts = index.query_signals(
        areas=_resolve_areas(area, ui_area),
        signal_type=valid_type(type),
        priority=valid_priority(priority),
        company_id=company_id,
        since=since_date,
        search=q,
        include_dismissed=include_dismissed,
        limit=limit,
        offset=offset,
    )
    latest = await run_in_threadpool(store.latest_run)
    return {
        "signals": rows,
        "total": total,
        "counts": counts,
        "limit": limit,
        "offset": offset,
        "generated_at": index.loaded_at,
        "last_run": latest,
    }


@app.get("/signals/{signal_id}")
async def get_signal(signal_id: str) -> dict[str, Any]:
    row = index.get_signal(signal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="signal not found")
    return row


class SignalPatch(BaseModel):
    dismissed: bool = Field(description="Hide this signal from the Radar")


@app.patch("/signals/{signal_id}")
async def patch_signal(signal_id: str, patch: SignalPatch) -> dict[str, Any]:
    """Dismiss or restore a signal.

    Writes through to the curated tier so the decision survives the next scan — the
    orchestrator reads `dismissed` forward when it rebuilds. An in-memory-only
    dismissal would silently reappear at 02:00.
    """
    row = index.get_signal(signal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="signal not found")

    area_id = str(row.get("area") or "")
    signals = await run_in_threadpool(store.load_signals, area_id)
    companies = await run_in_threadpool(store.load_companies, area_id)

    found = False
    for signal in signals:
        if signal.id == signal_id:
            signal.dismissed = patch.dismissed
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="signal not found in curated store")

    today = utcnow().date()
    await run_in_threadpool(
        lambda: store.publish_area(
            area_id, signals, companies, day=today, run_id=f"patch-{signal_id[:8]}"
        )
    )
    await run_in_threadpool(index.refresh, [area_id])
    return {"id": signal_id, "dismissed": patch.dismissed}


@app.get("/companies")
async def get_companies(
    area: str | None = Query(default=None),
    ui_area: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    rows, total = index.query_companies(
        areas=_resolve_areas(area, ui_area), search=q, limit=limit, offset=offset
    )
    return {
        "companies": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
        "generated_at": index.loaded_at,
    }


@app.get("/stats")
async def get_stats(
    area: str | None = Query(default=None),
    ui_area: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO datetime for 'new since'"),
) -> dict[str, Any]:
    areas = _resolve_areas(area, ui_area)
    payload = index.stats(areas)
    if since:
        try:
            payload.update(index.new_since(areas, _parse_iso_datetime(since)))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid since: {since!r}") from None
    payload["last_run"] = await run_in_threadpool(store.latest_run)
    return payload


@app.get("/freshness")
async def get_freshness(
    area: str | None = Query(default=None),
    ui_area: str | None = Query(default=None),
) -> dict[str, Any]:
    """Data currency, for the "as of" indicator the UI shows on every page.

    Reports three different clocks that are routinely conflated:

      * `today`               — the platform's own date
      * `last_scan`           — when this service last looked
      * `sources[].latest_published` — how recent the newest record each source
                                actually returned is, extracted from the data

    The third is the one that matters for judging staleness and the one a naive
    implementation omits. "Scanned 20 minutes ago" says nothing about whether the
    field has moved; "newest EDGAR filing is 5 days old" does.

    `next_scan_at` is computed from the same cron settings the scheduler uses, so
    the UI can say when the picture will change next without guessing.
    """
    payload = index.freshness(_resolve_areas(area, ui_area))
    latest = await run_in_threadpool(store.latest_run)

    payload["last_scan"] = (
        {
            "run_id": latest.get("run_id"),
            "started_at": latest.get("started_at"),
            "finished_at": latest.get("finished_at"),
            "status": latest.get("status"),
        }
        if latest
        else None
    )
    payload["next_scan_at"] = _next_cron_utc().isoformat()
    payload["schedule"] = {
        "hour": cfg.cron_hour(),
        "minute": cfg.cron_minute(),
        "timezone": cfg.timezone(),
    }
    return payload


def _next_cron_utc(now: dt.datetime | None = None) -> dt.datetime:
    """Next daily scan time. Mirrors the CronTrigger registered in `lifespan`."""
    current = now or utcnow()
    candidate = current.replace(
        hour=cfg.cron_hour(), minute=cfg.cron_minute(), second=0, microsecond=0
    )
    if candidate <= current:
        candidate += dt.timedelta(days=1)
    return candidate


@app.get("/runs")
async def get_runs(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    runs = await run_in_threadpool(store.recent_runs, limit)
    return {"runs": runs, "total": len(runs)}


@app.get("/areas")
async def get_areas() -> dict[str, Any]:
    return {
        "areas": [
            {"id": a.id, "label": a.label, "keywords": list(a.keywords)}
            for a in enabled_areas()
        ],
        "with_data": index.areas,
    }


@app.get("/digest")
async def get_digest(
    area: str | None = Query(default=None),
    ui_area: str | None = Query(default=None, description="UI profile focus area"),
    date: str | None = Query(default=None),
    format: str = Query(default="json", pattern="^(json|markdown)$"),
) -> Any:
    """Fetch a stored briefing, or build one on demand if none is stored yet.

    Accepts `ui_area` as well as an explicit `area` so the taxonomy bridge stays in
    this service. The UI's coarse profile areas (hematology, immunology) and the scan
    taxonomy (hemophilia, hereditary_angioedema, …) are different vocabularies, and
    translating in the BFF would put a second copy of that mapping in TypeScript to
    drift out of sync with `areas.UI_AREA_MAP`.
    """
    try:
        day = dt.date.fromisoformat(date[:10]) if date else utcnow().date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"invalid date: {date!r}") from None

    if not area:
        resolved = _resolve_areas(None, ui_area) or index.areas
        if not resolved:
            raise HTTPException(status_code=404, detail="no scanned areas available")
        # One briefing per area; a profile mapping onto several gets the one it
        # names most directly, which is the first in the declared order.
        area = resolved[0]

    payload = await run_in_threadpool(store.load_digest, area, day)
    if payload is None:
        signals = await run_in_threadpool(store.load_signals, area)
        companies = await run_in_threadpool(store.load_companies, area)
        if not signals:
            raise HTTPException(status_code=404, detail=f"no data for area {area!r}")
        payload = digest_builder.build(area, signals, companies)

    if format == "markdown":
        return Response(
            content=digest_builder.to_markdown(payload),
            media_type="text/markdown; charset=utf-8",
        )
    return payload


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@app.get("/config")
async def get_config() -> dict[str, Any]:
    config = await run_in_threadpool(store.load_config)
    return config.public()


@app.put("/config")
async def put_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Replace the scan configuration.

    Validated through `ScanConfig` before it is stored, so a malformed Settings save
    is rejected at the boundary with a 400 rather than being written and then
    silently ignored at the next scan.
    """
    current = await run_in_threadpool(store.load_config)
    updated_by = payload.pop("updated_by", None)
    # version/updated_at are server-owned; a client echoing back a stale version must
    # not be able to rewind the audit trail.
    payload.pop("version", None)
    payload.pop("updated_at", None)
    try:
        candidate = ScanConfig.model_validate({**current.model_dump(mode="json"), **payload})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid configuration: {e}") from None

    saved = await run_in_threadpool(store.save_config, candidate.bumped(updated_by))
    return saved.public()


@app.post("/notify/test")
async def notify_test() -> dict[str, Any]:
    return await run_in_threadpool(send_test)


# ---------------------------------------------------------------------------
# Use Case 2 — Accelerated Scientific Due Diligence
# ---------------------------------------------------------------------------


class DueDiligenceRequest(BaseModel):
    company: str = Field(min_length=2, max_length=200)
    asset: str | None = Field(default=None, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=10)
    window_days: int = Field(default=1825, ge=30, le=3650)
    limit_per_source: int = Field(default=40, ge=5, le=200)
    force: bool = Field(
        default=False,
        description="Re-run even if a stored brief exists for this target.",
    )


@app.post("/dd/brief")
async def due_diligence(req: DueDiligenceRequest) -> dict[str, Any]:
    """Run scientific due diligence on one target and return the brief.

    Synchronous, like /scan and for the same reason: the caller is a human who
    needs to know whether it worked. Measured at ~30s against four live sources,
    which is well inside a request and four orders of magnitude inside the
    "2-4 weeks" the use case is displacing.

    Requires outbound internet. On a serve-only deployment this returns 409 rather
    than a brief full of empty sections that would read as "nothing found".
    """
    if not cfg.scan_enabled():
        raise HTTPException(
            status_code=409,
            detail=(
                "This instance is serve-only (SCOUT_SCAN_ENABLED=false) and has no route "
                "to the public sources due diligence reads. Run this where egress exists."
            ),
        )
    # A stored brief is returned unless the caller asks for a fresh run. Diligence is
    # expensive in wall-clock and in requests against rate-limited public registries;
    # re-running it because someone reopened a tab is how a service gets throttled.
    from scout.duediligence.target import Target  # local: avoids a cycle at import time

    target_id = Target(company=req.company, asset=req.asset).id
    if not req.force:
        cached = await run_in_threadpool(store.load_brief, target_id)
        if cached:
            cached["from_cache"] = True
            return cached

    return await run_in_threadpool(
        run_due_diligence,
        req.company,
        req.asset,
        req.aliases,
        window_days=req.window_days,
        limit_per_source=req.limit_per_source,
    )


@app.get("/dd/briefs")
async def list_due_diligence() -> dict[str, Any]:
    """Every target with a stored brief, newest first."""
    targets = await run_in_threadpool(store.list_briefs)
    return {"count": len(targets), "targets": targets}


@app.get("/dd/brief/{target_id}")
async def get_due_diligence(target_id: str, date: str | None = Query(default=None)) -> dict[str, Any]:
    """A stored brief. `?date=YYYY-MM-DD` returns the brief as it read that day.

    The dated form exists because diligence is a decision record: when someone asks in
    six months why a partnership was progressed, the answer is the brief as it stood
    then, not as it reads now.
    """
    if date:
        try:
            day = dt.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid date {date!r}; use YYYY-MM-DD") from None
        doc = await run_in_threadpool(store.load_brief_dated, target_id, day)
        if not doc:
            raise HTTPException(status_code=404, detail=f"no brief for {target_id} on {date}")
        return doc

    doc = await run_in_threadpool(store.load_brief, target_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"no brief stored for {target_id!r}. POST /dd/brief to generate one.",
        )
    return doc
