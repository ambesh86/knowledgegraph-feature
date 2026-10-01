"""PyMuPDF structural parse — exact text with exact geometry.

This is half of the extraction. It reads the PDF's own content stream, so the text
and coordinates are exact rather than inferred: nothing here is a model guess.
What it CANNOT do is tell you a block is an *abstract* rather than a *paragraph* —
that semantic labelling is `layout.py`'s job, and the two are merged in
`pipeline.py`.

Bounding boxes are normalized to [0,1] with (0,0) at top-left. Normalized boxes
survive re-rendering at any DPI, which is exactly what the evidence viewer needs:
it rasterizes on the fly and must place the highlight correctly at whatever size
the user's screen asks for.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import fitz  # PyMuPDF

from ade import detectors, tables

logger = logging.getLogger(__name__)


# --- Mechanisms M1 + M2 -----------------------------------------------------
# Chunk ids are DERIVED, never random. Re-parsing an unchanged document must
# reproduce byte-identical ids, because the same string is the Neo4j `chunk_id`
# AND the Milvus primary key — there is no join map between the two stores, and a
# join map is exactly the thing that drifts on re-ingestion and silently points a
# citation at the wrong paragraph.
#
# This replaced `uuid.uuid4()`: every re-ingest used to mint new ids and orphan
# every stored evidence link, with nothing in the system noticing.
_ID_LEN = 32


def _element_id(page: int, block_index: int, kind: str) -> str:
    """The parser's native handle for a page element.

    Position-based rather than content-based on purpose: a passage whose wording
    is corrected in a revised PDF is still the same passage in the same place, so
    it should keep its identity.
    """
    return f"p{page}-{kind}{block_index}"


def _chunk_id(doc_id: str, ordinal: int, element_id: str) -> str:
    return hashlib.sha1(
        f"{doc_id}:{ordinal}:{element_id}".encode("utf-8")
    ).hexdigest()[:_ID_LEN]


def _content_hash(text: str) -> str:
    """SHA-256 of verbatim text, so a stored citation can be proven unchanged."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# Fraction of page height treated as header/footer. Running heads and page
# numbers are not evidence and should never be cited as such.
_MARGIN_BAND = 0.08
# A text block overlapping a detected table by more than this is part of the
# table and must not also be emitted as loose text.
_TABLE_OVERLAP = 0.5
# Minimum normalized side length for a box to be considered renderable. ~0.1% of
# a page dimension — below a line of text, above a numerical collapse.
_MIN_BOX_SIDE = 0.001


def _norm_box(rect: tuple[float, float, float, float], pw: float, ph: float) -> dict[str, float]:
    x0, y0, x1, y1 = rect
    pw = pw or 1.0
    ph = ph or 1.0
    return {
        "left": max(0.0, min(1.0, x0 / pw)),
        "top": max(0.0, min(1.0, y0 / ph)),
        "right": max(0.0, min(1.0, x1 / pw)),
        "bottom": max(0.0, min(1.0, y1 / ph)),
    }


def _overlap_fraction(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Fraction of rect `a`'s area covered by rect `b`."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(1e-6, (ax1 - ax0) * (ay1 - ay0))
    return inter / area_a


def _is_renderable(box: dict[str, float]) -> bool:
    """True when a box encloses real area and can therefore be highlighted.

    Rotated text — vertical figure labels, sidebar watermarks — comes back from
    PyMuPDF with coordinates outside the page rect. Normalization clamps those to
    the edge, collapsing the box to zero height or width. Observed on a real
    document: 23 chunks with top == bottom == 1.0, one per rotated trial name.
    A chunk whose box has no area cannot be shown to a user as evidence, so
    emitting it creates a passage that can be retrieved but never proven.
    """
    return (box["right"] - box["left"]) > _MIN_BOX_SIDE and (
        box["bottom"] - box["top"]
    ) > _MIN_BOX_SIDE


def _classify(box: dict[str, float]) -> str:
    if box["bottom"] <= _MARGIN_BAND or box["top"] >= (1.0 - _MARGIN_BAND):
        return "marginalia"
    return "text"


def parse_pdf(
    pdf_bytes: bytes,
    doc_id: str = "doc",
    *,
    cell_level_tables: bool = True,
    detect_visuals: bool = True,
) -> dict[str, Any]:
    """Parse PDF bytes into markdown, chunks, page index and grounding index.

    `doc_id` participates in every chunk id (M2), so it must be the same stable
    document identifier used everywhere else in the system.
    """
    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        chunks: list[dict[str, Any]] = []
        grounding: dict[str, Any] = {}
        md_pages: list[str] = []
        pages: list[dict[str, Any]] = []
        order = 0
        chars_total = 0
        # Running character offset into the assembled markdown. Every chunk
        # records the span it occupies, which is what lets an extracted fact
        # point back at the exact text it came from -- the mechanism ADE uses
        # for evidence links -- without re-searching the document later.
        md_cursor = 0

        def _span(text: str) -> dict[str, int]:
            """Reserve the markdown span this text will occupy."""
            nonlocal md_cursor
            start = md_cursor
            md_cursor += len(text) + 2   # +2 for the "\n\n" join
            return {"start": start, "end": start + len(text)}

        for pno in range(doc.page_count):
            page = doc[pno]
            pw = float(page.rect.width) or 1.0
            ph = float(page.rect.height) or 1.0
            page_md: list[str] = [f"## Page {pno + 1}"]
            ids_on_page: list[str] = []

            # --- Tables first, so overlapping text blocks can be suppressed ---
            table_rects: list[tuple[float, ...]] = []
            try:
                found = page.find_tables()
                tables = list(getattr(found, "tables", []) or [])
            except Exception as e:
                logger.debug(f"table detection failed on page {pno}: {e}")
                tables = []

            for tab in tables:
                try:
                    bb = tab.bbox
                    rect = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
                    md = (tab.to_markdown() or "").strip()
                except Exception:
                    continue
                if not md:
                    continue
                table_rects.append(rect)
                eid = _element_id(pno, len(table_rects) - 1, "tbl")
                cid = _chunk_id(doc_id, order, eid)
                box = _norm_box(rect, pw, ph)
                chunks.append({
                    "chunk_id": cid, "chunk_type": "table", "page": pno,
                    "page_start": pno, "page_end": pno,
                    "bbox": box, "text": md, "order": order,
                    "element_id": eid, "content_hash": _content_hash(md),
                    "markdown_range": _span(md),
                    # Structural extraction — exact cell geometry from the PDF,
                    # not a model prediction, so confidence is 1.0 by definition.
                    "parser_confidence": 1.0,
                })
                grounding[cid] = {"page": pno, "box": box, "type": "chunkTable"}
                ids_on_page.append(cid)
                page_md.append(md)
                order += 1
                chars_total += len(md)

            # --- Text and image blocks, in reading order ---
            blocks = list(page.get_text("blocks") or [])
            # Reading order: top-to-bottom, then left-to-right. Rounded so that
            # blocks sitting on the same visual line don't get split by sub-pixel
            # y-differences.
            blocks.sort(key=lambda b: (round(float(b[1]), 1), round(float(b[0]), 1)))
            for b in blocks:
                x0, y0, x1, y1, text, btype = b[0], b[1], b[2], b[3], b[4], b[6]
                rect = (float(x0), float(y0), float(x1), float(y1))
                if any(_overlap_fraction(rect, tr) > _TABLE_OVERLAP for tr in table_rects):
                    continue

                box = _norm_box(rect, pw, ph)
                if not _is_renderable(box):
                    continue
                eid = _element_id(pno, int(b[5]), "img" if btype == 1 else "blk")
                cid = _chunk_id(doc_id, order, eid)

                if btype == 1:  # image block
                    fig_type, fig_extra = "figure", {}
                    if detect_visuals:
                        # Refine figure → logo / card / attestation where the
                        # geometry and ink statistics indicate one.
                        refined = detectors.classify_figure(page, box)
                        if refined:
                            fig_type = refined["chunk_type"]
                            fig_extra = {
                                "visual_confidence": refined["confidence"],
                                "heuristic": refined["heuristic"],
                                "visual_signals": refined.get("signals", {}),
                            }
                    chunks.append({
                        "chunk_id": cid, "chunk_type": fig_type, "page": pno,
                        "page_start": pno, "page_end": pno,
                        "bbox": box, "text": f"*[{fig_type}]*", "order": order,
                        "element_id": eid,
                        "content_hash": _content_hash(f"*[{fig_type}]*"),
                        "markdown_range": _span(f"*[{fig_type}]*"),
                        "parser_confidence": 1.0, **fig_extra,
                    })
                    grounding[cid] = {"page": pno, "box": box, "type": "chunkFigure"}
                    ids_on_page.append(cid)
                    order += 1
                    continue

                cleaned = " ".join(str(text or "").split())
                if not cleaned:
                    continue
                chunks.append({
                    "chunk_id": cid, "chunk_type": _classify(box), "page": pno,
                    "page_start": pno, "page_end": pno,
                    "bbox": box, "text": cleaned, "order": order,
                    "element_id": eid, "content_hash": _content_hash(cleaned),
                    "markdown_range": _span(cleaned),
                    "parser_confidence": 1.0,
                })
                grounding[cid] = {"page": pno, "box": box, "type": "chunkText"}
                ids_on_page.append(cid)
                page_md.append(cleaned)
                order += 1
                chars_total += len(cleaned)

            # --- scan codes (QR / barcode) — real detection, page-wide -----
            # Run over the whole page rather than per-region: codes are commonly
            # dropped into margins the layout model calls `abandon`, and would be
            # missed entirely if only figures were inspected.
            if detect_visuals:
                for i, code in enumerate(detectors.detect_scan_codes(page)):
                    eid = _element_id(pno, i, "code")
                    cid = _chunk_id(doc_id, order, eid)
                    payload = code.get("payload") or ""
                    txt = f"*[{code['kind']}]* {payload}".strip()
                    chunks.append({
                        "chunk_id": cid, "chunk_type": "scan_code", "page": pno,
                        "page_start": pno, "page_end": pno,
                        "bbox": code["bbox"], "text": txt, "order": order,
                        "element_id": eid, "content_hash": _content_hash(txt),
                        "markdown_range": _span(txt),
                        "parser_confidence": code["confidence"],
                        "heuristic": False,
                        "scan_code_kind": code["kind"],
                        "scan_code_payload": payload,
                    })
                    grounding[cid] = {"page": pno, "box": code["bbox"], "type": "chunkScanCode"}
                    ids_on_page.append(cid)
                    page_md.append(txt)
                    order += 1

            pages.append({
                "page": pno,
                "width": pw,
                "height": ph,
                "chunk_ids": ids_on_page,
            })
            md_pages.append("\n\n".join(page_md))

        return {
            "markdown": "\n\n".join(md_pages).strip(),
            "chunks": chunks,
            "pages": pages,
            "grounding": grounding,
            "page_count": doc.page_count,
            # A PDF with essentially no extractable characters is a scan. We flag
            # it rather than silently returning an empty parse.
            "text_layer": chars_total > 50,
        }
    finally:
        doc.close()
