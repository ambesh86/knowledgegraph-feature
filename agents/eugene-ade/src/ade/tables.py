"""Cell-level table grounding — reconstructing grid geometry from word positions.

Why this exists: a table chunk with one bounding box around the whole table is
weak evidence. A claim like "injection-site reactions had OR 30.94" highlights a
20-row table and leaves the reader to find the row themselves. Cell-level
grounding highlights *that cell*.

Why it is reconstructed rather than read: PyMuPDF's `find_tables()` returns **0
tables** on the academic PDFs in this corpus — it relies on ruling lines, and
journal tables are typically borderless. Measured on page 10 of a real
meta-analysis, `find_tables()` found nothing while the region genuinely contained
199 positioned words. So the table chunks we do have come from the layout model's
region labels, and the grid inside them has to be derived.

The method mirrors what DPT-2 describes doing: establish the table's geometry
first — where rows and columns begin and end — then attribute each piece of text
to a cell and give that cell its own box. Concretely:

  1. Take every word inside the table region, with its rectangle.
  2. Cluster words into ROWS by vertical overlap (not exact y, because baselines
     wobble and superscripts sit high).
  3. Derive COLUMN boundaries from the x-projection of word starts across all
     rows — a column edge is a vertical gap that persists down the table.
  4. Assign each word to (row, column); a cell's box is the union of its words.

This is deterministic and needs no model weights, which matters because the whole
point of this build is that there is no vendor API key.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Two words belong to the same row if their vertical spans overlap by at least
# this fraction of the shorter one. Tolerant enough for sub/superscripts, tight
# enough not to merge adjacent rows in a dense table.
_ROW_OVERLAP = 0.35
# A horizontal gap wider than this multiple of the median character width is
# treated as a column separator rather than a word space.
_COL_GAP_FACTOR = 2.2
# Below this many words a "table" region is almost certainly a caption or a
# mis-labelled paragraph; emitting a fake grid for it would be worse than
# leaving it as a single chunk.
_MIN_WORDS = 12


def _v_overlap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Fraction of the shorter vertical span that the two words share."""
    top, bot = max(a[1], b[1]), min(a[3], b[3])
    if bot <= top:
        return 0.0
    return (bot - top) / max(1e-6, min(a[3] - a[1], b[3] - b[1]))


def _group_rows(words: list[tuple]) -> list[list[tuple]]:
    """Cluster words into visual rows by vertical overlap."""
    rows: list[list[tuple]] = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        placed = False
        for row in rows:
            # Compare against the row's most recent word: rows are built left to
            # right, and the last word carries the row's current vertical band.
            if _v_overlap(w, row[-1]) >= _ROW_OVERLAP:
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])
    for row in rows:
        row.sort(key=lambda w: w[0])
    return rows


def _column_edges(rows: list[list[tuple]]) -> list[float]:
    """Derive column start positions from gaps that recur down the table.

    A single row's gaps are unreliable — one row may simply have a short value.
    A gap that appears at roughly the same x in many rows is a real column
    boundary.
    """
    widths = [
        (w[2] - w[0]) / max(1, len(w[4]))
        for row in rows for w in row if w[4]
    ]
    char_w = sorted(widths)[len(widths) // 2] if widths else 4.0
    threshold = char_w * _COL_GAP_FACTOR

    starts: list[float] = []
    for row in rows:
        starts.append(row[0][0])
        for prev, cur in zip(row, row[1:]):
            if (cur[0] - prev[2]) > threshold:
                starts.append(cur[0])

    if not starts:
        return []
    # Merge start positions that are within one character width of each other —
    # the same column, jittered by proportional fonts.
    starts.sort()
    edges = [starts[0]]
    for s in starts[1:]:
        if s - edges[-1] > char_w * 1.5:
            edges.append(s)
    return edges


def extract_cells(
    page, region: dict[str, float], max_cells: int = 400
) -> list[dict[str, Any]]:
    """Return per-cell records for a table region.

    `region` is a normalized 0–1 box. Each returned cell carries its own
    normalized box, so it can be highlighted independently of the table.
    """
    pw, ph = float(page.rect.width) or 1.0, float(page.rect.height) or 1.0
    x0, y0 = region["left"] * pw, region["top"] * ph
    x1, y1 = region["right"] * pw, region["bottom"] * ph

    words = [
        w for w in (page.get_text("words") or [])
        # Small tolerance: layout boxes are predicted, so a word may sit a
        # fraction outside the region it clearly belongs to.
        if w[0] >= x0 - 2 and w[2] <= x1 + 2 and w[1] >= y0 - 2 and w[3] <= y1 + 2
        and str(w[4]).strip()
    ]
    if len(words) < _MIN_WORDS:
        logger.debug(f"table region has only {len(words)} words; skipping grid")
        return []

    rows = _group_rows(words)
    edges = _column_edges(rows)
    if len(rows) < 2 or len(edges) < 2:
        logger.debug(f"grid too degenerate: {len(rows)} rows, {len(edges)} cols")
        return []

    cells: list[dict[str, Any]] = []
    for r_idx, row in enumerate(rows):
        buckets: dict[int, list[tuple]] = {}
        for w in row:
            # Rightmost edge at or left of the word's start = its column.
            c_idx = max((i for i, e in enumerate(edges) if w[0] >= e - 1.0), default=0)
            buckets.setdefault(c_idx, []).append(w)
        for c_idx, ws in sorted(buckets.items()):
            text = " ".join(w[4] for w in ws).strip()
            if not text:
                continue
            cells.append({
                "row": r_idx,
                "col": c_idx,
                "text": text,
                "bbox": {
                    "left": max(0.0, min(1.0, min(w[0] for w in ws) / pw)),
                    "top": max(0.0, min(1.0, min(w[1] for w in ws) / ph)),
                    "right": max(0.0, min(1.0, max(w[2] for w in ws) / pw)),
                    "bottom": max(0.0, min(1.0, max(w[3] for w in ws) / ph)),
                },
            })
            if len(cells) >= max_cells:
                logger.warning(f"table hit {max_cells}-cell cap; truncating")
                return cells

    logger.debug(f"reconstructed {len(rows)}x{len(edges)} grid → {len(cells)} cells")
    return cells


def to_markdown(cells: list[dict[str, Any]]) -> str:
    """Render reconstructed cells as a markdown table.

    Used for the parent table chunk's text so the passage still reads naturally
    when an LLM sees it, while the cells carry the fine-grained geometry.
    """
    if not cells:
        return ""
    n_cols = max(c["col"] for c in cells) + 1
    grid: dict[int, dict[int, str]] = {}
    for c in cells:
        grid.setdefault(c["row"], {})[c["col"]] = c["text"]

    lines = []
    for r_idx in sorted(grid):
        row = [grid[r_idx].get(i, "") for i in range(n_cols)]
        lines.append("| " + " | ".join(row) + " |")
        if r_idx == min(grid):  # header separator after the first row
            lines.append("|" + "|".join([" --- "] * n_cols) + "|")
    return "\n".join(lines)
