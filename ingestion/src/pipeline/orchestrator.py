"""Nightly ingestion orchestrator.

Reads the declared research areas, sweeps the configured sources, drives each
discovered document through extraction, then refreshes ranking.

Deliberately an ORCHESTRATOR, not a second parser. Document extraction lives in
the `eugene-ade` service and is called over HTTP: duplicating a YOLO parser in two
processes would mean two model downloads, two sets of weights to keep in sync, and
two places for a chunking bug to hide. Ingestion owns *what to fetch and when*;
ADE owns *how to parse*.

Order matters. Centrality runs last, once, after every document is in the graph —
structural importance is a property of the whole corpus, so scoring per-document
would measure the wrong thing.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
import yaml

logger = logging.getLogger(__name__)

_ADE_URL = os.environ.get("EUGENE_ADE_URL", "http://eugene_ade:8000")
_CONFIG = Path(
    os.environ.get(
        "INGESTION_CONFIG",
        str(Path(__file__).parent / "config" / "research_areas.yaml"),
    )
)
# Extraction is minutes-scale per document (YOLO dominates); this bounds one call,
# not the run.
_ADE_TIMEOUT_S = float(os.environ.get("INGESTION_ADE_TIMEOUT_S", "600"))
_EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_UA = "Eugene-Ingestion/1.0 (biomedical knowledge graph)"


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or _CONFIG
    with p.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _discover_papers(query: str, limit: int, recency_days: int) -> list[dict[str, str]]:
    """Find candidate papers for one area via Europe PMC.

    Europe PMC rather than PubMed because only it exposes per-record PDF links —
    PubMed indexes abstracts, and most of its records have no downloadable PDF at
    all, which would leave the extraction pipeline with nothing to parse.
    """
    since = (dt.date.today() - dt.timedelta(days=recency_days)).isoformat()
    params = {
        "query": f'({query}) AND (FIRST_PDATE:[{since} TO {dt.date.today().isoformat()}])',
        "format": "json",
        "pageSize": max(1, min(limit, 100)),
        "resultType": "core",
        "sort": "P_PDATE_D desc",
    }
    try:
        r = requests.get(_EPMC, params=params, timeout=45, headers={"User-Agent": _UA})
        r.raise_for_status()
        records = (r.json().get("resultList", {}) or {}).get("result", []) or []
    except Exception as e:
        logger.warning(f"discovery failed for {query[:50]!r}: {e}")
        return []

    out: list[dict[str, str]] = []
    for rec in records:
        # Prefer PMCID: it resolves to the OA PDF endpoint directly.
        if rec.get("pmcid"):
            out.append({"source": "pmc", "id": rec["pmcid"]})
        elif rec.get("pmid"):
            out.append({"source": "pubmed", "id": rec["pmid"]})
    return out[:limit]


def _ade_ingest(item: dict[str, str]) -> dict[str, Any]:
    """Drive one document through extraction. Idempotent server-side."""
    try:
        r = requests.post(
            f"{_ADE_URL}/ade/ingest",
            json={"source": item["source"], "id": item["id"]},
            timeout=_ADE_TIMEOUT_S,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"ADE ingest failed for {item}: {e}")
        return {"status": "failed", "reason": str(e)[:200], **item}


def _refresh_centrality() -> dict[str, Any]:
    from pipeline.steps import centrality_step

    return centrality_step.run()


def run(config_path: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Execute one full nightly sweep."""
    started = time.perf_counter()
    cfg = load_config(config_path)
    defaults = cfg.get("defaults", {}) or {}
    areas = [a for a in (cfg.get("areas") or []) if a.get("enabled")]

    logger.info(f"ingestion run: {len(areas)} enabled area(s)")
    summary: dict[str, Any] = {
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "areas": [],
        "documents_seen": 0,
        "documents_ready": 0,
        "documents_unavailable": 0,
        "dry_run": dry_run,
    }

    seen: set[str] = set()
    for area in areas:
        q = (area.get("queries") or {}).get("literature")
        if not q:
            continue
        found = _discover_papers(
            q,
            int(defaults.get("max_papers_per_area", 15)),
            int(defaults.get("recency_days", 365)),
        )
        # Dedup across areas — a paper matching two areas must not be extracted
        # twice, and the pipeline's idempotency shouldn't be relied on for that.
        fresh = [f for f in found if f["id"] not in seen]
        seen.update(f["id"] for f in fresh)

        entry = {"id": area["id"], "discovered": len(found), "new": len(fresh),
                 "ready": 0, "unavailable": 0}
        if not dry_run:
            for item in fresh:
                res = _ade_ingest(item)
                status = res.get("status")
                if status == "ready":
                    entry["ready"] += 1
                elif status == "unavailable":
                    entry["unavailable"] += 1
        summary["areas"].append(entry)
        summary["documents_seen"] += len(fresh)
        summary["documents_ready"] += entry["ready"]
        summary["documents_unavailable"] += entry["unavailable"]
        logger.info(f"  [{area['id']}] {entry}")

    if not dry_run:
        # Last, and once: centrality describes the whole corpus.
        summary["centrality"] = _refresh_centrality()

    summary["elapsed_s"] = round(time.perf_counter() - started, 1)
    logger.info(f"ingestion complete in {summary['elapsed_s']}s: {summary['documents_ready']} ready")
    return summary
