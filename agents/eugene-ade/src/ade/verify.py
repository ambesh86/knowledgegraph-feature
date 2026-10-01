"""Extraction quality verification — the "agentic" checking loop.

ADE's agentic behaviour is not an LLM doing the extraction; it is an orchestrator
that runs extraction, *checks the result against quality thresholds*, and retries
differently when the check fails. This module is that check.

Four measures, each catching a distinct failure the others miss:

  * **text recovery** — characters captured in chunks ÷ characters PyMuPDF can
    see on the page. Catches the worst silent failure: layout regions that miss
    whole columns, leaving text in the PDF but absent from the graph.
  * **area coverage** — page area inside chunk boxes. Catches figures and tables
    dropped entirely, which text recovery cannot see because they have no text.
  * **geometry sanity** — degenerate, inverted or out-of-range boxes. A box that
    is wrong renders evidence pointing at the wrong part of the page, which is
    worse than no evidence at all.
  * **duplication** — the same text emitted under several chunk ids, which
    inflates retrieval and double-counts in fusion.

A failing document is retried with different layout settings rather than silently
accepted. The verdict is recorded on the manifest either way, so a poor
extraction is visible instead of quietly degrading every answer built on it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# A good digital PDF recovers ~0.9+. The floor is deliberately below that:
# marginalia and figure-only pages legitimately depress the ratio, and failing
# them would cause pointless retries.
MIN_TEXT_RECOVERY = 0.70
MIN_AREA_COVERAGE = 0.10
MAX_BAD_GEOMETRY = 0.02
MAX_DUPLICATION = 0.25
# Text shorter than this is a label or fragment; repetition of it is document
# structure, not a duplicated extraction.
_DUP_MIN_CHARS = 40
# Mirrors indexer._SKIP_TYPES plus table cells: chunk types that never become
# retrievable passages, and so cannot pollute retrieval by repeating.
_NON_INDEXED = {"table_cell", "marginalia", "figure"}


@dataclass
class Verdict:
    passed: bool
    score: float
    metrics: dict[str, float] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    attempt: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "metrics": {k: round(v, 4) for k, v in self.metrics.items()},
            "failures": self.failures,
            "attempt": self.attempt,
        }


def _page_text_lengths(pdf_bytes: bytes) -> list[int]:
    import fitz

    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [len("".join(str(doc[i].get_text("text") or "").split())) for i in range(doc.page_count)]
    finally:
        doc.close()


def verify(pdf_bytes: bytes, chunks: list[dict[str, Any]], attempt: int = 1) -> Verdict:
    """Score an extraction and decide whether it is good enough to keep."""
    metrics: dict[str, float] = {}
    failures: list[str] = []

    page_chars = _page_text_lengths(pdf_bytes)
    total_chars = sum(page_chars) or 1

    captured = sum(len("".join(str(c.get("text", "")).split())) for c in chunks)
    # Can exceed 1.0 when a table is emitted both as a parent and as cells; the
    # clamp keeps the score meaningful rather than rewarding duplication.
    metrics["text_recovery"] = min(1.0, captured / total_chars)

    # Area coverage, summed per page then averaged. Overlapping boxes are not
    # deduplicated — this is a floor check for "did we miss whole regions", not
    # a precise measure of page occupancy.
    per_page: dict[int, float] = {}
    bad_geometry = 0
    for c in chunks:
        b = c.get("bbox") or {}
        try:
            l, t, r, bm = (float(b["left"]), float(b["top"]),
                           float(b["right"]), float(b["bottom"]))
        except (KeyError, TypeError, ValueError):
            bad_geometry += 1
            continue
        if not (0.0 <= l < r <= 1.0 and 0.0 <= t < bm <= 1.0):
            bad_geometry += 1
            continue
        per_page[c.get("page", 0)] = per_page.get(c.get("page", 0), 0.0) + (r - l) * (bm - t)

    n_pages = max(1, len(page_chars))
    metrics["area_coverage"] = min(1.0, sum(per_page.values()) / n_pages)
    metrics["bad_geometry"] = bad_geometry / max(1, len(chunks))

    # Duplication counts only SUBSTANTIVE repeated text.
    #
    # Two exclusions, both learned from a correctly-extracted document failing:
    #   * table cells legitimately repeat values — a column of study counts holds
    #     "7" many times, at different coordinates;
    #   * short repeated labels are document structure, not extraction error. In
    #     a real meta-analysis "Intervention group:" appears 60 times and
    #     "Control group:" 23 times, because each study row in the characteristics
    #     table carries them. Counting those put duplication at 28.6% and burned
    #     every retry attempt on a problem that did not exist.
    #
    # Identical text ABOVE the length floor is what actually indicates the same
    # passage extracted twice.
    # Measure only what will actually be INDEXED. The indexer drops marginalia
    # and figures, so counting them here flagged documents whose furniture had
    # already been correctly identified and demoted — the metric disagreed with
    # the thing it was meant to describe.
    texts = [
        str(c.get("text", "")).strip()
        for c in chunks
        if c.get("chunk_type") not in _NON_INDEXED
        and len(str(c.get("text", "")).strip()) >= _DUP_MIN_CHARS
    ]
    metrics["duplication"] = 1 - (len(set(texts)) / max(1, len(texts)))

    if metrics["text_recovery"] < MIN_TEXT_RECOVERY:
        failures.append(
            f"text_recovery {metrics['text_recovery']:.2f} < {MIN_TEXT_RECOVERY}"
        )
    if metrics["area_coverage"] < MIN_AREA_COVERAGE:
        failures.append(
            f"area_coverage {metrics['area_coverage']:.2f} < {MIN_AREA_COVERAGE}"
        )
    if metrics["bad_geometry"] > MAX_BAD_GEOMETRY:
        failures.append(
            f"bad_geometry {metrics['bad_geometry']:.2%} > {MAX_BAD_GEOMETRY:.0%}"
        )
    if metrics["duplication"] > MAX_DUPLICATION:
        failures.append(
            f"duplication {metrics['duplication']:.2%} > {MAX_DUPLICATION:.0%}"
        )

    # Weighted so recovery dominates: a document missing half its text is broken
    # even if every box it did emit is geometrically perfect.
    score = (
        0.45 * metrics["text_recovery"]
        + 0.25 * min(1.0, metrics["area_coverage"] / MIN_AREA_COVERAGE)
        + 0.15 * (1 - min(1.0, metrics["bad_geometry"] / max(MAX_BAD_GEOMETRY, 1e-6)))
        + 0.15 * (1 - min(1.0, metrics["duplication"] / max(MAX_DUPLICATION, 1e-6)))
    )

    verdict = Verdict(
        passed=not failures, score=score, metrics=metrics,
        failures=failures, attempt=attempt,
    )
    logger.info(
        f"verification attempt {attempt}: "
        f"{'PASS' if verdict.passed else 'FAIL'} score={score:.3f} "
        f"recovery={metrics['text_recovery']:.2f} coverage={metrics['area_coverage']:.2f}"
        + (f" failures={failures}" if failures else "")
    )
    return verdict


def retry_settings(attempt: int) -> dict[str, Any]:
    """Parameters for the next attempt after a failed verification.

    Lowering the layout-detector confidence admits regions it was unsure about —
    the usual cause of a low recovery score is a column the model declined to
    call text. Disabling layout entirely on the last attempt falls back to pure
    structural parsing, which recovers text even when the model is unhelpful.
    """
    return {
        2: {"layout_conf": 0.15, "reason": "lower layout confidence to admit missed regions"},
        3: {"layout_enabled": False, "reason": "structural-only fallback"},
    }.get(attempt, {})
