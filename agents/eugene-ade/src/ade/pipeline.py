"""Ingestion orchestration — the only module that composes the others.

fetch → store PDF → structural parse → DL layout merge → write artifacts.

Idempotent by design: `doc_id` is deterministic, so re-ingesting a paper returns
the cached manifest instead of re-downloading and re-parsing. That matters because
the UI auto-ingests every result of every literature search — without idempotency
a user running the same query twice would pay for the whole pipeline twice.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from typing import Any

import fitz

from ade import detectors, enrich, indexer, layout, parser, storage, tables, verify
from ade.fetch import PdfUnavailable, doc_id_for, fetch_pdf

logger = logging.getLogger(__name__)

ARTIFACT_VERSION = "1.0"

# Bound how many documents extract at once.
#
# Measured without this: a 5-document batch fired 5 concurrent YOLO inferences
# and pushed the container to 1211% CPU. Each individual document got slower and
# the box had nothing left for the graph/vector services sharing it. Layout
# detection is CPU-saturating by nature, so the useful concurrency is small —
# queueing is strictly better than thrashing.
_MAX_CONCURRENT = int(os.environ.get("ADE_MAX_CONCURRENT_INGESTS", "2"))
# Text repeated on at least this fraction of a document's pages is furniture.
# A third is comfortably above any legitimate repetition (a recurring section
# heading) and comfortably below a watermark, which hits nearly every page.
_FURNITURE_PAGE_FRACTION = 0.34
_ingest_slots = threading.Semaphore(_MAX_CONCURRENT)


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()




def _demote_page_furniture(chunks: list[dict[str, Any]], page_count: int) -> int:
    """Reclassify repeated page furniture as marginalia.

    The band heuristic in `parser._classify` only catches text in the top/bottom
    8% of a page. It misses the two most common kinds of furniture in journal
    PDFs: rotated sidebar watermarks and footers that sit just inside the band.
    Measured on one PMC manuscript, "Author Manuscript" was emitted 51 times and
    a journal footer 50 times, all indexed as substantive text — 101 junk chunks
    that would each compete for retrieval against real passages.

    The signal is repetition across PAGES, not position: text appearing on a
    large fraction of pages is furniture whatever its coordinates. A real passage
    is not reprinted on two-thirds of the document.
    """
    if page_count < 3:
        return 0

    by_text: dict[str, set[int]] = {}
    for c in chunks:
        if c.get("chunk_type") in ("table_cell", "marginalia"):
            continue
        t = str(c.get("text", "")).strip()
        if t:
            by_text.setdefault(t, set()).add(int(c.get("page", 0)))

    threshold = max(3, int(page_count * _FURNITURE_PAGE_FRACTION))
    furniture = {t for t, pages in by_text.items() if len(pages) >= threshold}
    if not furniture:
        return 0

    demoted = 0
    for c in chunks:
        if str(c.get("text", "")).strip() in furniture and c.get("chunk_type") != "marginalia":
            c["chunk_type"] = "marginalia"
            c["demoted_reason"] = "repeated_page_furniture"
            demoted += 1
    logger.info(
        f"demoted {demoted} chunk(s) as page furniture "
        f"({len(furniture)} distinct string(s) on >= {threshold}/{page_count} pages)"
    )
    return demoted


def _expand_table_cells(
    pdf_bytes: bytes,
    chunks: list[dict[str, Any]],
    doc_id: str,
    grounding: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Emit a `table_cell` chunk per reconstructed cell of every table region.

    The parent table chunk is kept: an LLM reading the answer wants the table as
    a readable whole, while the cells carry the geometry that makes a single
    number citable. Cell ids derive from the parent's element id plus (row, col),
    so they are as deterministic as everything else (M2).
    """
    import fitz

    table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
    if not table_chunks:
        return chunks

    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        extra: list[dict[str, Any]] = []
        order = max((c.get("order", 0) for c in chunks), default=0) + 1
        for parent in table_chunks:
            pno = parent.get("page", 0)
            if pno >= doc.page_count:
                continue
            cells = tables.extract_cells(doc[pno], parent["bbox"])
            if not cells:
                continue
            # Replace the region's text with the reconstructed grid — far more
            # readable than the raw block text the layout region contained.
            md = tables.to_markdown(cells)
            if md:
                parent["text"] = md
                parent["content_hash"] = parser._content_hash(md)
            parent["cell_count"] = len(cells)
            parent["table_rows"] = max(c["row"] for c in cells) + 1
            parent["table_cols"] = max(c["col"] for c in cells) + 1

            for cell in cells:
                eid = f"{parent['element_id']}-r{cell['row']}c{cell['col']}"
                cid = parser._chunk_id(doc_id, order, eid)
                extra.append({
                    "chunk_id": cid, "chunk_type": "table_cell", "page": pno,
                    "page_start": pno, "page_end": pno,
                    "bbox": cell["bbox"], "text": cell["text"], "order": order,
                    "element_id": eid,
                    "content_hash": parser._content_hash(cell["text"]),
                    "parser_confidence": 1.0,
                    "table_row": cell["row"], "table_col": cell["col"],
                    "parent_chunk_id": parent["chunk_id"],
                })
                # The renderer resolves a chunk through `grounding`, not through
                # `chunks` — without this a cell exists but cannot be rendered,
                # which is a 404 on the one thing cell-level grounding is for.
                if grounding is not None:
                    grounding[cid] = {
                        "page": pno, "box": cell["bbox"], "type": "chunkTableCell",
                    }
                order += 1
        if extra:
            logger.info(
                f"{doc_id}: expanded {len(table_chunks)} table(s) into {len(extra)} cells"
            )
        return chunks + extra
    finally:
        doc.close()


def get_manifest(doc_id: str) -> dict[str, Any] | None:
    st = storage.storage()
    key = storage.key_manifest(doc_id)
    if not st.exists(key):
        return None
    return st.get_json(key)


def _detect_layout(pdf_bytes: bytes) -> dict[int, list[dict]]:
    """Run the detector over every page. Empty dict when the model is unavailable."""
    if not layout.available():
        return {}
    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        out: dict[int, list[dict]] = {}
        for pno in range(doc.page_count):
            regions = layout.detect_page(doc[pno])
            if regions:
                out[pno] = regions
        return out
    finally:
        doc.close()


def ingest(source: str, ident: str, force: bool = False) -> dict[str, Any]:
    """Run the full pipeline for one document and return its manifest."""
    doc_id = doc_id_for(source, ident)
    st = storage.storage()

    # The cache check is deliberately OUTSIDE the concurrency gate: an already
    # extracted document costs one S3 HEAD and must not queue behind live
    # extractions.
    if not force:
        cached = get_manifest(doc_id)
        # `failed` means a transient error (network blip, killed container) and
        # MUST stay retryable — caching it would make one bad moment permanent.
        # `unavailable` (paywalled) is cached on purpose: that answer won't change
        # on a retry, and re-fetching it on every search is pure waste.
        if cached and cached.get("status") != "failed":
            logger.info(f"{doc_id}: cache hit ({cached.get('status')}), skipping pipeline")
            cached["cached"] = True
            return cached
        if cached:
            logger.info(f"{doc_id}: previous attempt failed, retrying")

    with _ingest_slots:
        return _run_pipeline(doc_id, source, ident, st)


def _run_pipeline(doc_id: str, source: str, ident: str, st: storage.Storage) -> dict[str, Any]:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    # 1. FETCH ---------------------------------------------------------------
    try:
        fetched = fetch_pdf(source, ident)
    except PdfUnavailable as e:
        # An expected outcome, not a failure: record it so the UI can explain
        # itself and so we don't retry a paywalled paper on every search.
        manifest = {
            "doc_id": doc_id, "status": "unavailable", "reason": e.reason,
            "source": source, "identifier": ident, "metadata": e.metadata,
            "ingested_at": _now(), "artifact_version": ARTIFACT_VERSION,
        }
        st.put_json(storage.key_manifest(doc_id), manifest)
        return manifest
    timings["fetch_s"] = round(time.perf_counter() - t0, 2)

    # 2. STORE the original bytes, unmodified — this is the evidence of record.
    t = time.perf_counter()
    pdf_uri = st.put_bytes(storage.key_pdf(doc_id), fetched.pdf, "application/pdf")
    timings["store_pdf_s"] = round(time.perf_counter() - t, 2)

    # 3. PARSE ---------------------------------------------------------------
    t = time.perf_counter()
    # doc_id is passed through so chunk ids are derived from it (M2) — the same
    # document always yields the same chunk ids.
    parsed = parser.parse_pdf(fetched.pdf, doc_id=doc_id)
    timings["parse_s"] = round(time.perf_counter() - t, 2)

    # 4. LAYOUT --------------------------------------------------------------
    t = time.perf_counter()
    regions = _detect_layout(fetched.pdf)
    chunks = layout.merge(parsed["chunks"], regions)
    timings["layout_s"] = round(time.perf_counter() - t, 2)

    # 4b. CELL-LEVEL TABLE GROUNDING.
    #
    # Must run AFTER the layout merge, not inside the parser: `find_tables()`
    # returns nothing on these borderless academic tables, so the only reliable
    # signal that a region IS a table is the layout model's label. Each cell
    # becomes its own chunk with its own box, so a claim about one number
    # highlights that cell rather than a twenty-row table.
    t = time.perf_counter()
    _demote_page_furniture(chunks, parsed["page_count"])
    chunks = _expand_table_cells(fetched.pdf, chunks, doc_id, parsed["grounding"])
    timings["table_cells_s"] = round(time.perf_counter() - t, 2)

    # 4c. VERIFY — the agentic checking step. Retries with different layout
    # settings when the extraction misses too much, rather than accepting it.
    t = time.perf_counter()
    verdict = verify.verify(fetched.pdf, chunks, attempt=1)
    attempt = 1
    while not verdict.passed and attempt < 3:
        attempt += 1
        settings = verify.retry_settings(attempt)
        logger.warning(
            f"{doc_id}: verification failed ({verdict.failures}); "
            f"retry {attempt} — {settings.get('reason')}"
        )
        reparsed = parser.parse_pdf(
            fetched.pdf, doc_id=doc_id,
            detect_visuals=settings.get("layout_enabled", True),
        )
        retry_chunks = reparsed["chunks"]
        if settings.get("layout_enabled", True):
            retry_chunks = layout.merge(retry_chunks, _detect_layout(fetched.pdf))
        retry_chunks = _expand_table_cells(
            fetched.pdf, retry_chunks, doc_id, reparsed["grounding"]
        )
        retry_verdict = verify.verify(fetched.pdf, retry_chunks, attempt=attempt)
        # Keep the better attempt, not merely the last one.
        if retry_verdict.score > verdict.score:
            chunks, verdict, parsed = retry_chunks, retry_verdict, reparsed
        if retry_verdict.passed:
            break
    timings["verify_s"] = round(time.perf_counter() - t, 2)

    # 4d. DOMAIN ENRICHMENT — tag each chunk with the drugs/diseases it names,
    # so structured retrieval can filter before ranking.
    t = time.perf_counter()
    for ch in chunks:
        ch.update(enrich.tag_chunk(ch.get("text", "")))
    areas = enrich.document_areas(chunks)
    timings["enrich_s"] = round(time.perf_counter() - t, 2)

    # Every chunk carries its own provenance so a chunk lifted out of context
    # still knows which document and page it belongs to.
    for ch in chunks:
        ch["doc_id"] = doc_id
        ch["source"] = fetched.metadata.get("europepmc_url") or pdf_uri

    # 5. ARTIFACTS -----------------------------------------------------------
    t = time.perf_counter()
    st.put_bytes(
        storage.key_markdown(doc_id), parsed["markdown"].encode("utf-8"),
        "text/markdown; charset=utf-8",
    )
    st.put_json(storage.key_chunks(doc_id), chunks)
    st.put_json(storage.key_grounding(doc_id), parsed["grounding"])
    timings["artifacts_s"] = round(time.perf_counter() - t, 2)

    type_counts: dict[str, int] = {}
    for ch in chunks:
        type_counts[ch["chunk_type"]] = type_counts.get(ch["chunk_type"], 0) + 1

    manifest: dict[str, Any] = {
        "doc_id": doc_id,
        "status": "ready",
        "source": source,
        "identifier": ident,
        "metadata": fetched.metadata,
        "pdf_uri": pdf_uri,
        "pdf_sha256": hashlib.sha256(fetched.pdf).hexdigest(),
        "pdf_bytes": len(fetched.pdf),
        "page_count": parsed["page_count"],
        "chunk_count": len(chunks),
        "chunk_types": type_counts,
        "text_layer": parsed["text_layer"],
        # Quality verdict from the agentic checking loop — recorded whether it
        # passed or not, so a poor extraction is visible rather than silently
        # degrading every answer built on it.
        "verification": verdict.as_dict(),
        "therapeutic_areas": areas,
        "cell_level_tables": sum(1 for c in chunks if c.get("chunk_type") == "table_cell"),
        "layout_model": layout.available(),
        "layout_pages_detected": len(regions),
        "pages": parsed["pages"],
        "timings": timings,
        "total_s": round(time.perf_counter() - t0, 2),
        "ingested_at": _now(),
        "artifact_version": ARTIFACT_VERSION,
    }
    # 6. INDEX into the knowledge graph so fused retrieval can surface passages.
    #    Deliberately AFTER the manifest is composed but reported inside it: a
    #    graph-write failure must not discard an extraction whose artifacts are
    #    already durable in S3.
    t = time.perf_counter()
    manifest["graph_index"] = indexer.index_document(manifest, chunks)
    timings["index_s"] = round(time.perf_counter() - t, 2)
    manifest["total_s"] = round(time.perf_counter() - t0, 2)

    st.put_json(storage.key_manifest(doc_id), manifest)
    logger.info(
        f"{doc_id}: ready — {parsed['page_count']} pages, {len(chunks)} chunks, "
        f"{manifest['total_s']}s"
    )
    return manifest


def reindex(doc_id: str) -> dict[str, Any]:
    """Re-run only the graph-indexing step from artifacts already in S3.

    Backfill path: extraction is expensive (YOLO dominates at ~40s/document) but
    indexing is cheap, so a schema change or a newly-enabled graph index must not
    force a full re-extraction of the corpus.
    """
    st = storage.storage()
    manifest = get_manifest(doc_id)
    if not manifest:
        return {"doc_id": doc_id, "indexed": False, "reason": "not ingested"}
    if manifest.get("status") != "ready":
        return {"doc_id": doc_id, "indexed": False, "reason": manifest.get("status")}
    chunks = st.get_json(storage.key_chunks(doc_id))
    result = indexer.index_document(manifest, chunks)
    manifest["graph_index"] = result
    st.put_json(storage.key_manifest(doc_id), manifest)
    return {"doc_id": doc_id, **result}


def list_documents() -> list[str]:
    """Every doc_id with a manifest in S3."""
    st = storage.storage()
    out: list[str] = []
    try:
        paginator = st._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=st.bucket, Prefix="documents/", Delimiter="/"
        ):
            for p in page.get("CommonPrefixes", []) or []:
                doc_id = p["Prefix"].removeprefix("documents/").rstrip("/")
                if doc_id:
                    out.append(doc_id)
    except Exception as e:
        logger.warning(f"list documents failed: {e}")
    return out


def ingest_safe(source: str, ident: str, force: bool = False) -> dict[str, Any]:
    """`ingest` that PERSISTS unexpected errors as a 'failed' manifest.

    Used by the background batch path, where an exception has nowhere to surface
    and would otherwise vanish into a task queue.

    Persisting the failure is the point. Returning it is not enough: a background
    task's return value goes nowhere, so a document whose pipeline died midway
    left `source.pdf` in S3 with no manifest and read as "never ingested" forever
    — observed after a container restart killed an in-flight extraction. Writing
    the failure means the UI can say "extraction failed, retry" instead of
    silently offering nothing.
    """
    try:
        return ingest(source, ident, force=force)
    except Exception as e:
        logger.exception(f"ingest failed for {source}:{ident}")
        doc_id = doc_id_for(source, ident)
        manifest = {
            "doc_id": doc_id, "status": "failed",
            "reason": f"{type(e).__name__}: {e}", "source": source,
            "identifier": ident, "ingested_at": _now(),
            "artifact_version": ARTIFACT_VERSION,
            # `ingest` treats a missing manifest as "not yet done", so a retry
            # would be blocked by this record. Say so explicitly.
            "retryable": True,
        }
        try:
            storage.storage().put_json(storage.key_manifest(doc_id), manifest)
        except Exception:
            logger.exception(f"could not persist failure manifest for {doc_id}")
        return manifest
