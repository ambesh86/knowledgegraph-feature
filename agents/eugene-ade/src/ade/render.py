"""On-the-fly evidence rendering — the "100% proof" surface.

Given a chunk id, produce a PNG of the page it came from with that exact region
highlighted. The point is that the user is never asked to take the answer on
trust: they see the original document, at the original coordinates, with the cited
passage outlined.

Rendering is done on demand rather than pre-generated at ingest, because a
document has hundreds of chunks and only a handful are ever cited. Renders are
cached in S3 afterwards so the second view is a straight object fetch.
"""
from __future__ import annotations

import logging
from typing import Any

import fitz

from ade import storage

logger = logging.getLogger(__name__)

# Matches the highlight styling of the reference evidence viewer.
_STROKE = (0.38, 0.67, 0.02)
_FILL = (0.66, 0.85, 0.29)
_OPACITY = 0.38
_DPI_MIN, _DPI_MAX = 96, 300


class EvidenceUnavailable(RuntimeError):
    """The requested chunk cannot be located or rendered."""


def _rect_for(page, box: dict[str, float]) -> fitz.Rect:
    """Map a normalized 0..1 box onto this page's coordinate rect.

    Normalized boxes are what make DPI-independent rendering possible: the same
    stored geometry is correct whether we rasterize at 96 or 300 dpi.
    """
    pr = page.rect
    return fitz.Rect(
        pr.x0 + float(box["left"]) * pr.width,
        pr.y0 + float(box["top"]) * pr.height,
        pr.x0 + float(box["right"]) * pr.width,
        pr.y0 + float(box["bottom"]) * pr.height,
    )


def render_evidence(doc_id: str, chunk_id: str, dpi: int = 150) -> bytes:
    """Return PNG bytes of the chunk's page with the chunk highlighted."""
    dpi = max(_DPI_MIN, min(_DPI_MAX, int(dpi)))
    st = storage.storage()

    cache_key = storage.key_render(doc_id, chunk_id, dpi)
    if st.exists(cache_key):
        return st.get_bytes(cache_key)

    grounding_key = storage.key_grounding(doc_id)
    if not st.exists(grounding_key):
        raise EvidenceUnavailable(f"{doc_id} has not been ingested")
    grounding: dict[str, Any] = st.get_json(grounding_key)

    entry = grounding.get(chunk_id)
    if not isinstance(entry, dict) or not isinstance(entry.get("box"), dict):
        raise EvidenceUnavailable(f"no grounding for chunk {chunk_id} in {doc_id}")

    pdf_bytes = st.get_bytes(storage.key_pdf(doc_id))
    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.page_count <= 0:
            raise EvidenceUnavailable(f"{doc_id} PDF has no pages")
        pno = max(0, min(doc.page_count - 1, int(entry.get("page", 0))))
        page = doc[pno]

        annot = page.add_rect_annot(_rect_for(page, entry["box"]))
        annot.set_colors(stroke=_STROKE, fill=_FILL)
        annot.set_border(width=max(1.5, page.rect.width * 0.0035))
        annot.set_opacity(_OPACITY)
        annot.update()

        png = page.get_pixmap(dpi=dpi, alpha=False).tobytes("png")
    finally:
        doc.close()

    try:
        st.put_bytes(cache_key, png, "image/png")
    except Exception as e:  # caching is an optimization, never a hard dependency
        logger.warning(f"could not cache render {cache_key}: {e}")
    return png


def render_page(doc_id: str, page_no: int, dpi: int = 150) -> bytes:
    """Plain page render with no highlight — used for page-level browsing."""
    dpi = max(_DPI_MIN, min(_DPI_MAX, int(dpi)))
    st = storage.storage()
    pdf_bytes = st.get_bytes(storage.key_pdf(doc_id))
    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pno = max(0, min(doc.page_count - 1, int(page_no)))
        return doc[pno].get_pixmap(dpi=dpi, alpha=False).tobytes("png")
    finally:
        doc.close()
