"""FastAPI surface for the ADE service.

All PDF work is CPU-bound and blocking (PyMuPDF, YOLO, S3), so every handler that
touches it runs in a threadpool via `run_in_threadpool`. Doing that work inline
would stall the event loop and make concurrent requests queue behind a single
40-page parse.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ade import layout, pipeline, render, storage

logger = logging.getLogger(__name__)

# Extraction and evidence rendering are separable, and the split matters where
# egress is not available: fetching a PDF needs the public internet, but every
# artifact it produces — chunks, grounding, page renders — is read back out of
# S3. So an instance with no internet can still prove every claim in an answer
# for documents already extracted elsewhere.
#
# ADE_INGEST_ENABLED=false makes that mode explicit rather than leaving a fetch
# to fail with a connection timeout that reads like a bug.
INGEST_ENABLED = os.environ.get("ADE_INGEST_ENABLED", "true").lower() == "true"


def _require_ingest() -> None:
    if not INGEST_ENABLED:
        raise HTTPException(
            status_code=409,
            detail=(
                "This instance is serve-only (ADE_INGEST_ENABLED=false): it renders "
                "evidence from artifacts already in S3 but has no route to the "
                "internet to fetch new PDFs. Run ingestion where egress exists; "
                "the artifacts land in the same bucket and are served from here."
            ),
        )



@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load YOLO weights at boot so the first user request doesn't pay for it."""
    ok = await run_in_threadpool(layout.warm)
    logger.info(f"layout model warm: {ok}")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Eugene ADE",
    description=(
        "Agentic document extraction with full evidence provenance: fetch research "
        "PDFs, store in S3, extract Markdown + grounded JSON chunks, and render the "
        "exact source region an answer came from."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
SourceKind = Literal["pubmed", "europepmc", "pmc", "url"]


class IngestRequest(BaseModel):
    source: SourceKind = "europepmc"
    id: str = Field(..., description="PMID, PMCID, DOI or URL", min_length=1)
    force: bool = False


class BatchItem(BaseModel):
    source: SourceKind = "europepmc"
    id: str


class BatchRequest(BaseModel):
    items: list[BatchItem] = Field(default_factory=list, max_length=25)
    force: bool = False


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, Any]:
    st = await run_in_threadpool(lambda: storage.storage().health())
    return {
        "status": "OK" if st.get("ok") else "DEGRADED",
        "service": "eugene-ade",
        "s3": st,
        "layout_model": {
            "enabled": layout.available(),
            "repo": layout._REPO_ID,
        },
        "ingest": {
            "enabled": INGEST_ENABLED,
            "mode": "ingest+serve" if INGEST_ENABLED else "serve-only",
        },
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
@app.post("/ade/ingest")
async def ingest(req: IngestRequest) -> dict[str, Any]:
    """Run the extraction pipeline for one document (idempotent)."""
    _require_ingest()
    return await run_in_threadpool(pipeline.ingest_safe, req.source, req.id, req.force)


@app.post("/ade/ingest/batch")
async def ingest_batch(req: BatchRequest, background: BackgroundTasks) -> dict[str, Any]:
    """Queue every item for background ingestion and return immediately.

    Used to pre-warm evidence for a whole result set, so the paper is already
    extracted by the time the user clicks it.
    """
    _require_ingest()
    accepted = []
    for item in req.items:
        background.add_task(pipeline.ingest_safe, item.source, item.id, req.force)
        accepted.append({"source": item.source, "id": item.id})
    return {"accepted": len(accepted), "items": accepted, "status": "queued"}


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------
@app.post("/ade/reindex")
async def reindex_all(doc_id: str | None = Query(None, description="one doc, or all")) -> dict[str, Any]:
    """Re-run graph indexing from existing S3 artifacts — no re-extraction.

    Backfill after a schema change or after enabling graph indexing on a corpus
    that was extracted without it.
    """
    def _run() -> dict[str, Any]:
        ids = [doc_id] if doc_id else pipeline.list_documents()
        results = [pipeline.reindex(d) for d in ids]
        ok = [r for r in results if r.get("indexed")]
        return {
            "documents": len(ids),
            "indexed": len(ok),
            "chunks": sum(int(r.get("chunks") or 0) for r in ok),
            "mentions": sum(int(r.get("mentions") or 0) for r in ok),
            "results": results,
        }

    return await run_in_threadpool(_run)


@app.get("/ade/documents/{doc_id}")
async def get_document(doc_id: str) -> dict[str, Any]:
    manifest = await run_in_threadpool(pipeline.get_manifest, doc_id)
    if manifest is None:
        raise HTTPException(404, f"{doc_id} has not been ingested")
    return manifest


@app.get("/ade/documents/{doc_id}/chunks")
async def get_chunks(
    doc_id: str,
    chunk_type: str | None = Query(None, description="filter by chunk type"),
    page: int | None = Query(None, ge=0, description="filter by 0-based page"),
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    def _load() -> list[dict]:
        st = storage.storage()
        key = storage.key_chunks(doc_id)
        if not st.exists(key):
            raise HTTPException(404, f"{doc_id} has not been ingested")
        return st.get_json(key)

    chunks = await run_in_threadpool(_load)
    if chunk_type:
        chunks = [c for c in chunks if c.get("chunk_type") == chunk_type]
    if page is not None:
        chunks = [c for c in chunks if c.get("page") == page]
    return {"doc_id": doc_id, "count": len(chunks), "chunks": chunks[:limit]}


@app.get("/ade/documents/{doc_id}/markdown")
async def get_markdown(doc_id: str) -> Response:
    def _load() -> bytes:
        st = storage.storage()
        key = storage.key_markdown(doc_id)
        if not st.exists(key):
            raise HTTPException(404, f"{doc_id} has not been ingested")
        return st.get_bytes(key)

    md = await run_in_threadpool(_load)
    return Response(content=md, media_type="text/markdown; charset=utf-8")


@app.get("/ade/documents/{doc_id}/pdf")
async def get_pdf(doc_id: str, download: bool = False) -> Response:
    """Stream the original PDF — the byte-identical evidence of record."""
    def _load() -> bytes:
        st = storage.storage()
        key = storage.key_pdf(doc_id)
        if not st.exists(key):
            raise HTTPException(404, f"{doc_id} has not been ingested")
        return st.get_bytes(key)

    pdf = await run_in_threadpool(_load)
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{doc_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
@app.get("/ade/evidence/{doc_id}/{chunk_id}.png")
async def evidence_png(doc_id: str, chunk_id: str, dpi: int = Query(150, ge=96, le=300)) -> Response:
    """The proof image: the source page with the cited region highlighted."""
    try:
        png = await run_in_threadpool(render.render_evidence, doc_id, chunk_id, dpi)
    except render.EvidenceUnavailable as e:
        raise HTTPException(404, str(e)) from e
    except storage.StorageError as e:
        raise HTTPException(502, str(e)) from e
    return Response(
        content=png,
        media_type="image/png",
        # Renders are deterministic for a given (doc, chunk, dpi).
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/ade/page/{doc_id}/{page_no}.png")
async def page_png(doc_id: str, page_no: int, dpi: int = Query(150, ge=96, le=300)) -> Response:
    try:
        png = await run_in_threadpool(render.render_page, doc_id, page_no, dpi)
    except storage.StorageError as e:
        raise HTTPException(404, str(e)) from e
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
