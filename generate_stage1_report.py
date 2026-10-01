"""
Eugene Platform - Stage 1 Assessment & Audit Report Generator
Generates a professional, colorful PDF report using ReportLab
"""

import io
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
C_DEEP_BLUE   = colors.HexColor("#1B3A6B")
C_STEEL_BLUE  = colors.HexColor("#2E6DA4")
C_TEAL        = colors.HexColor("#00897B")
C_TEAL_LIGHT  = colors.HexColor("#E0F2F1")
C_ORANGE      = colors.HexColor("#E65100")
C_ORANGE_LIGHT= colors.HexColor("#FFF3E0")
C_PURPLE      = colors.HexColor("#4A148C")
C_PURPLE_LIGHT= colors.HexColor("#F3E5F5")
C_RED         = colors.HexColor("#B71C1C")
C_RED_LIGHT   = colors.HexColor("#FFEBEE")
C_GREEN       = colors.HexColor("#1B5E20")
C_GREEN_LIGHT = colors.HexColor("#E8F5E9")
C_YELLOW_LIGHT= colors.HexColor("#FFFDE7")
C_GOLD        = colors.HexColor("#F57F17")
C_BLUE_PALE   = colors.HexColor("#E3F2FD")
C_GRAY_LIGHT  = colors.HexColor("#F5F5F5")
C_GRAY_MID    = colors.HexColor("#9E9E9E")
C_WHITE       = colors.white
C_BLACK       = colors.black

W, H = A4

OUTPUT_PATH = "docs/EUGENE_STAGE1_ASSESSMENT_REPORT.pdf"

# ─────────────────────────────────────────────────────────────────────────────
# PAGE TEMPLATE (header / footer)
# ─────────────────────────────────────────────────────────────────────────────
def on_page(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = A4

    # Header bar
    canvas_obj.setFillColor(C_DEEP_BLUE)
    canvas_obj.rect(0, h - 1.2*cm, w, 1.2*cm, fill=1, stroke=0)
    canvas_obj.setFillColor(C_WHITE)
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.drawString(1.5*cm, h - 0.8*cm, "EUGENE PLATFORM  |  STAGE 1 ASSESSMENT & AUDIT REPORT")
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawRightString(w - 1.5*cm, h - 0.8*cm, "CONFIDENTIAL — CSL BEHRING")

    # Footer bar
    canvas_obj.setFillColor(C_DEEP_BLUE)
    canvas_obj.rect(0, 0, w, 0.9*cm, fill=1, stroke=0)
    canvas_obj.setFillColor(C_WHITE)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawString(1.5*cm, 0.3*cm, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    canvas_obj.drawCentredString(w/2, 0.3*cm, "Eugene Knowledge Graph — Agentic AI Platform")
    canvas_obj.drawRightString(w - 1.5*cm, 0.3*cm, f"Page {doc.page}")

    canvas_obj.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=4, textColor=C_BLACK,
            fontName="Helvetica"),

        "body_justify": ParagraphStyle("body_justify", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=4, alignment=TA_JUSTIFY,
            textColor=C_BLACK, fontName="Helvetica"),

        "h1": ParagraphStyle("h1", parent=base["Heading1"],
            fontSize=18, leading=22, spaceBefore=14, spaceAfter=8,
            textColor=C_WHITE, fontName="Helvetica-Bold"),

        "h2": ParagraphStyle("h2", parent=base["Heading2"],
            fontSize=13, leading=17, spaceBefore=12, spaceAfter=6,
            textColor=C_DEEP_BLUE, fontName="Helvetica-Bold"),

        "h3": ParagraphStyle("h3", parent=base["Heading3"],
            fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=4,
            textColor=C_STEEL_BLUE, fontName="Helvetica-Bold"),

        "h4": ParagraphStyle("h4", parent=base["Heading4"],
            fontSize=9.5, leading=13, spaceBefore=6, spaceAfter=3,
            textColor=C_TEAL, fontName="Helvetica-Bold"),

        "code": ParagraphStyle("code", parent=base["Code"],
            fontSize=7.5, leading=11, fontName="Courier",
            textColor=C_DEEP_BLUE, backColor=C_BLUE_PALE,
            leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4,
            borderPadding=4),

        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
            fontSize=9, leading=13, spaceAfter=2,
            leftIndent=14, firstLineIndent=-8,
            textColor=C_BLACK, fontName="Helvetica"),

        "caption": ParagraphStyle("caption", parent=base["Normal"],
            fontSize=8, leading=11, spaceAfter=4,
            alignment=TA_CENTER, textColor=C_GRAY_MID,
            fontName="Helvetica-Oblique"),

        "finding_title": ParagraphStyle("finding_title", parent=base["Normal"],
            fontSize=9.5, leading=13, fontName="Helvetica-Bold",
            textColor=C_WHITE),

        "finding_body": ParagraphStyle("finding_body", parent=base["Normal"],
            fontSize=8.5, leading=12, fontName="Helvetica",
            textColor=C_BLACK),

        "cover_title": ParagraphStyle("cover_title", parent=base["Normal"],
            fontSize=28, leading=34, fontName="Helvetica-Bold",
            textColor=C_WHITE, alignment=TA_CENTER),

        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"],
            fontSize=14, leading=18, fontName="Helvetica",
            textColor=C_BLUE_PALE, alignment=TA_CENTER),

        "cover_meta": ParagraphStyle("cover_meta", parent=base["Normal"],
            fontSize=10, leading=14, fontName="Helvetica",
            textColor=C_BLUE_PALE, alignment=TA_CENTER),

        "tag_critical": ParagraphStyle("tag_critical", parent=base["Normal"],
            fontSize=8, leading=10, fontName="Helvetica-Bold",
            textColor=C_RED),

        "tag_high": ParagraphStyle("tag_high", parent=base["Normal"],
            fontSize=8, leading=10, fontName="Helvetica-Bold",
            textColor=C_ORANGE),

        "tag_medium": ParagraphStyle("tag_medium", parent=base["Normal"],
            fontSize=8, leading=10, fontName="Helvetica-Bold",
            textColor=C_GOLD),

        "tag_positive": ParagraphStyle("tag_positive", parent=base["Normal"],
            fontSize=8, leading=10, fontName="Helvetica-Bold",
            textColor=C_GREEN),
    }
    return styles


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FLOWABLES
# ─────────────────────────────────────────────────────────────────────────────
class ColorBand(Flowable):
    """A full-width colored rectangle used as section headers."""
    def __init__(self, text, color=C_DEEP_BLUE, text_color=C_WHITE,
                 height=1.1*cm, font_size=13):
        super().__init__()
        self.text = text
        self.color = color
        self.text_color = text_color
        self.height = height
        self.font_size = font_size

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.setFillColor(self.text_color)
        self.canv.setFont("Helvetica-Bold", self.font_size)
        self.canv.drawString(10, self.height/2 - self.font_size/2 + 1, self.text)


class SidebarBox(Flowable):
    """Colored left-border info box."""
    def __init__(self, text, bg=C_BLUE_PALE, border=C_STEEL_BLUE,
                 font_size=8.5, width=None):
        super().__init__()
        self._text = text
        self.bg = bg
        self.border = border
        self.font_size = font_size
        self._width = width

    def wrap(self, avail_w, avail_h):
        self.avail_w = self._width or avail_w
        return self.avail_w, 40

    def draw(self):
        self.canv.setFillColor(self.bg)
        self.canv.rect(0, 0, self.avail_w, 30, fill=1, stroke=0)
        self.canv.setFillColor(self.border)
        self.canv.rect(0, 0, 4, 30, fill=1, stroke=0)
        self.canv.setFillColor(C_BLACK)
        self.canv.setFont("Helvetica", self.font_size)
        self.canv.drawString(12, 10, self._text)


def section_header(num, title, s, color=C_DEEP_BLUE):
    return [
        Spacer(1, 0.3*cm),
        ColorBand(f"  {num}   {title.upper()}", color=color, height=1.0*cm, font_size=12),
        Spacer(1, 0.2*cm),
    ]


def subsection(title, s):
    return [Paragraph(title, s["h3"]), Spacer(1, 0.1*cm)]


def bullet_list(items, s, color="•"):
    return [Paragraph(f"<b>{color}</b>  {item}", s["bullet"]) for item in items]


def _cell(text, font_size=7.5, bold=False, color=C_BLACK, bg=None):
    """Wrap a string in a Paragraph so ReportLab word-wraps it properly."""
    if not isinstance(text, str):
        return text  # already a Paragraph or other flowable
    fn = "Helvetica-Bold" if bold else "Helvetica"
    st = ParagraphStyle("tc", fontName=fn, fontSize=font_size,
                        leading=font_size * 1.35, textColor=color,
                        wordWrap="CJK", splitLongWords=1,
                        leftIndent=0, rightIndent=0)
    return Paragraph(text, st)


def _wrap(data, font_size=7.5):
    """Convert every string cell in a 2-D list to a Paragraph."""
    out = []
    for i, row in enumerate(data):
        new_row = []
        for cell in row:
            if isinstance(cell, str):
                bold = (i == 0)          # header row bold
                col = C_WHITE if bold else C_BLACK
                new_row.append(_cell(cell, font_size, bold=bold, color=col))
            else:
                new_row.append(cell)
        out.append(new_row)
    return out


def styled_table(data, col_widths, header_color=C_DEEP_BLUE,
                 alt_color=C_BLUE_PALE, font_size=7.5):
    wrapped = _wrap(data, font_size)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, alt_color]),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_GRAY_MID),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]
    return Table(wrapped, colWidths=col_widths, style=TableStyle(style),
                 repeatRows=1, splitByRow=1)


def finding_box(title, body, severity="INFO", s=None):
    colors_map = {
        "CRITICAL": (C_RED_LIGHT,   C_RED,    "CRITICAL"),
        "HIGH":     (C_ORANGE_LIGHT,C_ORANGE, "HIGH"),
        "MEDIUM":   (C_YELLOW_LIGHT,C_GOLD,   "MEDIUM"),
        "LOW":      (C_GREEN_LIGHT, C_GREEN,  "LOW"),
        "INFO":     (C_BLUE_PALE,   C_STEEL_BLUE, "INFO"),
        "POSITIVE": (C_GREEN_LIGHT, C_GREEN,  "POSITIVE"),
    }
    bg, border, label = colors_map.get(severity, colors_map["INFO"])

    title_data = [[Paragraph(f"[{label}]  {title}", s["finding_title"])]]
    body_data  = [[Paragraph(body, s["finding_body"])]]

    title_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), border),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ])
    body_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, border),
    ])

    return KeepTogether([
        Table(title_data, colWidths=[16.5*cm], style=title_style),
        Table(body_data,  colWidths=[16.5*cm], style=body_style),
        Spacer(1, 0.2*cm),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# MATPLOTLIB CHARTS → ReportLab Images
# ─────────────────────────────────────────────────────────────────────────────
def mpl_to_image(fig, width_cm=16, height_cm=8):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=width_cm*cm, height=height_cm*cm)


def chart_endpoint_distribution():
    fig, ax = plt.subplots(figsize=(11, 4))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    categories = ["Core API\nRouters", "MCP\nTools", "Agent API\nEndpoints",
                  "Node Types", "Rel. Types", "Neo4j\nAdapters"]
    values = [44, 12, 2, 44, 31, 20]
    bar_colors = ["#1B3A6B", "#00897B", "#E65100", "#4A148C", "#F57F17", "#2E6DA4"]

    bars = ax.bar(categories, values, color=bar_colors, width=0.6, edgecolor="white", linewidth=1.5)
    ax.set_ylim(0, 55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(colors="#444444")
    ax.set_ylabel("Count", color="#444444", fontsize=10)
    ax.set_title("Eugene Platform — Component Inventory at a Glance",
                 fontsize=12, fontweight="bold", color="#1B3A6B", pad=12)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                str(val), ha="center", va="bottom", fontsize=10,
                fontweight="bold", color="#1B3A6B")
    return mpl_to_image(fig, 16, 5.5)


def chart_severity_pie():
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    labels = ["Critical", "High", "Medium", "Positive"]
    sizes  = [2, 5, 7, 6]
    explode= [0.05, 0.03, 0, 0]
    pie_colors = ["#B71C1C", "#E65100", "#F57F17", "#1B5E20"]

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=pie_colors, autopct="%1.0f%%",
        startangle=90, explode=explode, pctdistance=0.75,
        wedgeprops=dict(edgecolor="white", linewidth=2)
    )
    for t in texts:
        t.set_fontsize(10)
        t.set_fontweight("bold")
    for at in autotexts:
        at.set_fontsize(9)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.set_title("Finding Distribution by Severity", fontsize=11,
                 fontweight="bold", color="#1B3A6B", pad=10)
    return mpl_to_image(fig, 8, 6)


def chart_latency_heatmap():
    fig, ax = plt.subplots(figsize=(11, 4))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    components = ["Streamlit\nUI", "Agent WS\n(FastAPI)", "Strands\nAgent",
                  "MCP\nServer", "Core API\n(FastAPI)", "Neo4j\nDB"]
    # Risk scores 0-10: latency risk at each layer
    risk = [2, 3, 8, 4, 5, 7]
    bar_colors = [
        "#1B5E20" if r <= 3 else "#F57F17" if r <= 6 else "#B71C1C"
        for r in risk
    ]

    bars = ax.barh(components, risk, color=bar_colors, height=0.55,
                   edgecolor="white", linewidth=1.5)
    ax.set_xlim(0, 10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.axvline(3, color="#1B5E20", linestyle="--", alpha=0.4, linewidth=1)
    ax.axvline(7, color="#B71C1C", linestyle="--", alpha=0.4, linewidth=1)
    ax.set_xlabel("Latency Risk Score (0=Low, 10=Critical)", color="#444444", fontsize=9)
    ax.set_title("Latency Risk by Service Layer",
                 fontsize=12, fontweight="bold", color="#1B3A6B", pad=12)
    ax.tick_params(colors="#444444")

    for bar, val in zip(bars, risk):
        label = "LOW" if val <= 3 else "MEDIUM" if val <= 6 else "HIGH"
        ax.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                f"  {val}/10 — {label}", va="center", fontsize=8.5,
                color="#444444")

    legend_patches = [
        mpatches.Patch(color="#1B5E20", label="Low (0-3)"),
        mpatches.Patch(color="#F57F17", label="Medium (4-6)"),
        mpatches.Patch(color="#B71C1C", label="High (7-10)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=8,
              framealpha=0.8)
    return mpl_to_image(fig, 16, 5)


def chart_ontology_nodes():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle("Eugene Knowledge Graph — Ontology Structure",
                 fontsize=12, fontweight="bold", color="#1B3A6B")

    # Left: Node category distribution
    ax = axes[0]
    ax.set_facecolor("#F8F9FA")
    categories = ["Core Biomedical", "Clinical Trial", "Patent/IP",
                  "Organization", "Drug-Specific", "GraphRAG/PubMed", "TPP"]
    counts = [10, 9, 5, 3, 2, 9, 6]
    cat_colors = ["#1B3A6B","#00897B","#E65100","#4A148C","#F57F17","#2E6DA4","#B71C1C"]
    bars = ax.bar(categories, counts, color=cat_colors, width=0.7,
                  edgecolor="white", linewidth=1.5)
    ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("Node Types", fontsize=9)
    ax.set_title(f"44 Total Node Types by Category", fontsize=10,
                 fontweight="bold", color="#1B3A6B")
    for bar, val in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(val), ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Right: Relationship category distribution
    ax2 = axes[1]
    ax2.set_facecolor("#F8F9FA")
    rel_cats = ["Domain\nRelations", "Biomedical\nAssoc.", "Cross-Domain",
                "Drug Meta", "Patent/Clinical", "Publications"]
    rel_counts = [4, 9, 8, 1, 5, 1]
    rel_colors = ["#1B3A6B","#00897B","#E65100","#4A148C","#F57F17","#2E6DA4"]
    ax2.barh(rel_cats, rel_counts, color=rel_colors, height=0.55,
             edgecolor="white", linewidth=1.5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.set_xlabel("Relationship Types", fontsize=9)
    ax2.set_title(f"31 Total Relationship Types by Category", fontsize=10,
                  fontweight="bold", color="#1B3A6B")
    for i, val in enumerate(rel_counts):
        ax2.text(val + 0.1, i, f"  {val}", va="center", fontsize=9, fontweight="bold")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    return mpl_to_image(fig, 16, 6)


def chart_observability_radar():
    fig, ax = plt.subplots(figsize=(6, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    categories = ["Structured\nLogging", "Metrics\nExport", "Distributed\nTracing",
                  "Health\nChecks", "Rate\nLimiting", "Error\nHandling"]
    N = len(categories)

    current_values = [1, 0, 0, 2, 0, 3]   # out of 10
    target_values  = [9, 8, 7, 9, 8, 9]

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    current_values += current_values[:1]
    target_values  += target_values[:1]

    ax.plot(angles, target_values, "o--", color="#00897B", linewidth=1.5,
            label="Target State", alpha=0.8)
    ax.fill(angles, target_values, alpha=0.08, color="#00897B")
    ax.plot(angles, current_values, "o-", color="#B71C1C", linewidth=2,
            label="Current State")
    ax.fill(angles, current_values, alpha=0.2, color="#B71C1C")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=7, color="#888888")
    ax.grid(color="#CCCCCC", linewidth=0.5)
    ax.set_title("Observability Maturity — Current vs Target",
                 fontsize=10, fontweight="bold", color="#1B3A6B", pad=15)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)

    return mpl_to_image(fig, 8, 6)


def chart_remediation_roadmap():
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    tasks = [
        "Enable SSL Verification",
        "Add Query Timeouts",
        "Agent Execution Timeout",
        "Health Check Deps",
        "Structured Logging (JSON)",
        "Rate Limiting Middleware",
        "Conversation Manager Fix",
        "Prometheus Metrics Export",
        "OpenTelemetry Tracing",
        "Session Recovery Mechanism",
    ]
    start_weeks = [0, 0, 1, 1, 2, 2, 3, 4, 5, 6]
    durations   = [0.5, 1, 1, 1, 2, 1, 2, 2, 3, 2]
    priorities  = ["C","H","H","H","M","M","M","M","M","M"]
    p_colors = {"C": "#B71C1C", "H": "#E65100", "M": "#F57F17"}
    bar_clrs = [p_colors[p] for p in priorities]

    y_pos = list(range(len(tasks)))
    ax.barh(y_pos, durations, left=start_weeks, color=bar_clrs, height=0.6,
            edgecolor="white", linewidth=1.2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tasks, fontsize=8.5)
    ax.set_xlabel("Weeks from Start", fontsize=9)
    ax.set_xticks(range(9))
    ax.set_xticklabels([f"Wk {i}" for i in range(9)], fontsize=8)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("Remediation Roadmap — Priority Timeline",
                 fontsize=12, fontweight="bold", color="#1B3A6B", pad=12)

    legend_patches = [
        mpatches.Patch(color="#B71C1C", label="Critical"),
        mpatches.Patch(color="#E65100", label="High"),
        mpatches.Patch(color="#F57F17", label="Medium"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=8)
    ax.axvline(2, color="#1B3A6B", linestyle="--", alpha=0.3, linewidth=1, label="Week 2")
    plt.tight_layout()
    return mpl_to_image(fig, 16, 6.5)


def chart_arch_layer():
    """Simple layered architecture diagram using matplotlib."""
    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5)
    ax.axis("off")

    layers = [
        (0.3, 3.5, 2.0, 1.0, "#1B3A6B",  "LAYER 1\nStreamlit UI\n:18501",     "#FFFFFF"),
        (2.7, 3.5, 2.0, 1.0, "#2E6DA4",  "LAYER 2\nAgent Backend\n:18001",    "#FFFFFF"),
        (5.1, 3.5, 2.0, 1.0, "#00897B",  "LAYER 3\nStrands Agent\n(In-Proc)", "#FFFFFF"),
        (7.5, 3.5, 2.0, 1.0, "#4A148C",  "LAYER 4\nMCP Server\n:18443",       "#FFFFFF"),
        (9.9, 3.5, 2.0, 1.0, "#E65100",  "LAYER 5\nCore API\n:18000",         "#FFFFFF"),
        (9.9, 1.8, 2.0, 1.0, "#B71C1C",  "Neo4j\nGraph DB\n:17687",           "#FFFFFF"),
    ]

    for x, y, w, h, col, label, txt_col in layers:
        rect = mpatches.FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.08", facecolor=col, edgecolor="white",
            linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center",
                fontsize=7.5, color=txt_col, fontweight="bold",
                multialignment="center")

    # Arrows between layers 1-5
    arrow_xs = [(2.3, 2.7), (4.7, 5.1), (7.1, 7.5), (9.5, 9.9)]
    for (x1, x2) in arrow_xs:
        ax.annotate("", xy=(x2, 4.0), xytext=(x1, 4.0),
                    arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5))

    # Arrow from Core API down to Neo4j
    ax.annotate("", xy=(10.9, 2.8), xytext=(10.9, 3.5),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5))

    # Data flow label
    ax.text(6.5, 3.2, "JWT propagated end-to-end ►", ha="center", va="center",
            fontsize=8, color="#1B3A6B", fontstyle="italic")

    ax.set_title("Eugene Platform — Service Layer Architecture",
                 fontsize=12, fontweight="bold", color="#1B3A6B", pad=8)
    plt.tight_layout()
    return mpl_to_image(fig, 16, 5)


# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
def build_cover(s):
    story = []

    # Background-colored band (simulated via table)
    cover_bg = Table(
        [[Paragraph("", s["body"])]],
        colWidths=[W - 4*cm], rowHeights=[3*cm],
        style=TableStyle([("BACKGROUND", (0,0), (-1,-1), C_DEEP_BLUE)])
    )

    logo_band = Table(
        [[Paragraph("EUGENE PLATFORM", ParagraphStyle(
            "lp", fontName="Helvetica-Bold", fontSize=10,
            textColor=C_TEAL, alignment=TA_CENTER))]],
        colWidths=[W - 4*cm], rowHeights=[1.2*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), C_DEEP_BLUE)])
    )

    title_data = [[Paragraph(
        "Assessment &amp;<br/>Audit Report", s["cover_title"]
    )]]
    title_band = Table(title_data, colWidths=[W - 4*cm], rowHeights=[4.5*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), C_DEEP_BLUE),
                          ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))

    sub_data = [[Paragraph(
        "Eugene Knowledge Graph &amp; Agentic AI Platform<br/>"
        "Production Readiness Assessment | CSL Behring", s["cover_sub"]
    )]]
    sub_band = Table(sub_data, colWidths=[W - 4*cm], rowHeights=[2*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), C_DEEP_BLUE),
                          ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))

    stripe_data = [[""]]
    stripe_band = Table(stripe_data, colWidths=[W - 4*cm], rowHeights=[0.4*cm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), C_TEAL)]))

    meta_items = [
        ["Document Type:", "Inception & Audit Report"],
        ["Prepared For:", "CSL Behring"],
        ["Prepared By:", "Rajesh Gupta"],
        ["Classification:", "CONFIDENTIAL"],
        ["System Under Review:", "Eugene Knowledge Graph v2.x"],
        ["Audit Scope:", "Code, Architecture, Security, Observability, Agent Framework"],
    ]

    meta_table_data = [[
        Paragraph(k, ParagraphStyle("mk", fontName="Helvetica-Bold",
                                    fontSize=9, textColor=C_STEEL_BLUE)),
        Paragraph(v, ParagraphStyle("mv", fontName="Helvetica",
                                    fontSize=9, textColor=C_BLACK))
    ] for k, v in meta_items]

    meta_table = Table(meta_table_data, colWidths=[5*cm, 11.5*cm],
        style=TableStyle([
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_WHITE, C_BLUE_PALE]),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("BOX",(0,0),(-1,-1),0.5, C_STEEL_BLUE),
        ]))

    story += [
        logo_band,
        title_band,
        sub_band,
        stripe_band,
        Spacer(1, 1.5*cm),
        meta_table,
        Spacer(1, 1*cm),
    ]

    # Summary stats strip
    stats = [
        ("44", "API Endpoints"),
        ("12", "MCP Tools"),
        ("44", "Node Types"),
        ("31", "Rel. Types"),
        ("20", "Neo4j Adapters"),
        ("14", "Findings"),
    ]
    stats_cells = [[
        Table([[
            Paragraph(v, ParagraphStyle("sv", fontName="Helvetica-Bold",
                fontSize=16, textColor=C_WHITE, alignment=TA_CENTER)),
            Paragraph(l, ParagraphStyle("sl", fontName="Helvetica",
                fontSize=7, textColor=C_BLUE_PALE, alignment=TA_CENTER))
        ]], colWidths=[2.6*cm],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),
             [C_DEEP_BLUE, C_STEEL_BLUE, C_TEAL, C_PURPLE, C_ORANGE, C_RED][i % 6]),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        for i, (v, l) in enumerate(stats)
    ]]
    stats_table = Table(stats_cells, colWidths=[2.65*cm]*6,
        style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),2),
                          ("RIGHTPADDING",(0,0),(-1,-1),2)]))
    story.append(stats_table)
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: EXECUTIVE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
def build_exec_summary(s):
    story = section_header("01", "Executive Summary", s, C_DEEP_BLUE)

    story.append(Paragraph(
        "This report presents the findings of the Stage 1 Assessment & Audit of the "
        "<b>Eugene Platform</b> — CSL Behring's proprietary biomedical knowledge graph and "
        "agentic AI system. The audit covers architecture, code quality, agent framework design, "
        "security posture, observability maturity, latency hot-spots, state synchronisation gaps, "
        "and graph schema completeness. The assessment was conducted through exhaustive source "
        "code review, live system inspection, and architectural analysis across all four "
        "microservices: <b>eugene_ws</b> (Core API), <b>eugene-agent-ws</b> (Agent Backend), "
        "<b>eugene-mcp</b> (MCP Server), and <b>eugene-agent-ui</b> (Streamlit UI).",
        s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("Key Findings at a Glance", s["h3"]))

    summary_data = [
        ["Category", "Status", "Priority Findings"],
        ["Architecture", "STRONG", "Clean DDD + hexagonal design; 44 endpoints across 19 routers"],
        ["Knowledge Graph", "STRONG", "44 node types, 31 relationship types; comprehensive ontology"],
        ["Agent Framework", "NEEDS WORK", "Shared conversation manager creates race conditions"],
        ["Security", "CRITICAL", "SSL verification disabled; insufficient allowlist error handling"],
        ["Observability", "POOR", "No structured logging, no metrics export, no distributed tracing"],
        ["Latency", "NEEDS WORK", "Unbounded N-hop queries; no query timeouts; deep pagination risk"],
        ["State Sync", "NEEDS WORK", "File-based sessions; no recovery on process restart"],
        ["MCP Tools", "GOOD", "12 tools fully operational; stateless HTTP design is scalable"],
    ]

    col_w = [3.8*cm, 2.8*cm, 10*cm]
    tbl = Table(summary_data, colWidths=col_w)
    status_colors = {
        "STRONG": C_GREEN, "GOOD": C_TEAL, "NEEDS WORK": C_GOLD,
        "POOR": C_ORANGE, "CRITICAL": C_RED
    }

    style = [
        ("BACKGROUND", (0,0), (-1,0), C_DEEP_BLUE),
        ("TEXTCOLOR",  (0,0), (-1,0), C_WHITE),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("GRID",       (0,0), (-1,-1), 0.5, C_GRAY_MID),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]
    for i, row in enumerate(summary_data[1:], 1):
        status = row[1]
        col = status_colors.get(status, C_GRAY_MID)
        style.append(("BACKGROUND", (1, i), (1, i), col))
        style.append(("TEXTCOLOR",  (1, i), (1, i), C_WHITE))
        style.append(("FONTNAME",   (1, i), (1, i), "Helvetica-Bold"))
        style.append(("ROWBACKGROUNDS", (0, i), (0, i), [C_GRAY_LIGHT if i%2==0 else C_WHITE]))
        style.append(("ROWBACKGROUNDS", (2, i), (2, i), [C_BLUE_PALE if i%2==0 else C_WHITE]))

    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 0.3*cm))

    story.append(chart_endpoint_distribution())
    story.append(Paragraph("Figure 1: Eugene Platform Component Inventory", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("Critical Immediate Actions Required", s["h3"]))
    story += bullet_list([
        "<b>CRITICAL:</b> Enable SSL certificate verification in MCP client connections (1-day fix)",
        "<b>CRITICAL:</b> Fix shared SlidingWindowConversationManager — race conditions in concurrent sessions",
        "<b>HIGH:</b> Add Neo4j query timeouts (30s) and agent execution limits (10 min)",
        "<b>HIGH:</b> Implement comprehensive health checks with dependency validation",
        "<b>HIGH:</b> Add structured JSON logging for log aggregation compatibility",
    ], s)
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: CURRENT-STATE ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────
def build_architecture(s):
    story = section_header("02", "Current-State Architecture & Call-Graph", s, C_STEEL_BLUE)

    story.append(Paragraph("2.1  Service Topology", s["h3"]))
    story.append(Paragraph(
        "The Eugene platform is composed of four containerised microservices orchestrated "
        "via Docker Compose locally and AWS ECS Fargate in production. All services run "
        "Python 3.13 and communicate over internal Docker networks. The startup dependency "
        "chain is strictly enforced: <b>Neo4j → eugene_ws → eugene_mcp → eugene_agent_ws → "
        "eugene_agent_ui</b>. Ports are prefixed with <b>1xxxx</b> externally to avoid "
        "conflicts with other local services.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(chart_arch_layer())
    story.append(Paragraph("Figure 2: Eugene Service Layer Architecture", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("2.2  Service Inventory", s["h3"]))
    svc_data = [
        ["Service", "Container", "External Port", "Internal Port", "Framework", "Role"],
        ["Neo4j DB", "eugene-neo4j", "17474 (HTTP)\n17687 (Bolt)", "7474 / 7687",
         "Neo4j 5.26.9", "Graph data store"],
        ["Core API", "eugene-ws", "18000", "8000",
         "FastAPI + Uvicorn", "Primary REST API — 44 endpoints"],
        ["MCP Server", "eugene-mcp", "18443", "8000",
         "FastMCP", "12 registered MCP tools"],
        ["Agent Backend", "eugene-agent-ws", "18001", "8000",
         "FastAPI + Strands", "ReAct agent orchestration"],
        ["Chat UI", "eugene-agent-ui", "18501", "8501",
         "Streamlit", "Conversational web interface"],
    ]
    story.append(styled_table(svc_data, [3.5*cm, 3*cm, 2.5*cm, 2*cm, 3*cm, 4.5*cm],
                              font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("2.3  Core API Endpoint Catalog (19 Routers / 44 Endpoints)", s["h3"]))
    ep_data = [
        ["Router", "Prefix", "Key Endpoints", "Auth"],
        ["auth_router", "/", "/login, /auth/whoami, /auth/callback", "Public / Entra ID"],
        ["health_router", "/", "/health", "Public"],
        ["count_router", "/count", "/{label}", "JWT"],
        ["label_router", "/labels", "/{label} — paginated, max 50", "JWT"],
        ["node_id_lookup_router", "/node", "/find/{node_value}?fuzzy_match", "JWT"],
        ["node_details_router", "/node", "/details [POST] — max 50 IDs", "JWT"],
        ["n_hop_router", "/graph", "/relationship/start/{id}?n_hop — max 2 hops", "JWT"],
        ["search_path_router", "/graph", "/path/start/{id}/end/{id}\n/reachability/start/.../end/...", "JWT"],
        ["facet_router", "/facet", "/{label} [POST] — faceted search", "JWT"],
        ["similarity_router", "/similarity", "/{label} [POST]", "JWT"],
        ["drug_alias_search_router", "/drugs", "/aliases/{drug_name}\n/aliases/id/{drug_id}", "JWT"],
        ["patent_search_router", "/patents", "/drugs, /clinicaltrials, /geneproteins", "JWT"],
        ["pubmed_search_router", "/pmids", "/drugs, /clinicaltrials, /geneproteins", "JWT"],
        ["facts_router", "/graph", "/facts/start/{id} — fixed n_hop=1", "JWT"],
        ["organization_search_router", "/organizations", "/{name} (wildcard)\n/assets/{organization_id}", "JWT"],
        ["tpp_router", "/embeddings", "4 embedding search endpoints", "JWT"],
        ["database_stats_router", "/stats", "Graph statistics", "JWT"],
        ["release_notes_router", "/", "Release notes", "JWT"],
    ]
    story.append(styled_table(ep_data, [4*cm, 2.2*cm, 7.3*cm, 2*cm], font_size=7))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("2.4  Agent API & MCP Tool Inventory", s["h3"]))
    mcp_data = [
        ["MCP Tool", "Tool Class", "Core API Endpoint", "Purpose"],
        ["fetch_identity", "EugeneIdentityTools", "/auth/whoami", "Return current user identity"],
        ["fetch_by_label", "EugeneFetchTools", "/labels/{label}", "List all nodes of a label type"],
        ["fetch_similar", "EugeneFetchTools", "/similarity/{label}", "Find related nodes by relationship"],
        ["lookup_node_by_value", "EugeneNodeTools", "/node/find/{value}", "Translate name to node_id"],
        ["fetch_node_details", "EugeneNodeTools", "/node/details [POST]", "Get node properties (max 50 IDs)"],
        ["fetch_drug_aliases", "EugeneDrugTools", "/drugs/aliases/{name}", "Drug brand/generic synonyms"],
        ["fetch_facts", "EugeneFactTools", "/graph/facts/start/{id}", "Retrieve facts for a node"],
        ["fetch_node_relationships", "EugeneGraphTools", "/graph/relationship/start/{id}", "N-hop graph traversal (max 2)"],
        ["has_reachable_path", "EugeneGraphTools", "/graph/reachability/.../...", "Boolean path existence check"],
        ["fetch_paths", "EugeneGraphTools", "/graph/path/start/{id}/end/{id}", "All paths between two nodes"],
        ["find_organization_names", "EugeneOrganizationTools", "/organizations/{pattern}", "Wildcard organisation search"],
        ["find_organization_assets", "EugeneOrganizationTools", "/organizations/assets/{id}", "Company IP and drug assets"],
    ]
    story.append(styled_table(mcp_data, [3.8*cm, 4.2*cm, 4.2*cm, 4.3*cm],
                              header_color=C_PURPLE, alt_color=C_PURPLE_LIGHT, font_size=7))
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: KNOWLEDGE GRAPH ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────
def build_ontology(s):
    story = section_header("03", "Eugene Knowledge Graph — Ontology Assessment", s, C_TEAL)

    story.append(Paragraph(
        "The Eugene knowledge graph uses a rich, multi-domain ontology designed for biomedical "
        "competitive intelligence. The schema integrates data from <b>USPTO</b> (patents), "
        "<b>PubMed/PMC</b> (publications), <b>ClinicalTrials.gov</b> (trials), and internal "
        "CSL Behring TPP (Target Product Profile) documents into a unified Neo4j graph.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(chart_ontology_nodes())
    story.append(Paragraph("Figure 3: Eugene Ontology — Node Types & Relationship Distribution", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("3.1  Node Types (44 Total)", s["h3"]))
    node_data = [
        ["Category", "Node Labels", "Count", "Data Source"],
        ["Core Biomedical", "ANATOMY, BIOLOGICAL_PROCESS, CELLULAR_COMPONENT, DISEASE, DRUG,\nEFFECT_PHENOTYPE, EXPOSURE, GENE_PROTEIN, MOLECULAR_FUNCTION, PATHWAY", "10", "Hetionet/DrugBank"],
        ["Clinical Trial", "CLINICAL_TRIAL, CONDITION, INTERVENTION, PHASE, PRIMARY_OUTCOME_MEASURE,\nSECONDARY_OUTCOME_MEASURE, SPONSOR, COLLABORATOR, FUNDER_TYPE", "9", "ClinicalTrials.gov"],
        ["Patent / IP", "PATENT, APPROVED_PATENT, PATENT_APPLICATION,\nUSPTO_APPLICATION, USPTO_PGPUB", "5", "USPTO"],
        ["Drug-Specific", "DRUG_PRODUCT, DRUG_SYNONYM", "2", "DrugBank"],
        ["Organization", "ORGANIZATION, RESEARCH, INVESTIGATORS", "3", "Internal / Web"],
        ["GraphRAG / Docs", "SUMMARY, SUMMARY_FINDING, PUBMED_DOCUMENT,\nPUBMED_SUMMARY, PUBMED_SUMMARY_FINDING", "5", "PubMed / LLM"],
        ["TPP / CSL", "CSL_TPP, CSL_TPP_QUESTION", "2", "Internal CSL"],
        ["Metadata", "UNKNOWN", "1", "System"],
    ]
    story.append(styled_table(node_data, [3*cm, 6.5*cm, 1.5*cm, 3.5*cm],
                              header_color=C_TEAL, alt_color=C_TEAL_LIGHT, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("3.2  Relationship Types (31 Total)", s["h3"]))
    rel_data = [
        ["Relationship Type", "Category", "Cardinality", "Example"],
        ["INDICATION", "Drug-Disease", "Many-to-Many", "Emicizumab → Hemophilia A"],
        ["CONTRAINDICATION", "Drug-Disease", "Many-to-Many", "Drug → Disease"],
        ["OFF_LABEL_USE", "Drug-Disease", "Many-to-Many", "Drug → Disease (off-label)"],
        ["DRUG_EFFECT", "Drug-Phenotype", "Many-to-Many", "Drug → SideEffect"],
        ["DRUG_PROTEIN", "Drug-Target", "Many-to-Many", "Drug → GeneProtein (target)"],
        ["DISEASE_PROTEIN", "Disease-Gene", "Many-to-Many", "Hemophilia A → Factor VIII"],
        ["PROTEIN_PROTEIN", "Gene-Gene", "Many-to-Many", "GeneProtein interactions"],
        ["DISCLOSED_IN", "Drug-Patent", "Many-to-Many", "Drug → Patent"],
        ["FEATURED_IN", "Trial-Drug", "Many-to-Many", "ClinicalTrial → Drug"],
        ["HAS_PUBLICATION", "Node-PubMed", "One-to-Many", "Drug → PubMedDocument"],
        ["SUPPORTS_PATENT_APPLICATION", "Node-Patent", "Many-to-Many", "Drug → PatentApp"],
        ["HAS_DRUG_ALIAS", "Drug-Synonym", "One-to-Many", "Drug → DrugSynonym"],
    ]
    story.append(styled_table(rel_data, [4.5*cm, 3*cm, 3*cm, 6*cm],
                              header_color=C_TEAL, alt_color=C_TEAL_LIGHT, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("3.3  Typical Query Patterns & Graph Traversal Logic", s["h3"]))
    qp_data = [
        ["Query Pattern", "Cypher Pattern", "N-hop Limit", "Used In"],
        ["Node lookup by name", "MATCH (n {node_name: $name}) RETURN n", "0", "lookup_node_by_value"],
        ["Node lookup by ID", "MATCH (n {node_id: $id}) RETURN n", "0", "fetch_node_details"],
        ["N-hop subgraph", "MATCH (s {node_id:$id})-[r]-{0,N}(e) UNWIND(r) AS rel RETURN...", "Max 2", "fetch_node_relationships"],
        ["Path finding", "MATCH p=shortestPath((s)-[*..N]-(e)) RETURN p", "Max 4", "fetch_paths"],
        ["Reachability check", "MATCH (s)-[*..N]-(e) RETURN COUNT(*)>0", "Max 4", "has_reachable_path"],
        ["Drug-patent join", "MATCH (d:Drug)-[:DISCLOSED_IN]->(p:Patent) WHERE d.node_id=$id", "1", "patent_search_router"],
        ["Org asset lookup", "MATCH (o:Organisation)-[r]-(asset) WHERE o.node_id=$id", "1", "find_organization_assets"],
        ["Faceted search", "MATCH (n:{label}) WHERE n.node_name IN $values RETURN n", "0", "facet_router"],
        ["Graph density", "CALL apoc.meta.stats() YIELD relCount, nodeCount", "N/A", "analytics"],
    ]
    story.append(styled_table(qp_data, [3.5*cm, 7*cm, 1.5*cm, 3.5*cm],
                              header_color=C_TEAL, alt_color=C_TEAL_LIGHT, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story += [
        finding_box(
            "Graph Traversal Hard Limit — MAX_SUPPORTED_HOPS = 2",
            "The Neo4j n-hop adapter enforces a maximum of 2 hops "
            "(neo4j_foundational_n_hop_adapter.py:19). This is intentional — the Eugene graph "
            "is highly connected, and unconstrained traversal beyond 2 hops would return "
            "the entire graph, causing memory exhaustion and agent hang. This limit must be "
            "preserved and validated at the API gateway level.", "INFO", s
        ),
        finding_box(
            "No Graph Statistics Dashboard",
            "The only graph analytics queries in saved_queries/ are density.cypher (using "
            "apoc.meta.stats) and diameter.cypher (O(n²) expensive operation). There is no "
            "live dashboard showing node/edge counts, growth rate, or coverage gaps by category. "
            "Recommend adding a /stats/graph endpoint returning node counts per label and "
            "relationship counts per type.", "MEDIUM", s
        ),
    ]
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: AGENT FRAMEWORK DEEP-DIVE
# ─────────────────────────────────────────────────────────────────────────────
def build_agent_analysis(s):
    story = section_header("04", "Strands Agent Framework — Deep-Dive & Hanging Runs Analysis", s, C_PURPLE)

    story.append(Paragraph(
        "The agent layer is the most complex and highest-risk component of the Eugene platform. "
        "It uses the <b>Strands agent framework</b> with a <b>ReAct (Reason-Act-Observe)</b> "
        "loop to orchestrate multi-step LLM-driven queries against the knowledge graph via MCP tools. "
        "The audit identified several design issues that are direct root causes of the reported "
        "<b>'Hanging Runs'</b> phenomenon.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("4.1  Agent Architecture", s["h3"]))
    agent_data = [
        ["Component", "Class/Module", "Configuration", "Risk"],
        ["Agent Executor", "EugeneDataAgent", "Singleton per process", "LOW"],
        ["LLM Model", "Anthropic Claude Sonnet 4\nOpenAI GPT-4.1-mini", "Auto-detected via env vars", "LOW"],
        ["Conv. Manager", "SlidingWindowConversationManager", "window_size=10, per_turn=2\nShared singleton — RACE CONDITION", "CRITICAL"],
        ["Session Manager", "FileSessionManager", "File-based, session_id=conversation_id", "MEDIUM"],
        ["MCP Client", "MCPClient (streamable-http)", "verify=False — SSL disabled", "CRITICAL"],
        ["Tool Timeout", "OpenAI: 60s / Anthropic: None", "No circuit breaker", "HIGH"],
        ["Max Iterations", "None configured", "Unbounded ReAct loop", "HIGH"],
        ["Local Tools", "calculator, current_time, python_repl", "Always loaded (not conditional)", "LOW"],
    ]
    story.append(styled_table(agent_data, [3.5*cm, 4*cm, 4.5*cm, 2.5*cm],
                              header_color=C_PURPLE, alt_color=C_PURPLE_LIGHT, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("4.2  Root Cause Analysis — 'Hanging Runs'", s["h3"]))
    story.append(Paragraph(
        "Based on code review, the following five root causes account for the majority of "
        "reported hanging agent runs:", s["body"]
    ))
    story.append(Spacer(1, 0.1*cm))

    story += [
        finding_box("Root Cause #1 — Unbounded ReAct Loop",
            "There is no maximum iteration count configured for the Strands Agent. The ReAct loop "
            "can continue indefinitely if the LLM keeps deciding to call tools. For complex "
            "biomedical queries, the agent may cycle through multiple lookup → relationship → fact "
            "tool calls without converging to a final answer. "
            "Fix: Add max_iterations=25 to Agent constructor.", "CRITICAL", s),

        finding_box("Root Cause #2 — Shared SlidingWindowConversationManager",
            "The conversation manager is created ONCE in EugeneDataAgent.__init__() and shared "
            "across all agent instances created by _init_agent(). Under concurrent requests, "
            "multiple agents write to the same conversation window simultaneously, causing data "
            "corruption and potentially causing the agent to reason from incorrect conversation "
            "history, leading to repeated tool calls and loops. "
            "Fix: Instantiate SlidingWindowConversationManager per conversation, not per agent service.", "CRITICAL", s),

        finding_box("Root Cause #3 — No Query Timeout on Neo4j",
            "The Neo4j driver is initialised without a socket_keepalive or query timeout "
            "configuration. A slow or deadlocked Cypher query will block the adapter thread "
            "indefinitely. The n-hop adapter query on a large subgraph (n_hop=2 on a hub node "
            "with 10,000+ connections) can take 30-60 seconds and holds the thread. "
            "Fix: Pass connection_timeout=30 and max_transaction_retry_time=30 to neo4j.GraphDatabase.driver().", "HIGH", s),

        finding_box("Root Cause #4 — No Agent-Level Execution Timeout",
            "The generate_chat_response() async generator has no timeout wrapper. If the Strands "
            "agent stalls mid-execution (e.g., waiting for MCP tool response), the StreamingResponse "
            "connection is held open until the client (Streamlit, httpx) times out at 120 seconds. "
            "The MCP httpx client has no timeout either. "
            "Fix: Wrap agent.stream_async() with asyncio.wait_for(timeout=300).", "HIGH", s),

        finding_box("Root Cause #5 — File Session Manager Contention",
            "FileSessionManager writes conversation state to disk using the conversation_id as the "
            "file name. If two concurrent requests arrive with the same conversation_id (e.g., "
            "user double-clicks), both agents attempt to read and write the same session file. "
            "This causes state corruption and unpredictable agent behaviour. "
            "Fix: Use file locking (fcntl.flock) or migrate to a Redis/DynamoDB-backed session store.", "HIGH", s),
    ]

    story.append(Paragraph("4.3  LLM Provider Configuration", s["h3"]))
    llm_data = [
        ["Parameter", "Anthropic (Claude)", "OpenAI (GPT)"],
        ["Model ID", "claude-sonnet-4-20250514", "gpt-4.1-mini"],
        ["Max Tokens", "16,384", "4,096"],
        ["Temperature", "0.7", "0.7"],
        ["Top P", "Default", "1.0"],
        ["Timeout", "Not configured (RISK)", "60.0 seconds"],
        ["Max Retries", "Not configured", "3"],
        ["Selection", "Preferred (if ANTHROPIC_API_KEY present)", "Fallback"],
        ["Cost", "Higher per token", "Lower per token"],
    ]
    story.append(styled_table(llm_data, [4*cm, 6.5*cm, 6.5*cm],
                              header_color=C_PURPLE, alt_color=C_PURPLE_LIGHT, font_size=8))
    story.append(Spacer(1, 0.2*cm))

    story += [
        finding_box("Anthropic Client Timeout Not Configured",
            "The Anthropic LLM client has no timeout set. If the Anthropic API experiences "
            "latency or drops a connection mid-stream, the agent will hang indefinitely. "
            "OpenAI has a 60-second timeout configured. Anthropic should match this. "
            "Fix: Pass timeout=60.0 to the Anthropic model configuration.", "HIGH", s),
    ]
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: LATENCY HOT-SPOTS
# ─────────────────────────────────────────────────────────────────────────────
def build_latency(s):
    story = section_header("05", "Latency Hot-Spots & Performance Baseline", s, C_ORANGE)

    story.append(Paragraph(
        "Without live access to the AWS environment, quantified P50/P95/P99 latency baselines "
        "cannot be established from runtime data. This section presents code-review-derived "
        "latency risk assessments and estimated latency envelopes based on architectural "
        "analysis. These estimates should be validated once AWS/AI Accelerator access is granted.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(chart_latency_heatmap())
    story.append(Paragraph("Figure 4: Latency Risk Score by Service Layer", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("5.1  Estimated Latency Envelope (Code-Review Basis)", s["h3"]))
    lat_data = [
        ["Operation", "Estimated P50", "Estimated P95", "Primary Risk Factor", "Priority"],
        ["Health check (/health)", "5ms", "20ms", "None — static response", "LOW"],
        ["Node lookup by value", "20-50ms", "200ms", "Neo4j Bolt RTT", "LOW"],
        ["N-hop query (n_hop=1)", "80-200ms", "500ms", "Graph traversal depth", "MEDIUM"],
        ["N-hop query (n_hop=2)", "500ms-2s", "5-10s", "Highly-connected hub nodes", "HIGH"],
        ["Path finding (n_hop=4)", "1-5s", "15-30s", "Exponential path explosion", "HIGH"],
        ["Drug alias lookup", "30-100ms", "300ms", "Index scan on node_name", "LOW"],
        ["Organization search (wildcard)", "100-500ms", "2s", "Regex match on large dataset", "MEDIUM"],
        ["Facts retrieval (n_hop=1)", "200-500ms", "2s", "Subgraph + LLM summarization", "MEDIUM"],
        ["Agent execution (simple)", "3-8s", "20s", "LLM token generation", "MEDIUM"],
        ["Agent execution (complex)", "15-60s", "120s+", "Multiple tool calls + LLM", "HIGH"],
        ["MCP tool round-trip", "50-200ms", "500ms", "HTTP overhead + Core API", "LOW"],
    ]
    story.append(styled_table(lat_data, [4.5*cm, 2*cm, 2*cm, 4.5*cm, 1.5*cm],
                              header_color=C_ORANGE, alt_color=C_ORANGE_LIGHT, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("5.2  Identified Hot-Spots in Code", s["h3"]))
    hotspot_data = [
        ["File Location", "Function", "Issue", "Severity"],
        ["neo4j_foundational_n_hop_adapter.py:19", "collect_by_start_id_and_end_id", "No query timeout; hub nodes return 10K+ rows", "HIGH"],
        ["neo4j_foundational_path_adapter.py", "find_shortest_path", "Max 4 hops — exponential traversal risk", "HIGH"],
        ["foundational_n_hop_provider.py", "_ensure_result_size_or_raise", "10K row cap checked AFTER query runs (too late)", "MEDIUM"],
        ["graph_db_connection_factory.py", "remote_neo4j_instance", "No pool_size or connection timeout configured", "MEDIUM"],
        ["foundation/infra/db/util/pagination.py", "calculate_limit_and_offset", "No max OFFSET validation — deep pagination risk", "MEDIUM"],
        ["organization_search_router.py", "/{organization_name}", "Wildcard regex match — O(n) full scan", "MEDIUM"],
        ["annotation/timer_annotation.py", "log_time wrapper", "Decorator incompatible with async functions", "LOW"],
        ["eugene_data_agent.py:execute_stream", "agent.stream_async", "No asyncio.wait_for timeout wrapper", "HIGH"],
    ]
    story.append(styled_table(hotspot_data, [5*cm, 4*cm, 5*cm, 1.5*cm],
                              header_color=C_ORANGE, alt_color=C_ORANGE_LIGHT, font_size=7))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("5.3  Performance Recommendations", s["h3"]))
    perf_recs = [
        "Add <b>socket_keepalive=True</b> and <b>connection_timeout=10</b> to Neo4j driver initialisation",
        "Set <b>max_transaction_retry_time=30</b> on Neo4j driver for automatic retry on transient failures",
        "Add <b>explicit LIMIT clause</b> in n-hop Cypher BEFORE returning results (not just Python-side guard)",
        "Implement <b>query result caching</b> (Redis/in-memory) for frequently accessed hub nodes (drugs, diseases)",
        "Fix <b>async @log_time</b> decorator to properly wrap coroutines using functools.wraps + async def wrapper",
        "Add <b>SKIP validation</b> in pagination.py — reject requests with OFFSET > 100,000",
        "Consider <b>pre-materialised views</b> for top-100 most queried drug/disease relationship subgraphs",
        "Use <b>Neo4j query hints</b> (USING INDEX) for node_id and node_name lookups",
    ]
    story += bullet_list(perf_recs, s)
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: SECURITY ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────
def build_security(s):
    story = section_header("06", "Security Architecture Assessment", s, C_RED)

    story.append(Paragraph(
        "The Eugene platform implements a two-layer authentication strategy: "
        "<b>Microsoft Entra ID (Azure AD)</b> OAuth 2.0 for identity federation and "
        "<b>Eugene-internal HS256 JWT</b> for service authorisation. This is a sound approach "
        "for enterprise deployment. However, several implementation gaps were identified that "
        "require immediate remediation.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("6.1  Authentication Flow", s["h3"]))
    auth_data = [
        ["Step", "Actor", "Action", "Token Type", "Validation"],
        ["1", "User → Browser", "Navigate to /login", "None", "N/A"],
        ["2", "Core API → Entra ID", "Redirect to Microsoft MASL OAuth endpoint", "Auth Code", "PKCE"],
        ["3", "Entra ID → Core API", "Return ID token + access token", "Entra JWT", "MASL library"],
        ["4", "Core API → User", "Issue Eugene internal JWT (HS256)", "Eugene JWT", "HS256 + claims"],
        ["5", "User → Agent WS", "POST with Bearer token", "Eugene JWT", "validate_eugene_access_token()"],
        ["6", "Agent WS → MCP", "Forward JWT in httpx header", "Eugene JWT", "FastMCP JWTVerifier"],
        ["7", "MCP → Core API", "Forward JWT in httpx header", "Eugene JWT", "Core API auth middleware"],
    ]
    story.append(styled_table(auth_data, [1*cm, 3*cm, 5*cm, 2.5*cm, 3.5*cm],
                              header_color=C_RED, alt_color=C_RED_LIGHT, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("6.2  JWT Token Validation (Claims Checked)", s["h3"]))
    jwt_data = [
        ["Claim", "Required?", "Validated?", "Value Expected"],
        ["exp (expiration)", "YES", "YES (require_exp=True)", "Future timestamp"],
        ["iat (issued-at)", "YES", "YES (require_iat=True)", "Past timestamp"],
        ["aud (audience)", "YES", "YES (verify_aud=True)", "api://eugene/<GUID>"],
        ["iss (issuer)", "YES", "YES (verify_iss=True)", "https://eugene.ai/.../..."],
        ["tid (tenant ID)", "YES", "YES (custom check)", "CSL tenant GUID"],
        ["sub (subject)", "YES", "YES (custom check)", "User identifier"],
        ["roles", "YES", "YES (custom check)", "['user.public.read', ...]"],
        ["upn (user principal)", "YES", "YES (custom check)", "user@cslbehring.com"],
        ["name", "NO", "NO", "Display name"],
    ]
    story.append(styled_table(jwt_data, [3.5*cm, 2*cm, 3*cm, 6*cm],
                              header_color=C_RED, alt_color=C_RED_LIGHT, font_size=8))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("6.3  Security Findings", s["h3"]))
    story += [
        finding_box("FINDING SEC-01 — SSL Verification Disabled in MCP Client",
            "File: agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py:195\n"
            "Code: httpx.AsyncClient(verify=False, headers={...})\n"
            "Impact: All connections from the Agent Backend to the MCP Server lack certificate "
            "validation. A man-in-the-middle attacker on the internal Docker network could intercept "
            "all tool calls and the bearer tokens they carry.\n"
            "Fix: Set verify=True. For self-signed certs in dev, pass the cert path: verify='/path/to/cert.pem'",
            "CRITICAL", s),

        finding_box("FINDING SEC-02 — Allowlist Raises Generic Exception (Not HTTP 403)",
            "File: agents/eugene-agent-ws/src/router/auth/auth.py:25\n"
            "Code: raise Exception(f'{user_name} not in allowlist!')\n"
            "Impact: FastAPI cannot convert a generic Exception to a proper HTTP 403 Forbidden "
            "response. The client receives an HTTP 500 Internal Server Error, which leaks the "
            "error message and may expose usernames in logs.\n"
            "Fix: raise HTTPException(status_code=403, detail='Access denied')",
            "HIGH", s),

        finding_box("FINDING SEC-03 — No Rate Limiting on Any Endpoint",
            "No rate limiting middleware is configured on the Core API, Agent API, or MCP Server. "
            "A single client can issue unlimited concurrent requests, enabling resource exhaustion "
            "attacks against Neo4j and the Strands agent. The agent executor has no concurrency cap.\n"
            "Fix: Add slowapi (Starlette rate limiting) with limits like 100 req/min per IP, "
            "10 concurrent agent sessions per user.", "HIGH", s),

        finding_box("FINDING SEC-04 — Token Exposed in HTML Textarea",
            "The /login endpoint in local mode renders the Eugene JWT in an HTML <textarea> for "
            "manual copy-paste. In production, the Entra ID flow also renders both tokens in "
            "HTML. This is acceptable for a developer tool but requires HTTPS enforcement in "
            "production and a Content-Security-Policy header to prevent XSS.\n"
            "Fix: Ensure HTTPS is enforced at ALB level; add CSP headers to auth endpoints.",
            "MEDIUM", s),

        finding_box("FINDING SEC-05 — No Token Revocation / Logout Endpoint",
            "There is no /logout or token revocation endpoint. Once a Eugene JWT is issued, "
            "it remains valid until its exp claim expires. If a token is compromised, there is "
            "no mechanism to invalidate it.\n"
            "Fix: Implement a token revocation list (Redis) and a /auth/logout endpoint that "
            "adds the token JTI to the blocklist.", "MEDIUM", s),

        finding_box("FINDING SEC-06 — python_repl Tool Always Loaded (Code Execution Risk)",
            "The python_repl tool from strands_tools is always included in the agent's tool list "
            "regardless of include_tools. This gives the LLM the ability to execute arbitrary "
            "Python code in the agent container. In the context of a biomedical enterprise platform, "
            "this is a significant risk if the LLM is manipulated via prompt injection.\n"
            "Fix: Make python_repl opt-in via ToolRequestEnum.PYTHON_REPL; disable in production.", "HIGH", s),
    ]
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: OBSERVABILITY
# ─────────────────────────────────────────────────────────────────────────────
def build_observability(s):
    story = section_header("07", "Observability, Monitoring & Health Checks", s, C_STEEL_BLUE)

    story.append(Paragraph(
        "Observability is the most significant operational gap in the current Eugene deployment. "
        "The platform lacks structured logging, metrics export, and distributed tracing — the "
        "three pillars required for production-grade monitoring. Without these, diagnosing "
        "'Hanging Runs' in production requires log scraping from individual containers, with "
        "no correlation across service boundaries.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    obs_pie = chart_observability_radar()
    sev_pie = chart_severity_pie()

    obs_row = Table(
        [[obs_pie, sev_pie]],
        colWidths=[10*cm, 8*cm],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                          ("LEFTPADDING",(0,0),(-1,-1),0)])
    )
    story.append(obs_row)
    story.append(Paragraph("Figure 5 & 6: Observability Maturity (Radar) and Finding Severity Distribution", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("7.1  Observability Maturity Assessment", s["h3"]))
    obs_data = [
        ["Pillar", "Current State", "Score", "Recommended Solution"],
        ["Structured Logging", "Basic Python logging — plain text to stdout", "1/10", "JSON format via python-json-logger"],
        ["Metrics Export", "ABSENT — metrics logged as text only", "0/10", "Prometheus + Grafana / CloudWatch"],
        ["Distributed Tracing", "ABSENT — no trace ID propagation", "0/10", "OpenTelemetry SDK + AWS X-Ray"],
        ["Health Checks", "Minimal — /health returns {status: OK} only", "2/10", "Dependency checks: Neo4j, MCP, LLM"],
        ["Rate Limiting", "ABSENT", "0/10", "slowapi middleware"],
        ["Error Tracking", "Basic exception logging only", "3/10", "Sentry SDK integration"],
        ["Agent Metrics", "Captured per-run, logged only — not exported", "3/10", "Emit to CloudWatch or Prometheus"],
        ["Request Correlation", "conversation_id as session key only", "3/10", "X-Trace-ID header propagation"],
        ["Log Aggregation", "stdout to Docker (destination unknown)", "2/10", "AWS CloudWatch Log Groups"],
        ["APM", "ABSENT", "0/10", "AWS X-Ray or Datadog APM"],
    ]
    story.append(styled_table(obs_data, [3.2*cm, 5*cm, 1.3*cm, 5*cm],
                              header_color=C_STEEL_BLUE, alt_color=C_BLUE_PALE, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("7.2  Recommended Observability Stack (Target State)", s["h3"]))
    target_data = [
        ["Layer", "Tool", "Purpose", "Priority"],
        ["Logging", "python-json-logger", "Structured JSON log format", "HIGH"],
        ["Log Aggregation", "AWS CloudWatch Logs", "Centralised log storage and search", "HIGH"],
        ["Metrics", "Prometheus + Grafana", "Real-time metrics dashboard", "HIGH"],
        ["Tracing", "OpenTelemetry + AWS X-Ray", "Distributed request tracing", "HIGH"],
        ["Error Tracking", "Sentry SDK", "Exception aggregation and alerting", "MEDIUM"],
        ["Agent Metrics", "CloudWatch Custom Metrics", "Token usage, tool calls, latency", "MEDIUM"],
        ["Health Checks", "Custom health endpoints", "Neo4j, MCP, LLM availability", "HIGH"],
        ["Alerting", "CloudWatch Alarms + SNS", "P95 latency, error rate alerts", "HIGH"],
    ]
    story.append(styled_table(target_data, [3*cm, 3.5*cm, 5*cm, 2*cm],
                              header_color=C_STEEL_BLUE, alt_color=C_BLUE_PALE, font_size=8))
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: GATEWAY DESIGN
# ─────────────────────────────────────────────────────────────────────────────
def build_gateway_design(s):
    story = section_header("08", "Gateway Design — MCP Tool Interface Specifications", s, C_TEAL)

    story.append(Paragraph(
        "The Gateway Design section addresses Stage 1 deliverable: defining JSON-RPC schemas "
        "for new MCP tools (PubMed, SEC/Financial) and security policies. The current "
        "architecture provides an excellent foundation — the FastMCP stateless HTTP transport "
        "and JWT middleware make adding new tools straightforward.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("8.1  New MCP Tool Specifications — PubMed Tool", s["h3"]))
    pubmed_spec = """Tool Name:   search_pubmed_articles
Description: Search PubMed Central for biomedical research articles by query terms.
             Returns article IDs, titles, authors, journal, and abstract snippets.

Input Schema (JSON-RPC):
  {
    "query": "string (required) — search terms, e.g., 'Hemophilia A gene therapy'",
    "max_results": "integer (optional, default 10, max 50)",
    "date_from": "string (optional) — YYYY/MM/DD",
    "date_to":   "string (optional) — YYYY/MM/DD",
    "article_type": "string (optional) — 'Review' | 'Clinical Trial' | 'Meta-Analysis'"
  }

Output Schema:
  {
    "count": "integer — total results",
    "articles": [
      {
        "pmid":     "string",
        "title":    "string",
        "authors":  ["string"],
        "journal":  "string",
        "year":     "integer",
        "abstract": "string (first 500 chars)"
      }
    ]
  }

Security: Bearer JWT required (same Eugene JWT as existing tools)
Rate Limit: 10 req/min per user (NCBI API rate limit compliance)
Timeout: 30 seconds"""
    story.append(Paragraph(pubmed_spec, s["code"]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("8.2  New MCP Tool Specifications — SEC Financial Intelligence Tool", s["h3"]))
    sec_spec = """Tool Name:   search_sec_filings
Description: Search SEC EDGAR for financial filings (10-K, 10-Q, 8-K) related to
             biomedical companies. Useful for M&A intelligence and deal analysis.

Input Schema (JSON-RPC):
  {
    "company_name": "string (required) — e.g., 'Biogen'",
    "cik":          "string (optional) — SEC Central Index Key",
    "form_type":    "string (optional) — '10-K' | '10-Q' | '8-K' | 'DEF 14A'",
    "date_from":    "string (optional) — YYYY-MM-DD",
    "date_to":      "string (optional) — YYYY-MM-DD",
    "max_results":  "integer (optional, default 5, max 20)"
  }

Output Schema:
  {
    "company":   "string",
    "cik":       "string",
    "filings": [
      {
        "form":        "string",
        "filed_date":  "string",
        "period":      "string",
        "description": "string",
        "filing_url":  "string"
      }
    ]
  }

Security: Bearer JWT required; additionally rate-limited to 5 req/min (SEC EDGAR fair use)
Timeout: 45 seconds"""
    story.append(Paragraph(sec_spec, s["code"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("8.3  Target State Architecture (v2.0)", s["h3"]))
    arch_data = [
        ["Component", "Current (v1.x)", "Target (v2.0)", "Change"],
        ["MCP Tool Count", "12 tools", "16+ tools: PubMed, SEC, ClinicalTrials, ChEMBL added", "Additive"],
        ["MCP Transport", "Streamable HTTP (stateless)", "Streamable HTTP + Lambda adapters for SEC/PubMed", "Additive"],
        ["Agent Routing", "Single EugeneDataAgent for all queries", "Supervisor + Specialist Agents topology", "Refactor"],
        ["LLM Provider", "Anthropic / OpenAI (switchable)", "AWS Bedrock (primary) + Anthropic (fallback)", "Change"],
        ["Session Storage", "FileSessionManager (local disk)", "DynamoDB or ElastiCache (Redis)", "Upgrade"],
        ["Vector Search", "Neo4j graph similarity", "Amazon Bedrock Knowledge Base (S3 Vectors)", "Additive"],
        ["Observability", "Basic logging only", "OpenTelemetry + CloudWatch + X-Ray", "Upgrade"],
        ["Auth", "Entra ID + Eugene JWT", "Entra ID + Eugene JWT + API Gateway authoriser", "Additive"],
        ["Rate Limiting", "None", "API Gateway throttling + slowapi middleware", "Additive"],
        ["Health Checks", "Shallow /health only", "Deep dependency checks for Neo4j, MCP, LLM", "Upgrade"],
    ]
    story.append(styled_table(arch_data, [3*cm, 3.5*cm, 6*cm, 2*cm],
                              header_color=C_TEAL, alt_color=C_TEAL_LIGHT, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("8.4  Supervisor + Specialist Agent Topology (Recommended)", s["h3"]))
    story.append(Paragraph(
        "The current architecture uses a single generalist agent (<b>EugeneDataAgent</b>) for all "
        "query types. For Stage 2, we recommend a <b>Supervisor + Specialist</b> topology where a "
        "routing agent delegates to domain-specific agents:", s["body"]
    ))
    story.append(Spacer(1, 0.1*cm))

    topo_data = [
        ["Agent", "Responsibility", "Tools", "LLM"],
        ["Supervisor Agent", "Intent classification, routing, response synthesis", "classify_intent, route_to_agent", "Claude Sonnet"],
        ["Eugene Graph Agent", "Knowledge graph queries, relationship traversal", "12 Eugene MCP tools", "Claude Sonnet"],
        ["PubMed Agent", "Literature search, citation retrieval", "search_pubmed, get_article", "GPT-4.1-mini"],
        ["SEC Agent", "Financial intelligence, M&A, filings", "search_sec, get_filing", "GPT-4.1-mini"],
        ["ClinicalTrials Agent", "Trial search, protocol analysis", "search_trials, get_protocol", "GPT-4.1-mini"],
        ["Synthesis Agent", "Cross-source result aggregation and formatting", "All read tools", "Claude Sonnet"],
    ]
    story.append(styled_table(topo_data, [3.2*cm, 5.3*cm, 4*cm, 2.5*cm],
                              header_color=C_TEAL, alt_color=C_TEAL_LIGHT, font_size=7.5))
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: AI RISK & GOVERNANCE
# ─────────────────────────────────────────────────────────────────────────────
def build_governance(s):
    story = section_header("09", "AI Risk & Governance Framework", s, C_RED)

    story.append(Paragraph(
        "The Eugene platform operates in a highly regulated biomedical context. CSL Behring "
        "is a global pharmaceutical company subject to FDA, EMA, and GDPR/HIPAA requirements. "
        "The agentic AI system must meet rigorous standards for <b>explainability</b>, "
        "<b>data lineage</b>, <b>PII/PHI protection</b>, and <b>audit traceability</b>.", s["body_justify"]
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("9.1  AI Risk Register", s["h3"]))
    risk_data = [
        ["ID", "Risk", "Like-\nlihood", "Impact", "Current Controls", "Recommended Controls"],
        ["AI-R01", "Hallucination in biomedical context", "HIGH", "CRITICAL", "None", "Citation enforcement in system prompt; fact-check tool"],
        ["AI-R02", "PII/PHI in user prompts", "MEDIUM", "HIGH", "No PII filtering", "AWS Comprehend PII detection middleware"],
        ["AI-R03", "Prompt injection via tool results", "MEDIUM", "HIGH", "None", "Input/output sanitization; sandboxed tool results"],
        ["AI-R04", "Unbounded agent cost (token spend)", "HIGH", "HIGH", "No token budget", "Max token budget per session; cost alerting"],
        ["AI-R05", "python_repl arbitrary code execution", "LOW", "CRITICAL", "Always loaded", "Remove from default tools; restrict to dev env"],
        ["AI-R06", "Model bias in drug recommendations", "MEDIUM", "HIGH", "None", "Bias evaluation framework; human review gate"],
        ["AI-R07", "Outdated graph data (stale nodes)", "MEDIUM", "MEDIUM", "Manual ingestion only", "Automated freshness scoring on nodes"],
        ["AI-R08", "Agent decision non-explainability", "HIGH", "HIGH", "Callback handler logs tool calls", "Citation trail in every response; lineage API"],
        ["AI-R09", "JWT token compromise", "LOW", "CRITICAL", "JWT expiry + HS256 validation", "Token revocation list; reduce token TTL"],
        ["AI-R10", "Regulatory non-compliance (21 CFR Part 11)", "MEDIUM", "CRITICAL", "None", "Audit log for all agent decisions; change control"],
    ]
    story.append(styled_table(risk_data,
        [1.2*cm, 3.8*cm, 1.5*cm, 1.5*cm, 3*cm, 5.5*cm],
        header_color=C_RED, alt_color=C_RED_LIGHT, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("9.2  Explainability & Lineage Requirements", s["h3"]))
    story += bullet_list([
        "<b>Citation Enforcement:</b> Every agent response must include the source nodes, relationship types, and tool calls used to derive the answer. Modify the system prompt to require: 'Always cite the Eugene node IDs and data sources used in your answer.'",
        "<b>Tool Call Audit Log:</b> Log every MCP tool invocation (tool name, parameters, response size, latency, user UPN, conversation_id) to an immutable audit table (DynamoDB or S3).",
        "<b>Decision Lineage API:</b> Expose a /agent/conversation/{id}/lineage endpoint that returns the full tool call chain for any conversation, enabling post-hoc audit.",
        "<b>Data Freshness:</b> Add a last_updated timestamp to each Neo4j node. Surface this in API responses and agent context so the LLM can qualify answers with data recency.",
        "<b>Response Confidence:</b> Implement a confidence scoring system based on graph path length (shorter = higher confidence) and node source reliability.",
    ], s)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("9.3  PII/PHI Boundary Controls", s["h3"]))
    pii_data = [
        ["Data Category", "PII/PHI Risk", "Current Control", "Required Control"],
        ["User prompts (free text)", "HIGH — may contain patient info", "None", "AWS Comprehend PII detection; block or redact before LLM"],
        ["Agent responses", "MEDIUM — may reference clinical data", "None", "Output scanning; redact before returning to UI"],
        ["Conversation history (FileSession)", "MEDIUM — stored on disk", "None", "Encrypt at rest; auto-expire sessions after 24h"],
        ["JWT tokens (upn field)", "LOW — email address only", "HTTPS in transit", "Avoid logging upn in plain text"],
        ["Neo4j node data", "LOW — de-identified biomedical", "Access control via JWT", "Regular data audits; no patient-level data"],
        ["LLM API calls (Anthropic/OpenAI)", "HIGH — data leaves CSL network", "None", "Use AWS Bedrock (data stays in AWS); sign DPA with Anthropic/OpenAI"],
    ]
    story.append(styled_table(pii_data, [3.5*cm, 3*cm, 2.8*cm, 7.2*cm],
                              header_color=C_RED, alt_color=C_RED_LIGHT, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("9.4  Tool-Level Permission Matrix", s["h3"]))
    perm_data = [
        ["Tool", "Read?", "Write?", "Delete?", "PII Risk", "Prod-Safe?"],
        ["fetch_node_relationships", "YES", "NO", "NO", "LOW", "YES"],
        ["lookup_node_by_value", "YES", "NO", "NO", "LOW", "YES"],
        ["fetch_facts", "YES", "NO", "NO", "LOW", "YES"],
        ["fetch_drug_aliases", "YES", "NO", "NO", "LOW", "YES"],
        ["find_organization_assets", "YES", "NO", "NO", "LOW", "YES"],
        ["http_request (opt-in)", "YES", "YES", "YES", "HIGH", "NO — restrict"],
        ["python_repl (default — risk!)", "YES", "YES", "YES", "CRITICAL", "NO — disable"],
        ["calculator", "Compute only", "NO", "NO", "NONE", "YES"],
        ["current_time", "YES", "NO", "NO", "NONE", "YES"],
        ["search_pubmed (proposed)", "YES", "NO", "NO", "LOW", "YES"],
        ["search_sec (proposed)", "YES", "NO", "NO", "LOW", "YES"],
    ]
    story.append(styled_table(perm_data, [4.5*cm, 1.4*cm, 1.4*cm, 1.4*cm, 2*cm, 2.8*cm],
                              header_color=C_RED, alt_color=C_RED_LIGHT, font_size=7))
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10: RECOMMENDATIONS & ROADMAP
# ─────────────────────────────────────────────────────────────────────────────
def build_recommendations(s):
    story = section_header("10", "Recommendations & Remediation Roadmap", s, C_GREEN)

    story.append(Paragraph("10.1  Prioritised Finding Summary", s["h3"]))
    all_findings = [
        ["ID", "Finding", "Severity", "Effort", "Impact"],
        ["SEC-01", "SSL verification disabled in MCP client (verify=False)", "CRITICAL", "0.5 day", "Eliminates MITM risk"],
        ["AGT-01", "Shared SlidingWindowConversationManager — race condition", "CRITICAL", "1 day", "Fixes concurrent session corruption"],
        ["AGT-02", "Unbounded ReAct loop — no max_iterations", "HIGH", "0.5 day", "Eliminates infinite agent loops"],
        ["AGT-03", "No agent execution timeout (asyncio.wait_for missing)", "HIGH", "0.5 day", "Prevents hung streaming connections"],
        ["AGT-04", "Anthropic client has no timeout configured", "HIGH", "0.5 day", "Prevents LLM API hang"],
        ["AGT-05", "python_repl always loaded — arbitrary code execution risk", "HIGH", "0.5 day", "Reduces attack surface"],
        ["SEC-02", "Allowlist raises generic Exception (not HTTPException 403)", "HIGH", "0.5 day", "Correct HTTP error codes"],
        ["SEC-03", "No rate limiting on any endpoint", "HIGH", "2 days", "Prevents DoS/resource exhaustion"],
        ["DB-01", "No Neo4j query timeout configured", "HIGH", "1 day", "Prevents adapter thread blocks"],
        ["DB-02", "No explicit connection pool sizing", "MEDIUM", "0.5 day", "Supports concurrent load"],
        ["OBS-01", "No structured (JSON) logging", "HIGH", "2 days", "Enables log aggregation"],
        ["OBS-02", "No metrics export (Prometheus/CloudWatch)", "HIGH", "3 days", "Production visibility"],
        ["OBS-03", "No distributed tracing (OpenTelemetry)", "HIGH", "5 days", "Cross-service debugging"],
        ["OBS-04", "Shallow /health endpoints (no dependency checks)", "HIGH", "1 day", "Accurate service health"],
        ["SEC-04", "No token revocation mechanism", "MEDIUM", "3 days", "Invalidate compromised tokens"],
        ["SEC-05", "PII/PHI not filtered in prompts or responses", "HIGH", "5 days", "Regulatory compliance"],
        ["DB-03", "Deep pagination — no OFFSET limit validation", "MEDIUM", "0.5 day", "Prevents slow deep-page queries"],
        ["AGT-06", "FileSessionManager — no recovery or cleanup", "MEDIUM", "2 days", "Prevents disk exhaustion"],
        ["GRAPH-01", "No graph statistics dashboard endpoint", "MEDIUM", "1 day", "Operational visibility"],
        ["GRAPH-02", "Graph data freshness not tracked", "MEDIUM", "2 days", "Data quality assurance"],
    ]
    story.append(styled_table(all_findings, [1.5*cm, 7*cm, 2*cm, 1.5*cm, 3.5*cm],
                              header_color=C_GREEN, alt_color=C_GREEN_LIGHT, font_size=7))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("10.2  Remediation Roadmap (Gantt)", s["h3"]))
    story.append(chart_remediation_roadmap())
    story.append(Paragraph("Figure 7: Prioritised Remediation Gantt Chart (8 Weeks)", s["caption"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("10.3  Architecture Strengths (Positive Findings)", s["h3"]))
    story += [
        finding_box("POSITIVE: Clean DDD + Hexagonal Architecture",
            "The Core API follows Domain-Driven Design with hexagonal (ports-and-adapters) "
            "architecture. Each domain (foundation, drug, organization, TPP) has its own "
            "router/provider/adapter/mapper/model layers. Manual DI via conf.py factory functions "
            "keeps dependencies explicit and testable.", "POSITIVE", s),
        finding_box("POSITIVE: Comprehensive Knowledge Graph Ontology",
            "44 node types and 31 relationship types covering biomedical, clinical trial, patent, "
            "organization, and publication domains. The graph integrates USPTO, PubMed, "
            "ClinicalTrials.gov, and internal CSL TPP data — a rare and valuable asset.", "POSITIVE", s),
        finding_box("POSITIVE: Dual LLM Provider with Auto-Detection",
            "The agent framework seamlessly switches between Anthropic Claude and OpenAI GPT "
            "based on available API keys. This provides resilience against single provider "
            "outages and enables cost optimisation.", "POSITIVE", s),
        finding_box("POSITIVE: Stateless MCP Server Design",
            "FastMCP with stateless_http=True enables horizontal scaling of the MCP server "
            "without sticky sessions. Each tool call is independently authenticated and executed. "
            "This is the correct design for a cloud-native deployment.", "POSITIVE", s),
        finding_box("POSITIVE: Streaming SSE Architecture",
            "The Agent Backend uses Server-Sent Events (text/event-stream) for real-time "
            "response streaming. The UI renders tokens as they arrive, providing a ChatGPT-like "
            "experience for long-running biomedical queries.", "POSITIVE", s),
        finding_box("POSITIVE: Parameterised Cypher Queries",
            "All Neo4j adapters use parameterised Cypher queries (no string concatenation), "
            "completely preventing Cypher injection attacks. The MAX_SUPPORTED_HOPS=2 constraint "
            "is a pragmatic and necessary guard against graph explosion.", "POSITIVE", s),
    ]
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11: APPENDIX
# ─────────────────────────────────────────────────────────────────────────────
def build_appendix(s):
    story = section_header("APP", "Appendix — Environment Variables & File Reference", s, C_GRAY_MID)

    story.append(Paragraph("A.1  Key Environment Variables by Service", s["h3"]))
    env_data = [
        ["Variable", "Service", "Required?", "Description"],
        ["NEO4J_URI", "eugene_ws", "YES", "bolt://neo4j:7687"],
        ["NEO4J_USERNAME", "eugene_ws", "YES", "Database user"],
        ["NEO4J_PASSWORD", "eugene_ws", "YES", "Database password"],
        ["ENTRA_CLIENT_ID", "eugene_ws", "YES (prod)", "Azure AD app ID"],
        ["ENTRA_CLIENT_SECRET", "eugene_ws", "YES (prod)", "Azure AD secret"],
        ["ENTRA_TENANT_ID", "eugene_ws", "YES (prod)", "Azure AD tenant GUID"],
        ["ENVIRONMENT", "eugene_ws + agent_ws", "YES", "'local' | 'prod'"],
        ["EUGENE_API_BASE", "eugene_mcp", "YES", "http://eugene_ws:8000"],
        ["EUGENE_MCP_SERVER_URL", "agent_ws", "YES", "http://eugene_mcp:8000/mcp"],
        ["ANTHROPIC_API_KEY", "agent_ws", "COND.", "Required if LLM_PROVIDER=anthropic"],
        ["ANTHROPIC_MODEL_ID", "agent_ws", "NO", "Default: claude-sonnet-4-20250514"],
        ["OPENAI_API_KEY", "agent_ws", "COND.", "Required if LLM_PROVIDER=openai"],
        ["OPENAI_MODEL_ID", "agent_ws", "NO", "Default: gpt-4.1-mini"],
        ["LLM_PROVIDER", "agent_ws", "NO", "'anthropic' | 'openai' (auto-detected)"],
        ["EUGENE_AGENT_ALLOWLIST", "agent_ws", "YES", "Pipe-separated user UPN list"],
        ["EUGENE_AGENT_API_URL", "agent_ui", "YES", "http://eugene_agent_ws:8000/agent/api/..."],
    ]
    story.append(styled_table(env_data, [4*cm, 2.5*cm, 2*cm, 7*cm],
                              header_color=C_GRAY_MID, font_size=7.5))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("A.2  Key File Reference", s["h3"]))
    file_data = [
        ["File", "Purpose", "Risk Level"],
        ["agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py", "Core agent logic, ReAct loop, MCP client", "CRITICAL"],
        ["agents/eugene-agent-ws/src/query/conf/conf.py", "LLM provider factory, agent factory", "HIGH"],
        ["agents/eugene-agent-ws/src/router/auth/auth.py", "JWT validation, allowlist enforcement", "HIGH"],
        ["agents/eugene-mcp/src/eugene_mcp.py", "MCP server, tool registration, auth", "HIGH"],
        ["agents/eugene-mcp/src/auth/verifier.py", "FastMCP JWT verifier configuration", "HIGH"],
        ["src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py", "N-hop Cypher queries, MAX_HOPS=2", "HIGH"],
        ["src/graph/infra/db/graph_db_connection_factory.py", "Neo4j driver singleton, connection pool", "MEDIUM"],
        ["src/foundation/infra/db/util/pagination.py", "LIMIT/OFFSET calculation", "MEDIUM"],
        ["src/annotation/timer_annotation.py", "Performance timing decorator", "LOW"],
        ["docker-compose.yml", "Service topology, port mapping, env vars", "CONFIG"],
        ["docker.env", "Secrets — DO NOT commit to git", "SENSITIVE"],
    ]
    story.append(styled_table(file_data, [7.5*cm, 5*cm, 2*cm],
                              header_color=C_GRAY_MID, font_size=7.5))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("A.3  Stage 1 Deliverable Completion Status", s["h3"]))
    completion_data = [
        ["Deliverable", "Status", "Location in Report"],
        ["Inception & Audit Report", "COMPLETE", "Sections 01-10"],
        ["Runtime mapping — bottom-up path tracing", "COMPLETE (code-review basis)", "Section 02, 04"],
        ["Latency hot-spots", "COMPLETE (estimated — no AWS access)", "Section 05"],
        ["State sync gaps", "COMPLETE", "Section 04.2 (Root Causes)"],
        ["Quantified baselines (P50/P95)", "PARTIAL — AWS access required for live data", "Section 05.1"],
        ["Code and observability review", "COMPLETE", "Sections 07"],
        ["Analyze Strands code — root causes of Hanging Runs", "COMPLETE", "Section 04.2"],
        ["Eugene KG assessment — architecture diagrams", "COMPLETE", "Sections 02, 03"],
        ["Ontology (trial, indication, endpoint, asset, cohort)", "COMPLETE", "Section 03"],
        ["Node/edge volumes", "PARTIAL — 44 node types / 31 rel. types identified", "Section 03"],
        ["Typical query patterns", "COMPLETE", "Section 03.3"],
        ["Existing GraphRAG patterns", "COMPLETE", "Sections 03, 08"],
        ["Graph traversal logic", "COMPLETE", "Sections 03.3, 05"],
        ["Gateway Design — JSON-RPC MCP Tool schemas", "COMPLETE", "Section 08"],
        ["Map Knowledge Graph schema to Agent intents", "COMPLETE", "Section 08.4"],
        ["AI Risk & Governance — agent topology + guardrails", "COMPLETE", "Section 09"],
        ["Explainability, lineage, PII/PHI, tool permissions", "COMPLETE", "Sections 09.2, 09.3, 09.4"],
    ]
    story.append(styled_table(completion_data, [6*cm, 3.5*cm, 5.5*cm],
                              header_color=C_DEEP_BLUE, alt_color=C_BLUE_PALE, font_size=7.5))
    return story


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_report():
    os.makedirs("docs", exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.8*cm,
        bottomMargin=1.5*cm,
        title="Eugene Platform Stage 1 Assessment Report",
        author="Rajesh Gupta | AI Semantic Expert",
        subject="Eugene Knowledge Graph — Production Readiness Audit",
    )

    s = build_styles()
    story = []

    print("Building cover page...")
    story += build_cover(s)

    print("Building executive summary...")
    story += build_exec_summary(s)

    print("Building architecture section...")
    story += build_architecture(s)

    print("Building ontology section...")
    story += build_ontology(s)

    print("Building agent analysis section...")
    story += build_agent_analysis(s)

    print("Building latency section...")
    story += build_latency(s)

    print("Building security section...")
    story += build_security(s)

    print("Building observability section...")
    story += build_observability(s)

    print("Building gateway design section...")
    story += build_gateway_design(s)

    print("Building governance section...")
    story += build_governance(s)

    print("Building recommendations section...")
    story += build_recommendations(s)

    print("Building appendix...")
    story += build_appendix(s)

    print(f"Generating PDF: {OUTPUT_PATH}")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Done! Report saved to: {OUTPUT_PATH}")
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    build_report()
