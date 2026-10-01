"""Index extracted papers into the Eugene knowledge graph.

Without this step the extraction pipeline is a dead end: chunks sit in S3 where
only the evidence viewer can reach them, so the agent can *cite* a paper it found
but cannot *retrieve* what the paper actually says. Writing chunks into Neo4j puts
them in the same store as drugs, diseases and trials — which means fused retrieval
can surface a specific paragraph of a specific paper as evidence, and the answer
can link straight to the highlighted region it came from.

Graph shape:

    (:paper {doc_id, title, doi, pmid, pmcid, year, journal, url})
      -[:has_chunk]-> (:paper_chunk {chunk_id, doc_id, page, bbox_*, text, chunk_type})
    (:paper) -[:mentions]-> (:drug | :disease)     ← name-matched, same as CT.gov

`paper_chunk` nodes carry `doc_id` + `chunk_id`, which is exactly the pair the
evidence renderer needs. That is the whole point: a retrieved passage knows how to
prove itself.

Single-writer discipline: this module owns the paper/chunk subgraph in Neo4j.
Milvus embedding happens separately in eugene_ws (`corpus_ingest_service`), because
milvus-lite is an embedded single-process store and only that service may open it.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from neo4j import GraphDatabase, Query

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get("ADE_GRAPH_INDEX_ENABLED", "true").lower() != "false"
# Chunk types that carry no retrievable meaning. Indexing running heads and page
# numbers would pollute retrieval with "Page 7 of 14".
_SKIP_TYPES = {"marginalia", "figure"}
_MIN_CHARS = 80

_PAREN = re.compile(r"\([^)]*\)")
_NONWORD = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
        user = os.environ.get("NEO4J_USERNAME", "neo4j")
        pwd = os.environ.get("NEO4J_PASSWORD", "eugene_local_2024")
        _driver = GraphDatabase.driver(uri, auth=(user, pwd))
    return _driver


def available() -> bool:
    return _ENABLED


def _normalize(name: str) -> str:
    s = (name or "").lower().strip()
    s = _PAREN.sub(" ", s)
    s = _NONWORD.sub(" ", s)
    return _WS.sub(" ", s).strip()


def ensure_schema() -> None:
    """Indexes the retrieval path depends on. Idempotent."""
    stmts = [
        "CREATE CONSTRAINT paper_doc_id IF NOT EXISTS FOR (p:paper) REQUIRE p.doc_id IS UNIQUE",
        "CREATE CONSTRAINT paper_chunk_id IF NOT EXISTS FOR (c:paper_chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE INDEX paper_chunk_doc IF NOT EXISTS FOR (c:paper_chunk) ON (c.doc_id)",
        "CREATE INDEX paper_name IF NOT EXISTS FOR (p:paper) ON (p.node_name)",
        # Full-text over passages — this is what the fusion graph retriever hits.
        "CREATE FULLTEXT INDEX paper_chunk_fulltext IF NOT EXISTS "
        "FOR (c:paper_chunk) ON EACH [c.text]",
    ]
    drv = _get_driver()
    for s in stmts:
        try:
            drv.execute_query(Query(s))  # type: ignore[arg-type]
        except Exception as e:
            logger.warning(f"schema stmt failed ({s.split()[2]}): {e}")


def index_document(manifest: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Write one extracted paper and its chunks into the graph.

    Returns counts. Never raises: a graph write failure must not invalidate an
    otherwise good extraction whose artifacts are already durable in S3.
    """
    if not _ENABLED:
        return {"indexed": False, "reason": "ADE_GRAPH_INDEX_ENABLED=false"}

    doc_id = manifest.get("doc_id", "")
    meta = manifest.get("metadata") or {}
    try:
        ensure_schema()
        drv = _get_driver()

        # 1. Paper node. `node_name`/`node_id` mirror the graph's existing
        #    convention so generic lookups and the fusion retriever see it as a
        #    first-class entity rather than a special case.
        drv.execute_query(
            Query(
                "MERGE (p:paper {doc_id: $doc_id}) "
                "SET p.node_id = $doc_id, p.node_name = $title, p.title = $title, "
                "    p.doi = $doi, p.pmid = $pmid, p.pmcid = $pmcid, p.year = $year, "
                "    p.journal = $journal, p.authors = $authors, p.url = $url, "
                "    p.node_source = 'ADE (Europe PMC)', p.page_count = $pages, "
                "    p.indexed_at = datetime()"
            ),  # type: ignore[arg-type]
            doc_id=doc_id,
            title=(meta.get("title") or doc_id)[:500],
            doi=meta.get("doi", ""), pmid=meta.get("pmid", ""),
            pmcid=meta.get("pmcid", ""), year=meta.get("year", ""),
            journal=meta.get("journal", ""), authors=(meta.get("authors") or "")[:500],
            url=meta.get("europepmc_url") or meta.get("publisher_url", ""),
            pages=manifest.get("page_count", 0),
        )

        # 2. Chunks. Batched via UNWIND — one round trip per document instead of
        #    one per chunk (documents run to 643 chunks).
        rows = [
            {
                "chunk_id": c["chunk_id"],
                "doc_id": doc_id,
                "page": c["page"],
                "text": c["text"][:8000],
                "chunk_type": c.get("chunk_type", "text"),
                "left": c["bbox"]["left"], "top": c["bbox"]["top"],
                "right": c["bbox"]["right"], "bottom": c["bbox"]["bottom"],
                "order": c.get("order", 0),
                # M1 — provenance properties stored as ordinary queryable fields,
                # not sidecar JSON. `content_hash` lets a stored citation be
                # proven to reference the exact same bytes years later.
                "element_id": c.get("element_id", ""),
                "content_hash": c.get("content_hash", ""),
                "parser_confidence": float(c.get("parser_confidence") or 0.0),
                "layout_confidence": float(c.get("layout_confidence") or 0.0),
                "layout_label": c.get("layout_label", ""),
                # Markdown span (ADE's evidence-link mechanism) and page range.
                "md_start": int((c.get("markdown_range") or {}).get("start", -1)),
                "md_end": int((c.get("markdown_range") or {}).get("end", -1)),
                "page_start": int(c.get("page_start", c.get("page", 0))),
                "page_end": int(c.get("page_end", c.get("page", 0))),
                # Cell-level grounding
                "table_row": int(c.get("table_row", -1)),
                "table_col": int(c.get("table_col", -1)),
                "parent_chunk_id": c.get("parent_chunk_id", ""),
                # Domain enrichment — what structured filtering keys off.
                "drugs": c.get("drugs") or [],
                "diseases": c.get("diseases") or [],
                # Visual detectors
                "scan_code_payload": c.get("scan_code_payload", ""),
                "visual_confidence": float(c.get("visual_confidence") or 0.0),
                "heuristic": bool(c.get("heuristic", False)),
            }
            for c in chunks
            # Table cells bypass the length floor: "30.94 (6.43, 148.75)" is
            # short and is exactly the thing a numeric claim needs to cite.
            if c.get("chunk_type") not in _SKIP_TYPES
            and (c.get("chunk_type") == "table_cell" or len(c.get("text", "")) >= _MIN_CHARS)
        ]
        if rows:
            drv.execute_query(
                Query(
                    "MATCH (p:paper {doc_id: $doc_id}) "
                    "UNWIND $rows AS row "
                    "MERGE (c:paper_chunk {chunk_id: row.chunk_id}) "
                    "SET c:evidence_span "
                    "SET c.doc_id = row.doc_id, c.node_id = row.chunk_id, "
                    "    c.node_name = left(row.text, 200), c.text = row.text, "
                    "    c.page = row.page, c.chunk_type = row.chunk_type, "
                    "    c.bbox_left = row.left, c.bbox_top = row.top, "
                    "    c.bbox_right = row.right, c.bbox_bottom = row.bottom, "
                    "    c.order = row.order, c.node_source = 'ADE', "
                    "    c.element_id = row.element_id, c.content_hash = row.content_hash, "
                    "    c.parser_confidence = row.parser_confidence, "
                    "    c.layout_confidence = row.layout_confidence, "
                    "    c.layout_label = row.layout_label, "
                    "    c.md_start = row.md_start, c.md_end = row.md_end, "
                    "    c.page_start = row.page_start, c.page_end = row.page_end, "
                    "    c.table_row = row.table_row, c.table_col = row.table_col, "
                    "    c.parent_chunk_id = row.parent_chunk_id, "
                    "    c.drugs = row.drugs, c.diseases = row.diseases, "
                    "    c.scan_code_payload = row.scan_code_payload, "
                    "    c.visual_confidence = row.visual_confidence, "
                    "    c.heuristic = row.heuristic "
                    "MERGE (p)-[:has_chunk]->(c)"
                ),  # type: ignore[arg-type]
                doc_id=doc_id, rows=rows,
            )

        # 2b. Remove chunks that are no longer part of this document.
        #
        # Without this, re-extracting a document leaves its previous chunks
        # behind: MERGE creates nodes for the new ids and the old ones stay
        # attached to the paper. Observed when 12 documents were re-ingested
        # under deterministic ids (M2) — the graph grew from 5,235 to 6,375
        # chunks, silently holding two copies of every passage, and retrieval
        # would return both. Reconciling against the current id set makes
        # re-ingestion converge instead of accumulate.
        current_ids = [r["chunk_id"] for r in rows]
        stale, _, _ = drv.execute_query(
            Query(
                "MATCH (p:paper {doc_id: $doc_id})-[:has_chunk]->(c:paper_chunk) "
                "WHERE NOT c.chunk_id IN $keep "
                "DETACH DELETE c RETURN count(*) AS removed"
            ),  # type: ignore[arg-type]
            doc_id=doc_id, keep=current_ids,
        )
        removed = stale[0]["removed"] if stale else 0
        if removed:
            logger.info(f"{doc_id}: removed {removed} stale chunk(s) from a prior extraction")

        # 3. Link the paper to entities it names. Same normalized-name strategy
        #    as the CT.gov loader — an unlinked paper is searchable but not
        #    traversable from a drug or disease.
        mentions = _link_entities(drv, doc_id, meta, chunks)

        logger.info(f"{doc_id}: indexed {len(rows)} chunks, {mentions} entity links")
        return {"indexed": True, "chunks": len(rows), "mentions": mentions}
    except Exception as e:
        logger.exception(f"graph indexing failed for {doc_id}")
        return {"indexed": False, "reason": f"{type(e).__name__}: {e}"}


def _link_entities(drv, doc_id: str, meta: dict, chunks: list[dict]) -> int:
    """Link the paper to drug/disease nodes whose names appear in it.

    Scoped to the title plus the first few substantive chunks (title/abstract
    territory): scanning every chunk of a 643-chunk review would match dozens of
    incidentally-mentioned drugs and make `mentions` meaningless.
    """
    text_parts = [meta.get("title") or ""]
    for c in sorted(chunks, key=lambda x: x.get("order", 0)):
        if c.get("chunk_type") in ("text", "title") and len(c.get("text", "")) >= 120:
            text_parts.append(c["text"])
        if len(text_parts) >= 6:
            break
    haystack = _normalize(" ".join(text_parts))
    if not haystack:
        return 0

    # Candidate entity names, filtered server-side by length so we don't drag
    # 25k names across the wire. Short names ("Oxygen", "Iron") match far too
    # eagerly inside prose, so they are excluded by the length floor.
    records, _, _ = drv.execute_query(
        Query(
            "MATCH (n) WHERE (n:drug OR n:disease) AND n.node_name IS NOT NULL "
            "AND size(n.node_name) >= 6 "
            "RETURN n.node_index AS idx, n.node_name AS name, labels(n)[0] AS label"
        )  # type: ignore[arg-type]
    )
    hits = []
    for r in records:
        norm = _normalize(r["name"])
        if len(norm) < 6:
            continue
        # Word-boundary containment: "april" must not match "aprilia".
        if f" {norm} " in f" {haystack} ":
            hits.append({"idx": str(r["idx"]), "label": r["label"]})

    if not hits:
        return 0
    # Cap so a broad review can't create hundreds of weak edges.
    hits = hits[:40]
    drv.execute_query(
        Query(
            "MATCH (p:paper {doc_id: $doc_id}) "
            "UNWIND $hits AS h "
            "MATCH (e) WHERE e.node_index = h.idx AND (e:drug OR e:disease) "
            "MERGE (p)-[m:mentions]->(e) "
            "SET m.source = 'ADE name match'"
        ),  # type: ignore[arg-type]
        doc_id=doc_id, hits=hits,
    )
    return len(hits)
