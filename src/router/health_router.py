"""Deep health check (OBS-04)."""
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, Any]:
    return {"status": "OK", "service": "eugene-ws"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    # Neo4j reachability via existing connection factory
    uri = os.environ.get("NEO4J_URI", "")
    if uri:
        start = time.perf_counter()
        try:
            from graph.infra.db.graph_db_connection_factory import (
                GraphDbConnectionFactory,
            )

            driver = GraphDbConnectionFactory.remote_neo4j_instance_from_env()
            driver.verify_connectivity()
            checks["neo4j"] = {
                "ok": True,
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }
        except Exception as exc:
            checks["neo4j"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        overall_ok &= checks["neo4j"]["ok"]
    else:
        checks["neo4j"] = {"ok": False, "error": "NEO4J_URI not set"}
        overall_ok = False

    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "OK" if overall_ok else "DEGRADED",
        "service": "eugene-ws",
        "checks": checks,
    }


@router.get("/health/data-freshness")
async def data_freshness() -> dict[str, Any]:
    """When was the internal data last refreshed, and how stale is it?

    The agent reads this so it can date facts drawn from the internal snapshot
    honestly ("the Eugene snapshot dated X shows…") instead of implying they are
    current — the failure that had it reporting its training cutoff as "now".
    The UI reads it to show a freshness indicator.
    """
    import datetime as dt

    today = dt.date.today()
    out: dict[str, Any] = {
        "today": today.isoformat(),
        "snapshot_date": None,
        "sources": [],
        "age_days": None,
        "stale": None,
    }
    try:
        from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory

        driver = GraphDbConnectionFactory.remote_neo4j_instance_from_env()
        records, _, _ = driver.execute_query(
            "MATCH (s:DataSnapshot) "
            "RETURN s.source AS source, toString(s.ingested_at) AS ingested_at, "
            "       s.record_count AS record_count, s.window AS window "
            "ORDER BY s.ingested_at DESC"
        )
        sources = [dict(r) for r in records]
        out["sources"] = sources
        if sources:
            # The overall snapshot is only as fresh as its OLDEST source — saying
            # otherwise would overstate freshness for whichever source lagged.
            dates = sorted(
                (s["ingested_at"] or "")[:10] for s in sources if s.get("ingested_at")
            )
            if dates:
                out["snapshot_date"] = dates[0]
                try:
                    age = (today - dt.date.fromisoformat(dates[0])).days
                    out["age_days"] = age
                    out["stale"] = age > 30
                except ValueError:
                    pass
    except Exception as exc:
        logger.warning(f"data-freshness lookup failed: {exc}")
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out
