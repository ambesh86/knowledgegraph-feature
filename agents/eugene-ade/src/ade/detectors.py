"""Visual chunk-type detectors — scan_code, logo, attestation, card.

DocLayout-YOLO's DocStructBench classes cover title / text / table / figure /
caption / formula / abandon. They do NOT cover the four types DPT-2 adds:
`scan_code`, `logo`, `attestation` (signatures, stamps, seals) and `card` (ID
documents). This module supplies them locally, with no vendor API.

Be clear about what each one is, because the confidence values they emit are not
comparable:

  * `scan_code` is REAL DETECTION. OpenCV's QR and barcode detectors either find
    and decode a symbol or they do not, so a hit is a fact, not an estimate.
    Confidence 1.0, and the decoded payload is attached.

  * `logo`, `attestation` and `card` are HEURISTIC CLASSIFIERS over regions the
    layout model already called `figure`. They score geometry and ink statistics
    — position on the page, aspect ratio, stroke density, colourfulness — and
    they are explicitly labelled `heuristic: true` with a sub-1.0 confidence so
    nothing downstream mistakes them for model output. Training a real detector
    would need a labelled corpus we do not have; a transparent heuristic beats an
    unlabelled guess, and beats not detecting them at all.

They only run on figure/image regions, so cost is proportional to the number of
images in a document rather than to page count.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Rendering DPI for the crops these detectors inspect. High enough for a QR
# module to survive, low enough that a page of figures stays cheap.
_CROP_DPI = 200

# --- heuristic thresholds ---------------------------------------------------
# ID-1 cards (driving licences, national IDs) are 85.6 × 54 mm.
_CARD_ASPECT = 85.60 / 53.98          # ≈ 1.586
_CARD_ASPECT_TOL = 0.22
_CARD_MIN_AREA = 0.04                 # ≥4% of the page — a card is never tiny

# Logos sit in the page furniture (header/footer band) and are small.
_LOGO_MAX_AREA = 0.06
_LOGO_TOP_BAND = 0.18
_LOGO_BOTTOM_BAND = 0.88

# Signatures/stamps: sparse dark ink on light ground, wider than tall.
_ATTEST_MAX_INK = 0.35
_ATTEST_MIN_INK = 0.01
_ATTEST_MIN_ASPECT = 1.4


def _crop(page, box: dict[str, float]):
    """Render a normalized region to a BGR array, or None if it isn't usable."""
    try:
        import cv2
        import numpy as np
        import fitz

        pr = page.rect
        rect = fitz.Rect(
            pr.x0 + box["left"] * pr.width,
            pr.y0 + box["top"] * pr.height,
            pr.x0 + box["right"] * pr.width,
            pr.y0 + box["bottom"] * pr.height,
        )
        if rect.width < 8 or rect.height < 8:
            return None
        pix = page.get_pixmap(clip=rect, dpi=_CROP_DPI, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.debug(f"crop failed: {e}")
        return None


def detect_scan_codes(page) -> list[dict[str, Any]]:
    """Find QR codes and barcodes on a page — genuine detection, with payloads.

    Runs over the whole page rather than per-region: a QR code is frequently
    dropped into a margin the layout model labels `abandon`, and it would be
    missed if we only inspected figures.
    """
    out: list[dict[str, Any]] = []
    try:
        import cv2
        import numpy as np

        pix = page.get_pixmap(dpi=_CROP_DPI, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]

        def _norm(pts) -> dict[str, float]:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            return {
                "left": max(0.0, min(1.0, min(xs) / w)),
                "top": max(0.0, min(1.0, min(ys) / h)),
                "right": max(0.0, min(1.0, max(xs) / w)),
                "bottom": max(0.0, min(1.0, max(ys) / h)),
            }

        # QR — multi-detect so a page of codes isn't reduced to one.
        try:
            ok, decoded, points, _ = cv2.QRCodeDetector().detectAndDecodeMulti(bgr)
            if ok and points is not None:
                for text, quad in zip(decoded, points):
                    out.append({
                        "kind": "qr", "payload": str(text or ""),
                        "bbox": _norm(quad), "confidence": 1.0, "heuristic": False,
                    })
        except Exception as e:
            logger.debug(f"QR detection failed: {e}")

        # Barcode — availability varies by OpenCV build, so guard it.
        try:
            if hasattr(cv2, "barcode"):
                ok, decoded, types, corners = cv2.barcode.BarcodeDetector().detectAndDecodeWithType(bgr)
                if ok and corners is not None:
                    for text, btype, quad in zip(decoded, types, corners):
                        out.append({
                            "kind": f"barcode:{btype}".lower(), "payload": str(text or ""),
                            "bbox": _norm(quad), "confidence": 1.0, "heuristic": False,
                        })
        except Exception as e:
            logger.debug(f"barcode detection failed: {e}")

    except Exception as e:
        logger.debug(f"scan-code pass failed: {e}")

    if out:
        logger.info(f"detected {len(out)} scan code(s)")
    return out


def classify_figure(page, box: dict[str, float]) -> dict[str, Any] | None:
    """Refine a `figure` region into logo / card / attestation, if it looks like one.

    Returns None to leave the region as a plain figure — the common case, and the
    right answer when nothing is confidently indicated.
    """
    img = _crop(page, box)
    if img is None:
        return None
    try:
        import cv2
        import numpy as np

        h, w = img.shape[:2]
        area = (box["right"] - box["left"]) * (box["bottom"] - box["top"])
        aspect = (w / h) if h else 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Otsu adapts to scan exposure, so "ink" means dark-relative-to-this-crop
        # rather than dark in absolute terms.
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ink = float(np.count_nonzero(binary)) / max(1, binary.size)
        chans = img.reshape(-1, 3).astype(np.float32)
        colourfulness = float(np.mean(np.std(chans, axis=0))) / 255.0

        # CARD — ID-1 aspect ratio and a substantial share of the page.
        if area >= _CARD_MIN_AREA and abs(aspect - _CARD_ASPECT) <= _CARD_ASPECT_TOL:
            return {
                "chunk_type": "card", "heuristic": True,
                "confidence": round(0.55 + 0.35 * (1 - abs(aspect - _CARD_ASPECT) / _CARD_ASPECT_TOL), 3),
                "signals": {"aspect": round(aspect, 3), "area": round(area, 4)},
            }

        # ATTESTATION — sparse ink, wide, and not colourful: pen or stamp, not art.
        if (
            _ATTEST_MIN_INK <= ink <= _ATTEST_MAX_INK
            and aspect >= _ATTEST_MIN_ASPECT
            and colourfulness < 0.18
        ):
            return {
                "chunk_type": "attestation", "heuristic": True,
                "confidence": round(0.5 + 0.3 * (1 - ink / _ATTEST_MAX_INK), 3),
                "signals": {"ink": round(ink, 4), "aspect": round(aspect, 3)},
            }

        # LOGO — small, colourful, sitting in the header or footer band.
        in_furniture = box["bottom"] <= _LOGO_TOP_BAND or box["top"] >= _LOGO_BOTTOM_BAND
        if area <= _LOGO_MAX_AREA and in_furniture and colourfulness > 0.06:
            return {
                "chunk_type": "logo", "heuristic": True,
                "confidence": round(0.5 + 0.3 * min(1.0, colourfulness / 0.3), 3),
                "signals": {"area": round(area, 4), "colour": round(colourfulness, 3)},
            }
    except Exception as e:
        logger.debug(f"figure classification failed: {e}")
    return None
