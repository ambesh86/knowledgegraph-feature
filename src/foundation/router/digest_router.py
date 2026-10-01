"""Researcher digest — what actually changed, for this researcher's areas.

The previous "While you were away" panel queried live external APIs, sorted by
date, and displayed whatever came back. Three things were wrong with that:

  * Europe PMC does not reliably honour `sort=P_PDATE_D desc` on these queries —
    measured results came back in the order 2026-06-11, 2026-07-01, 2026-03-03,
    which is not sorted at all. "Latest" was never latest.
  * There was no date FILTER, only a sort. So the patent column happily showed
    2002-2010 grants under a heading that says "overnight".
  * Nothing connected the panel to the ingestion pipeline that actually runs at
    01:00 — the one part of the system that genuinely knows what is new.

This endpoint fixes the foundation: the primary signal is **our own graph**,
where every paper carries `indexed_at` from the nightly run. That is provably
fresh, provably scoped to the declared research areas, and needs no external call
to be trustworthy. Live external sources remain useful for breadth, but they are
a supplement, not the source of truth — and the UI is expected to date-filter
them rather than trust an unhonoured sort.

An empty result is a real answer here. If nothing was published overnight in a
narrow area, the honest output is zero items, not a decade-old patent.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body
from neo4j import Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])

# Keep the digest cheap enough to run on every page load.
_MAX_LIMIT = 25


def _driver():
    from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory

    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _since(value: str | None, default_hours: int = 24) -> dt.datetime:
    """Parse the caller's `since`, falling back to a sensible window."""
    if value:
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except ValueError:
            logger.warning(f"unparseable since={value!r}; using default window")
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=default_hours)


@router.post("/digest")
async def digest(
    payload: Annotated[dict[str, Any], Body()] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """What landed in this researcher's areas since `since`.

    Body: {keywords: [...], since: ISO8601, limit: int}

    Keywords come from the caller rather than being defined here on purpose: the
    focus-area taxonomy already lives in the UI (`lib/atlas/areas.ts`) and the
    ingestion config (`research_areas.yaml`). Duplicating it into a third place
    would guarantee the three drift apart.
    """
    body = payload or {}
    keywords = [str(k).lower().strip() for k in (body.get("keywords") or []) if str(k).strip()]
    since = _since(body.get("since"))
    limit = max(1, min(int(body.get("limit") or 8), _MAX_LIMIT))

    out: dict[str, Any] = {
        "since": since.isoformat(),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "keywords": keywords,
        "papers": [],
        "trials": [],
        "corpus": {},
    }

    try:
        drv = _driver()

        # 1. Papers this pipeline ingested in the window, scoped to the area.
        #    Matching is against the title AND the diseases tagged on the paper's
        #    own passages, so a paper about IgA nephropathy surfaces for a
        #    nephrology researcher even when the title never says "nephrology".
        recs, _, _ = drv.execute_query(
            Query(
                "MATCH (p:paper) WHERE p.indexed_at >= $since "
                "OPTIONAL MATCH (p)-[:has_chunk]->(c:paper_chunk) "
                "WITH p, [d IN collect(DISTINCT c.diseases) | d] AS nested "
                "WITH p, reduce(acc = [], x IN nested | acc + x) AS diseases "
                "RETURN p.doc_id AS doc_id, p.title AS title, p.journal AS journal, "
                "       p.year AS year, p.authors AS authors, p.url AS url, "
                "       p.pmid AS pmid, p.pmcid AS pmcid, "
                "       toString(p.indexed_at) AS indexed_at, "
                "       p.page_count AS pages, diseases "
                "ORDER BY p.indexed_at DESC LIMIT 200"
            ),  # type: ignore[arg-type]
            since=since,
        )

        papers: list[dict[str, Any]] = []
        for r in recs:
            d = dict(r)
            hay = " ".join(
                [str(d.get("title") or "")] + [str(x) for x in (d.get("diseases") or [])]
            ).lower()
            # No keywords means "everything"; the caller decides the scope.
            if keywords and not any(k in hay for k in keywords):
                continue
            matched = sorted({k for k in keywords if k in hay})
            papers.append({
                "doc_id": d.get("doc_id"),
                "title": d.get("title"),
                "journal": d.get("journal"),
                "year": d.get("year"),
                "authors": d.get("authors"),
                "url": d.get("url"),
                "pmid": d.get("pmid"),
                "pmcid": d.get("pmcid"),
                "indexed_at": d.get("indexed_at"),
                "pages": d.get("pages"),
                "matched_keywords": matched,
                # The payoff of ingesting rather than merely linking: this paper
                # is already extracted, so the evidence viewer works immediately.
                "has_evidence": True,
            })
        out["papers"] = papers[:limit]
        out["papers_total"] = len(papers)

        # 2. Trials from the ingested snapshot, most recently started first.
        trial_recs, _, _ = drv.execute_query(
            Query(
                "MATCH (t:clinical_trial) WHERE t.start_date <> '' "
                "RETURN t.nct_id AS nct_id, t.title AS title, t.status AS status, "
                "       t.phase AS phase, t.sponsor AS sponsor, t.url AS url, "
                "       t.start_date AS start_date, t.conditions AS conditions "
                "ORDER BY t.start_date DESC LIMIT 300"
            )  # type: ignore[arg-type]
        )
        trials: list[dict[str, Any]] = []
        for r in trial_recs:
            d = dict(r)
            hay = f"{d.get('title') or ''} {d.get('conditions') or ''}".lower()
            if keywords and not any(k in hay for k in keywords):
                continue
            trials.append({k: d.get(k) for k in
                           ("nct_id", "title", "status", "phase", "sponsor", "url", "start_date")})
        out["trials"] = trials[:limit]
        out["trials_total"] = len(trials)

        # 3. Corpus state — lets the UI say what the digest is drawn from rather
        #    than implying it searched the whole world.
        stat, _, _ = drv.execute_query(
            Query(
                "MATCH (p:paper) WITH count(p) AS papers, max(p.indexed_at) AS last "
                "MATCH (c:paper_chunk) WITH papers, last, count(c) AS passages "
                "MATCH (t:clinical_trial) "
                "RETURN papers, passages, count(t) AS trials, toString(last) AS last_ingest_at"
            )  # type: ignore[arg-type]
        )
        if stat:
            out["corpus"] = dict(stat[0])

    except Exception as e:
        logger.exception("digest query failed")
        out["error"] = f"{type(e).__name__}: {e}"

    logger.info(
        f"digest: {len(out['papers'])} papers, {len(out['trials'])} trials "
        f"since {since.isoformat()} keywords={keywords}"
    )
    return out
