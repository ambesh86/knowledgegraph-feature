"""DocLayout-YOLO semantic layout detection — the deep-learning half.

`parser.py` gives exact text and exact geometry but no semantics: every paragraph
looks the same to it. This module runs a document-layout object detector over a
rasterized page and returns labelled regions (title, plain text, abstract, table,
figure, caption, formula) — semantics with no text.

Neither half is sufficient alone, so `merge()` joins them: each PyMuPDF chunk
inherits the label of the detected region it overlaps most (by IoU). The result is
exact text + exact coordinates + a real semantic type, which is what makes a
citation like "Table 2, page 7" trustworthy rather than a guess.

Degradation is deliberate: if the model or its weights cannot be loaded, we log
and return chunks untouched. A missing optional model must never take document
extraction offline — the structural parse alone is still useful.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ID = os.environ.get("ADE_LAYOUT_REPO", "juliozhao/DocLayout-YOLO-DocStructBench")
_WEIGHTS = os.environ.get(
    "ADE_LAYOUT_WEIGHTS", "doclayout_yolo_docstructbench_imgsz1024.pt"
)
_IMGSZ = int(os.environ.get("ADE_LAYOUT_IMGSZ", "1024"))
_CONF = float(os.environ.get("ADE_LAYOUT_CONF", "0.25"))
_ENABLED = os.environ.get("ADE_LAYOUT_ENABLED", "true").lower() != "false"
# Below this IoU a detected region is not really describing the chunk, and
# adopting its label would be worse than keeping the structural default.
_MIN_IOU = float(os.environ.get("ADE_LAYOUT_MIN_IOU", "0.15"))

# DocStructBench class names → our chunk vocabulary.
_LABEL_MAP = {
    "title": "title",
    "plain text": "text",
    "abandon": "marginalia",  # headers/footers/page numbers
    "figure": "figure",
    "figure_caption": "caption",
    "table": "table",
    "table_caption": "caption",
    "table_footnote": "footnote",
    "isolate_formula": "formula",
    "formula_caption": "caption",
}

_model = None
_model_lock = threading.Lock()
_load_failed = False


def available() -> bool:
    return _ENABLED and not _load_failed


def _get_model():
    """Lazy-load and cache the detector. Thread-safe; failure is sticky."""
    global _model, _load_failed
    if _model is not None or _load_failed or not _ENABLED:
        return _model
    with _model_lock:
        if _model is not None or _load_failed:
            return _model
        try:
            import torch
            from doclayout_yolo import YOLOv10
            from huggingface_hub import hf_hub_download

            # Honour the thread cap explicitly: the OMP_NUM_THREADS env var alone
            # is not always respected once torch has initialised, and an
            # unbounded inference saturates every core on the host.
            threads = int(os.environ.get("TORCH_NUM_THREADS", "0"))
            if threads > 0:
                torch.set_num_threads(threads)
                logger.info(f"torch intra-op threads capped at {threads}")

            path = hf_hub_download(repo_id=_REPO_ID, filename=_WEIGHTS)
            _model = YOLOv10(path)
            logger.info(f"DocLayout-YOLO loaded from {path}")
        except Exception as e:
            _load_failed = True
            logger.warning(
                f"DocLayout-YOLO unavailable ({e}); falling back to structural labels only"
            )
    return _model


def warm() -> bool:
    """Load the model at startup so the first user request isn't the one that pays."""
    return _get_model() is not None


def detect_page(page, dpi: int = 120) -> list[dict[str, Any]]:
    """Detect labelled layout regions on one PyMuPDF page.

    Returns [{label, bbox(normalized), confidence}]; empty when unavailable.
    """
    model = _get_model()
    if model is None:
        return []
    try:
        import cv2
        import numpy as np

        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        results = model.predict(img, imgsz=_IMGSZ, conf=_CONF, verbose=False)
        if not results:
            return []
        res = results[0]
        names = getattr(res, "names", {}) or getattr(model, "names", {}) or {}
        out: list[dict[str, Any]] = []
        boxes = getattr(res, "boxes", None)
        if boxes is None:
            return []
        for b in boxes:
            xyxy = b.xyxy[0].tolist()
            cls_id = int(b.cls[0].item())
            conf = float(b.conf[0].item())
            raw_label = str(names.get(cls_id, cls_id))
            out.append({
                "label": _LABEL_MAP.get(raw_label, raw_label),
                "raw_label": raw_label,
                "bbox": {
                    "left": max(0.0, min(1.0, xyxy[0] / pix.width)),
                    "top": max(0.0, min(1.0, xyxy[1] / pix.height)),
                    "right": max(0.0, min(1.0, xyxy[2] / pix.width)),
                    "bottom": max(0.0, min(1.0, xyxy[3] / pix.height)),
                },
                "confidence": round(conf, 4),
            })
        return out
    except Exception as e:
        logger.warning(f"layout detection failed on page: {e}")
        return []


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    ix0, iy0 = max(a["left"], b["left"]), max(a["top"], b["top"])
    ix1, iy1 = min(a["right"], b["right"]), min(a["bottom"], b["bottom"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(1e-9, (a["right"] - a["left"]) * (a["bottom"] - a["top"]))
    area_b = max(1e-9, (b["right"] - b["left"]) * (b["bottom"] - b["top"]))
    return inter / (area_a + area_b - inter)


def merge(chunks: list[dict[str, Any]], regions_by_page: dict[int, list[dict]]) -> list[dict]:
    """Assign each chunk the label of its best-overlapping detected region.

    Mutates and returns `chunks`, adding `layout_label`/`layout_confidence` and
    upgrading `chunk_type` when the detector is confident. Tables found
    structurally are left alone — exact table geometry beats a detected box.
    """
    labelled = 0
    for ch in chunks:
        regions = regions_by_page.get(ch["page"]) or []
        if not regions:
            continue
        best, best_iou = None, 0.0
        for r in regions:
            score = _iou(ch["bbox"], r["bbox"])
            if score > best_iou:
                best, best_iou = r, score
        if best is None or best_iou < _MIN_IOU:
            continue
        ch["layout_label"] = best["label"]
        ch["layout_confidence"] = best["confidence"]
        ch["layout_iou"] = round(best_iou, 4)
        # `table` from find_tables() carries real cell geometry — never downgrade it.
        if ch["chunk_type"] != "table":
            ch["chunk_type"] = best["label"]
        labelled += 1
    logger.info(f"layout merge: labelled {labelled}/{len(chunks)} chunks")
    return chunks
