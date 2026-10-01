"""Shared helpers and styles for Eugene route flow guides.

Used by all section files in docs/flow_guide_sections/ and by
generate_route_flow_guides.py. Styles mirror generate_flow_guides.py.
"""
from __future__ import annotations

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Preformatted,
    Table,
    TableStyle,
)


DOCS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
)


ACCENT = HexColor("#0B3D91")
MUTED = HexColor("#555555")
CODE_BG = HexColor("#F4F6F8")
RULE = HexColor("#CFD8DC")

_styles = getSampleStyleSheet()

H_TITLE = ParagraphStyle(
    "H_TITLE", parent=_styles["Title"],
    fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=ACCENT, spaceAfter=6,
)
H_SUB = ParagraphStyle(
    "H_SUB", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=14,
    textColor=MUTED, spaceAfter=18,
)
H1 = ParagraphStyle(
    "H1", parent=_styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=16, leading=20,
    textColor=ACCENT, spaceBefore=14, spaceAfter=8,
)
H2 = ParagraphStyle(
    "H2", parent=_styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    textColor=black, spaceBefore=10, spaceAfter=4,
)
BODY = ParagraphStyle(
    "BODY", parent=_styles["BodyText"],
    fontName="Helvetica", fontSize=10, leading=14,
    alignment=TA_LEFT, spaceAfter=6,
)
BULLET = ParagraphStyle(
    "BULLET", parent=BODY,
    leftIndent=14, bulletIndent=2, spaceAfter=3,
)
CODE = ParagraphStyle(
    "CODE", parent=_styles["Code"],
    fontName="Courier", fontSize=8.5, leading=11,
    backColor=CODE_BG, borderPadding=6,
    leftIndent=0, rightIndent=0, spaceBefore=4, spaceAfter=8,
)
PATH = ParagraphStyle(
    "PATH", parent=BODY,
    fontName="Courier", fontSize=9, leading=12,
    textColor=ACCENT, spaceAfter=4,
)


def p(text, style=BODY):
    return Paragraph(text, style)


def code(text):
    return Preformatted(text.rstrip("\n"), CODE)


def bullets(items):
    return [Paragraph(f"&bull;&nbsp; {it}", BULLET) for it in items]


def rule():
    t = Table([[""]], colWidths=[16 * cm], rowHeights=[0.02 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE)]))
    return t


def c(s):
    """Inline courier wrap."""
    return f"<font face='Courier'>{s}</font>"


# Re-exports for section files
__all__ = [
    "H_TITLE", "H_SUB", "H1", "H2", "BODY", "BULLET", "CODE", "PATH",
    "p", "code", "bullets", "rule", "c",
    "Spacer", "PageBreak",
    "render",
]


def render(story, out_name, title):
    out_path = os.path.join(DOCS_DIR, out_name)
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        title=title, author="Eugene Engineering",
    )
    doc.build(story)
    print(f"wrote {out_path}")
