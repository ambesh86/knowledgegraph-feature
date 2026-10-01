"""
CSL Behring — Eugene Platform Stakeholder Reports (Book-Format Edition)
========================================================================
Generates four deliverables (two book-format documents in two formats each):

  1. EUGENE_PROJECT_EVALUATION.pdf       /  .docx
  2. EUGENE_TECHNICAL_RECOMMENDATIONS.pdf /  .docx

Content lives in csl_book_content_doc1.py and csl_book_content_doc2.py.
This module is a renderer that walks a flat sequence of typed flowables
(PART / CHAPTER / SECTION / SUBSEC / PARA / BULLETS / TABLE / DIAGRAM /
FINDINGS_TABLE / POSITIVES_TABLE / CALLOUT / CODE / QUOTE / PAGEBREAK)
and emits both a PDF (ReportLab) and a DOCX (python-docx).

Run:  python3 generate_csl_reports.py
"""
from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

# ───────────────────────────── ReportLab ─────────────────────────────
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image as RLImage, KeepTogether, NextPageTemplate,
)
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import (
    Drawing, Rect, String, Line, Polygon, Circle,
)
from reportlab.graphics import renderPM, renderPDF

# ─────────────────────────────── python-docx ─────────────────────────
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ─────────────────────────────── Content ─────────────────────────────
from csl_book_content_doc1 import (
    DOC1_TITLE, DOC1_SUBTITLE, DOC1_FILE_PDF, DOC1_FILE_DOCX, DOC1_BOOK,
)
from csl_book_content_doc2 import (
    DOC2_TITLE, DOC2_SUBTITLE, DOC2_FILE_PDF, DOC2_FILE_DOCX, DOC2_BOOK,
)

# ════════════════════════════════════════════════════════════════════════
# BRAND COLOURS — CSL Behring corporate palette
# ════════════════════════════════════════════════════════════════════════
CSL_RED        = colors.HexColor("#A6192E")
CSL_RED_DARK   = colors.HexColor("#7A1222")
CSL_RED_LIGHT  = colors.HexColor("#FBEAEC")
DEEP_BLUE      = colors.HexColor("#1B3A6B")
STEEL_BLUE     = colors.HexColor("#2E6DA4")
TEAL           = colors.HexColor("#00897B")
TEAL_LIGHT     = colors.HexColor("#E0F2F1")
ORANGE         = colors.HexColor("#E65100")
ORANGE_LIGHT   = colors.HexColor("#FFF3E0")
PURPLE         = colors.HexColor("#4A148C")
PURPLE_LIGHT   = colors.HexColor("#F3E5F5")
GREEN          = colors.HexColor("#1B5E20")
GREEN_LIGHT    = colors.HexColor("#E8F5E9")
GRAY_LIGHT     = colors.HexColor("#F5F5F5")
GRAY_MID       = colors.HexColor("#9E9E9E")
GRAY_DARK      = colors.HexColor("#424242")
BLUE_PALE      = colors.HexColor("#E3F2FD")
WHITE          = colors.white
BLACK          = colors.black

# DOCX colour equivalents
DOCX_CSL_RED    = RGBColor(0xA6, 0x19, 0x2E)
DOCX_DEEP_BLUE  = RGBColor(0x1B, 0x3A, 0x6B)
DOCX_STEEL_BLUE = RGBColor(0x2E, 0x6D, 0xA4)
DOCX_TEAL       = RGBColor(0x00, 0x89, 0x7B)
DOCX_BLACK      = RGBColor(0x00, 0x00, 0x00)
DOCX_GRAY       = RGBColor(0x42, 0x42, 0x42)
DOCX_WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
DOCX_GREEN      = RGBColor(0x1B, 0x5E, 0x20)
DOCX_ORANGE     = RGBColor(0xE6, 0x51, 0x00)
DOCX_PURPLE     = RGBColor(0x4A, 0x14, 0x8C)

W, H = A4
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
# Document creation date — fixed per programme governance.
TODAY = "May 2, 2026"


# ════════════════════════════════════════════════════════════════════════
# FINDINGS DATA (used by FINDINGS_TABLE flowable in both docs)
# ════════════════════════════════════════════════════════════════════════
FINDINGS = {
    "CRITICAL": [
        ("SEC-01", "SSL verification disabled in MCP client",
         "verify=False on httpx; service-to-service traffic vulnerable to MITM.",
         "Set verify=True; pass cert path for self-signed dev certs.", "0.5 day"),
        ("AGT-01", "Shared SlidingWindowConversationManager — race condition",
         "Single manager shared across agent instances corrupts concurrent sessions.",
         "Instantiate the manager per conversation, not per service.", "1 day"),
    ],
    "HIGH": [
        ("AGT-02", "Unbounded ReAct loop",
         "No max_iterations on agent; can cycle indefinitely on tool calls.",
         "Set max_iterations=25 in Agent constructor.", "0.5 day"),
        ("AGT-03", "No agent execution timeout",
         "Streaming connections held until client times out (~120s).",
         "Wrap stream_async() in asyncio.wait_for(timeout=300).", "0.5 day"),
        ("AGT-04", "Anthropic LLM client timeout not configured",
         "OpenAI client has 60s timeout; Anthropic has none.",
         "Pass timeout=60.0 to the Anthropic model configuration.", "0.5 day"),
        ("AGT-05", "python_repl tool always loaded",
         "LLM has access to arbitrary code execution by default.",
         "Make python_repl opt-in; disable in production.", "0.5 day"),
        ("SEC-02", "Allowlist raises generic Exception",
         "Causes HTTP 500 instead of 403; leaks stack to clients.",
         "Raise HTTPException(status_code=403, detail='Access denied').", "0.5 day"),
        ("SEC-03", "No rate limiting on any endpoint",
         "Unlimited concurrent requests; DoS / cost exposure.",
         "Add slowapi: 100 req/min per IP; 10 sessions per user.", "2 days"),
        ("DB-01", "No Neo4j query timeout",
         "Driver initialised without socket_keepalive or transaction timeout.",
         "Set connection_timeout=30 and max_transaction_retry_time=30.", "1 day"),
        ("OBS-01", "No structured JSON logging",
         "Plain-text logging incompatible with CloudWatch Logs Insights.",
         "Adopt python-json-logger across all services.", "2 days"),
        ("OBS-02", "No metrics export",
         "No Prometheus or CloudWatch metrics for application signals.",
         "Add Prometheus client + scrape config; or CloudWatch EMF.", "3 days"),
        ("OBS-03", "No distributed tracing",
         "No correlation across services; cross-service debugging is forensic.",
         "Integrate OpenTelemetry SDK + AWS X-Ray exporter.", "5 days"),
        ("OBS-04", "Shallow /health endpoints",
         "Returns OK without checking dependencies.",
         "Add deep checks for Neo4j, MCP, LLM availability.", "1 day"),
    ],
    "MEDIUM": [
        ("SEC-04", "No token revocation",
         "No /logout; compromised JWT remains valid until exp.",
         "Redis-backed denylist; expose /auth/logout endpoint.", "3 days"),
        ("SEC-05", "PII / PHI not filtered",
         "No redaction in prompts or responses; regulatory risk.",
         "AWS Comprehend PII detection middleware on prompts and responses.", "5 days"),
        ("DB-02", "No explicit Neo4j connection-pool sizing",
         "Pool defaults limit concurrent throughput.",
         "Tune pool_size against load tests.", "0.5 day"),
        ("DB-03", "No deep-pagination offset cap",
         "Unbounded OFFSET enables slow scans.",
         "Reject OFFSET > 100,000 in pagination utility.", "0.5 day"),
        ("AGT-06", "FileSessionManager — no recovery, no cleanup",
         "Disk-based sessions; concurrent writes contend; no purge.",
         "fcntl locking now; migrate to DynamoDB / Redis.", "2 days"),
        ("GRAPH-01", "No graph statistics dashboard",
         "Node / edge counts and growth rate not surfaced.",
         "Add /stats/graph endpoint and a small dashboard.", "1 day"),
        ("GRAPH-02", "Graph data freshness not tracked",
         "No last_updated on nodes; staleness not detectable.",
         "Add last_updated property; expose in /stats.", "2 days"),
    ],
}

POSITIVES = [
    ("Clean DDD + Hexagonal Architecture",
     "Domain-driven layering with explicit ports and adapters; testable, swappable, well-named."),
    ("Comprehensive Knowledge Graph Ontology",
     "Forty-four node types and thirty-one relationship types unify USPTO, PubMed, trials, drugs, deals."),
    ("Dual LLM Provider with Auto-Detect",
     "Anthropic / OpenAI hot-swap on a single env switch; resilience and cost flexibility."),
    ("Stateless MCP Server",
     "FastMCP with stateless_http=True; trivially horizontally scalable."),
    ("Streaming SSE Architecture",
     "Token-by-token UX; first-token latency drives perceived speed."),
    ("Parameterised Cypher; Two-Hop Cap",
     "No injection risk; bounded query cost prevents pathological queries."),
]


# ════════════════════════════════════════════════════════════════════════
# GRAPHICS — CSL logo + diagrams
# ════════════════════════════════════════════════════════════════════════
def csl_logo_drawing(width=2.4 * cm, height=0.95 * cm):
    """Top-left CSL Behring logo block: red square with CSL + wordmark."""
    d = Drawing(width, height)
    d.add(Rect(0, 0, height, height, fillColor=CSL_RED, strokeColor=None))
    d.add(String(height / 2, height * 0.30, "CSL",
                 fontName="Helvetica-Bold", fontSize=11,
                 textAnchor="middle", fillColor=WHITE))
    d.add(String(height + 4, height * 0.55, "CSL Behring",
                 fontName="Helvetica-Bold", fontSize=8.5, fillColor=CSL_RED))
    d.add(String(height + 4, height * 0.18, "Biotechnology Leader",
                 fontName="Helvetica", fontSize=5.5, fillColor=GRAY_DARK))
    return d


def render_drawing_to_png_bytes(drawing, dpi=200):
    buf = BytesIO()
    renderPM.drawToFile(drawing, buf, fmt="PNG", dpi=dpi)
    buf.seek(0)
    return buf.getvalue()


def architecture_diagram(width=18 * cm, height=11 * cm):
    """Eugene high-level architecture — LR layout matching the developer guide's
    mermaid flowchart: 3 subgraphs (What the user sees / AI Layer / Data Layer)."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "Eugene Platform — High-Level Architecture",
                 fontName="Helvetica-Bold", fontSize=11,
                 textAnchor="middle", fillColor=DEEP_BLUE))
    d.add(String(width / 2, height - 0.85 * cm,
                 "(per docs/DEVELOPER_GUIDE.md — flowchart LR)",
                 fontName="Helvetica-Oblique", fontSize=8,
                 textAnchor="middle", fillColor=GRAY_DARK))

    # Three subgraph rectangles (LR layout)
    sub_h     = 7.5 * cm
    sub_top_y = 1.5 * cm
    sub1_x, sub1_w = 0.5 * cm,  4.6 * cm    # "What the user sees"
    sub2_x, sub2_w = 6.0 * cm,  5.5 * cm    # "AI Layer"
    sub3_x, sub3_w = 12.5 * cm, 5.0 * cm    # "Data Layer"

    def subgraph(x, w, title, fill_bg, fill_border):
        d.add(Rect(x, sub_top_y, w, sub_h, fillColor=fill_bg,
                   strokeColor=fill_border, strokeWidth=1.4,
                   strokeDashArray=[4, 3]))
        d.add(String(x + w / 2, sub_top_y + sub_h - 0.5 * cm, title,
                     fontName="Helvetica-Bold", fontSize=9.5,
                     textAnchor="middle", fillColor=fill_border))

    subgraph(sub1_x, sub1_w, "What the user sees", CSL_RED_LIGHT, CSL_RED)
    subgraph(sub2_x, sub2_w, "AI Layer",            ORANGE_LIGHT,  ORANGE)
    subgraph(sub3_x, sub3_w, "Data Layer",          TEAL_LIGHT,    TEAL)

    # ---- Component nodes ----
    def comp_box(x, y, w, h, lines, color):
        d.add(Rect(x, y, w, h, fillColor=WHITE, strokeColor=color,
                   strokeWidth=1.6))
        # Header strip
        d.add(Rect(x, y + h - 0.55 * cm, w, 0.55 * cm,
                   fillColor=color, strokeColor=color))
        d.add(String(x + w / 2, y + h - 0.38 * cm, lines[0],
                     fontName="Helvetica-Bold", fontSize=10,
                     textAnchor="middle", fillColor=WHITE))
        # Body lines
        for i, line in enumerate(lines[1:]):
            d.add(String(x + w / 2,
                         y + h - 0.95 * cm - i * 0.42 * cm, line,
                         fontName="Helvetica" if i > 0 else "Helvetica-Oblique",
                         fontSize=8 if i > 0 else 8.5,
                         textAnchor="middle", fillColor=GRAY_DARK))

    # UI box (subgraph 1)
    ui_x, ui_y, ui_w, ui_h = sub1_x + 0.4 * cm, sub_top_y + 2.5 * cm, sub1_w - 0.8 * cm, 3.3 * cm
    comp_box(ui_x, ui_y, ui_w, ui_h, [
        "Chat UI",
        "Streamlit",
        "Port 8501",
        "(token in sidebar,",
        "live SSE stream)",
    ], CSL_RED)

    # AGENT box (subgraph 2 — top)
    ag_x = sub2_x + 0.4 * cm
    ag_w = sub2_w - 0.8 * cm
    ag_h = 2.6 * cm
    ag_y = sub_top_y + sub_h - 1.1 * cm - ag_h
    comp_box(ag_x, ag_y, ag_w, ag_h, [
        "Agent Backend",
        "FastAPI + Strands",
        "Port 8001  •  GPT / Claude",
    ], ORANGE)

    # MCP box (subgraph 2 — bottom). Leave ~1.4 cm of clear space between
    # Agent bottom and MCP top so the arrow + label pill don't overlap.
    mcp_h = 2.2 * cm
    mcp_y = sub_top_y + 0.5 * cm
    comp_box(ag_x, mcp_y, ag_w, mcp_h, [
        "MCP Tool Server",
        "FastMCP",
        "Port 8443  •  12 tools",
    ], PURPLE)

    # API box (subgraph 3 — top)
    api_x = sub3_x + 0.4 * cm
    api_w = sub3_w - 0.8 * cm
    api_h = 2.6 * cm
    api_y = sub_top_y + sub_h - 1.1 * cm - api_h
    comp_box(api_x, api_y, api_w, api_h, [
        "Core API",
        "FastAPI",
        "Port 8000  •  20 endpoints",
    ], STEEL_BLUE)

    # DB cylinder (subgraph 3 — bottom).  Lower it to leave clear gap above.
    db_x = sub3_x + 1.0 * cm
    db_w = sub3_w - 2.0 * cm
    db_h = 2.0 * cm
    db_y = sub_top_y + 0.5 * cm
    # cylinder body
    d.add(Rect(db_x, db_y + 0.3 * cm, db_w, db_h - 0.6 * cm,
               fillColor=TEAL, strokeColor=TEAL))
    d.add(Polygon([db_x, db_y + db_h - 0.3 * cm,
                   db_x + db_w / 2, db_y + db_h,
                   db_x + db_w, db_y + db_h - 0.3 * cm,
                   db_x + db_w / 2, db_y + db_h - 0.6 * cm],
                  fillColor=TEAL_LIGHT, strokeColor=TEAL))
    d.add(Polygon([db_x, db_y + 0.3 * cm,
                   db_x + db_w / 2, db_y,
                   db_x + db_w, db_y + 0.3 * cm,
                   db_x + db_w / 2, db_y + 0.6 * cm],
                  fillColor=TEAL, strokeColor=TEAL))
    d.add(String(db_x + db_w / 2, db_y + db_h / 2 + 4, "Neo4j",
                 fontName="Helvetica-Bold", fontSize=11,
                 textAnchor="middle", fillColor=WHITE))
    d.add(String(db_x + db_w / 2, db_y + db_h / 2 - 8, "Graph Database",
                 fontName="Helvetica", fontSize=8,
                 textAnchor="middle", fillColor=WHITE))
    d.add(String(db_x + db_w / 2, db_y + db_h / 2 - 20, "Port 7687",
                 fontName="Helvetica", fontSize=7.5,
                 textAnchor="middle", fillColor=BLUE_PALE))

    # ---- Connecting arrows ----
    def labelled_arrow(x1, y1, x2, y2, label, color=GRAY_DARK):
        d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.5))
        # arrowhead
        import math
        dx, dy = x2 - x1, y2 - y1
        ll = math.hypot(dx, dy) or 1
        ux, uy = dx / ll, dy / ll
        d.add(Polygon([x2, y2,
                       x2 - ux * 9 + uy * 5,
                       y2 - uy * 9 - ux * 5,
                       x2 - ux * 9 - uy * 5,
                       y2 - uy * 9 + ux * 5],
                      fillColor=color, strokeColor=color))
        # Label background pill
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        text_w = len(label) * 4.6 + 8
        d.add(Rect(mx - text_w / 2, my - 7, text_w, 14,
                   fillColor=WHITE, strokeColor=color, strokeWidth=0.6))
        d.add(String(mx, my - 3, label,
                     fontName="Helvetica-Bold", fontSize=7,
                     textAnchor="middle", fillColor=color))

    # UI -> AGENT
    labelled_arrow(ui_x + ui_w, ui_y + ui_h / 2,
                   ag_x, ag_y + ag_h / 2,
                   "HTTP + JWT", color=ORANGE)
    # AGENT -> MCP (down within subgraph 2)
    labelled_arrow(ag_x + ag_w / 2, ag_y,
                   ag_x + ag_w / 2, mcp_y + mcp_h,
                   "MCP protocol", color=PURPLE)
    # MCP -> API
    labelled_arrow(ag_x + ag_w, mcp_y + mcp_h / 2,
                   api_x, api_y + 0.4 * cm,
                   "HTTP + JWT", color=STEEL_BLUE)
    # API -> DB (down within subgraph 3)
    labelled_arrow(api_x + api_w / 2, api_y,
                   db_x + db_w / 2, db_y + db_h - 0.1 * cm,
                   "Bolt", color=TEAL)
    return d


def sequence_diagram(width=17 * cm, height=14 * cm):
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "End-to-End Query Sequence — User question to streamed answer",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    actors = [
        ("User", CSL_RED), ("UI", CSL_RED), ("Agent", ORANGE),
        ("MCP", PURPLE),  ("Core API", STEEL_BLUE),
        ("Neo4j", TEAL), ("LLM", GREEN),
    ]
    n = len(actors)
    margin_x = 0.8 * cm
    span_x = (width - 2 * margin_x) / (n - 1)
    top_y = height - 1.5 * cm
    bottom_y = 0.6 * cm

    actor_x = []
    for i, (name, col) in enumerate(actors):
        x = margin_x + i * span_x
        actor_x.append(x)
        d.add(Rect(x - 0.95 * cm, top_y - 0.35 * cm, 1.9 * cm, 0.7 * cm,
                   fillColor=col, strokeColor=col))
        d.add(String(x, top_y - 0.05 * cm, name,
                     fontName="Helvetica-Bold", fontSize=8.5,
                     textAnchor="middle", fillColor=WHITE))
        d.add(Line(x, top_y - 0.45 * cm, x, bottom_y,
                   strokeColor=GRAY_MID, strokeWidth=0.5,
                   strokeDashArray=[2, 2]))

    def arrow(from_idx, to_idx, label, y, dashed=False, color=BLACK):
        x1, x2 = actor_x[from_idx], actor_x[to_idx]
        dash = [3, 2] if dashed else None
        d.add(Line(x1, y, x2, y, strokeColor=color, strokeWidth=0.9,
                   strokeDashArray=dash))
        head_dir = 1 if x2 > x1 else -1
        d.add(Polygon([x2, y, x2 - head_dir * 5, y + 3, x2 - head_dir * 5, y - 3],
                      fillColor=color, strokeColor=color))
        mid = (x1 + x2) / 2
        d.add(String(mid, y + 4, label, fontName="Helvetica", fontSize=6.5,
                     textAnchor="middle", fillColor=GRAY_DARK))

    steps = [
        (0, 1, "1. Types question", False, BLACK),
        (1, 2, "2. POST /agent/api/query/stream  +  JWT", False, BLACK),
        (2, 6, "3. ReAct: think -> tool plan", True, GREEN),
        (2, 3, "4. tool: lookup_node_by_value('Hemophilia A')", False, BLACK),
        (3, 4, "5. GET /node/find/...   +  Bearer JWT", False, BLACK),
        (4, 5, "6. Cypher MATCH (n)... RETURN id", False, BLACK),
        (5, 4, "7. node_id 'abc123'", True, BLACK),
        (4, 3, "8. JSON {node_id, labels}", True, BLACK),
        (3, 2, "9. tool result -> agent", True, BLACK),
        (2, 3, "10. tool: fetch_node_relationships(2-hop)", False, BLACK),
        (3, 4, "11. GET /graph/relationship/start/...", False, BLACK),
        (4, 5, "12. Cypher 2-hop traversal", False, BLACK),
        (5, 4, "13. 47 triples", True, BLACK),
        (4, 2, "14. JSON triples (via MCP)", True, BLACK),
        (2, 6, "15. Synthesise answer (stream tokens)", False, GREEN),
        (2, 1, "16. SSE: text/event-stream chunks", True, BLACK),
        (1, 0, "17. UI renders live tokens", True, BLACK),
    ]
    avail = top_y - 0.7 * cm - bottom_y - 0.1 * cm
    step_dy = avail / (len(steps) + 0.5)
    for i, (a, b, lab, dashed, color) in enumerate(steps):
        y = top_y - 0.9 * cm - (i + 1) * step_dy
        arrow(a, b, lab, y, dashed=dashed, color=color)
    return d


def nextgen_diagram(width=17 * cm, height=11.5 * cm):
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "CSL Next-Generation Agentic Platform (Target State)",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    # Persona band
    d.add(Rect(0.5 * cm, height - 1.5 * cm, width - 1 * cm, 0.7 * cm,
               fillColor=CSL_RED_LIGHT, strokeColor=CSL_RED))
    d.add(String(width / 2, height - 1.15 * cm,
                 "Personas: BD / Researchers   •   Asset-in-Licensing Portal   •   Decision-Ready Outputs",
                 fontName="Helvetica-Bold", fontSize=8.5,
                 textAnchor="middle", fillColor=CSL_RED_DARK))

    # Orchestration band
    orch_y = height - 3.2 * cm
    d.add(Rect(0.5 * cm, orch_y, width - 1 * cm, 1.4 * cm,
               fillColor=ORANGE_LIGHT, strokeColor=ORANGE))
    d.add(String(width / 2, orch_y + 1.1 * cm,
                 "Agent Orchestration & Policy Layer (CSL-Owned)",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=ORANGE))
    agents = ["Supervisor", "Eugene Agent", "Research Agent",
              "PubMed Agent", "SEC Agent", "Trials Agent"]
    aw = (width - 1.4 * cm) / len(agents)
    for i, name in enumerate(agents):
        ax = 0.7 * cm + i * aw
        d.add(Rect(ax, orch_y + 0.15 * cm, aw - 0.2 * cm, 0.65 * cm,
                   fillColor=WHITE, strokeColor=ORANGE))
        d.add(String(ax + (aw - 0.2 * cm) / 2, orch_y + 0.42 * cm, name,
                     fontName="Helvetica-Bold", fontSize=7.5,
                     textAnchor="middle", fillColor=ORANGE))

    # AgentCore band
    core_y = height - 5 * cm
    d.add(Rect(0.5 * cm, core_y, width - 1 * cm, 1.4 * cm,
               fillColor=PURPLE_LIGHT, strokeColor=PURPLE))
    d.add(String(width / 2, core_y + 1.1 * cm,
                 "AWS Bedrock AgentCore (Runtime • Memory • Observability • Gateway)",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=PURPLE))
    cores = ["Runtime", "Memory", "Gateway", "Observability"]
    cw = (width - 1.4 * cm) / len(cores)
    for i, name in enumerate(cores):
        cx = 0.7 * cm + i * cw
        d.add(Rect(cx, core_y + 0.15 * cm, cw - 0.2 * cm, 0.65 * cm,
                   fillColor=WHITE, strokeColor=PURPLE))
        d.add(String(cx + (cw - 0.2 * cm) / 2, core_y + 0.42 * cm, name,
                     fontName="Helvetica-Bold", fontSize=8,
                     textAnchor="middle", fillColor=PURPLE))

    # Knowledge band
    know_y = height - 7 * cm
    d.add(Rect(0.5 * cm, know_y, width - 1 * cm, 1.6 * cm,
               fillColor=TEAL_LIGHT, strokeColor=TEAL))
    d.add(String(width / 2, know_y + 1.3 * cm,
                 "CSL Authoritative Knowledge & Intelligence",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=TEAL))
    knows = ["Eugene KG\n(Neo4j auth.)", "Milvus\nVector Index",
             "Bedrock\nKnowledge Base", "SharePoint /\nConfluence",
             "eRooms /\nVDR (Deals)"]
    kw = (width - 1.4 * cm) / len(knows)
    for i, name in enumerate(knows):
        kx = 0.7 * cm + i * kw
        d.add(Rect(kx, know_y + 0.15 * cm, kw - 0.2 * cm, 1 * cm,
                   fillColor=WHITE, strokeColor=TEAL))
        for j, line in enumerate(name.split("\n")):
            d.add(String(kx + (kw - 0.2 * cm) / 2,
                         know_y + 0.7 * cm - j * 0.3 * cm, line,
                         fontName="Helvetica-Bold", fontSize=7,
                         textAnchor="middle", fillColor=TEAL))

    # Sources
    src_y = height - 8.6 * cm
    d.add(Rect(0.5 * cm, src_y, width - 1 * cm, 1 * cm,
               fillColor=GRAY_LIGHT, strokeColor=GRAY_MID))
    d.add(String(width / 2, src_y + 0.7 * cm,
                 "Data Sources: Public (PubMed, USPTO, ClinicalTrials, SEC EDGAR, ChEMBL)   |   Partner (Prudentia)   |   Internal CSL",
                 fontName="Helvetica", fontSize=7.5,
                 textAnchor="middle", fillColor=GRAY_DARK))
    d.add(String(width / 2, src_y + 0.25 * cm,
                 "Modalities: Literature  •  Trials  •  Patents  •  Financial  •  Market data",
                 fontName="Helvetica-Oblique", fontSize=7,
                 textAnchor="middle", fillColor=GRAY_DARK))

    # Security band
    sec_y = 0.5 * cm
    d.add(Rect(0.5 * cm, sec_y, width - 1 * cm, 1.4 * cm,
               fillColor=BLUE_PALE, strokeColor=DEEP_BLUE))
    d.add(String(width / 2, sec_y + 1.1 * cm,
                 "Security, Identity & Governance (Cross-Cutting)",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=DEEP_BLUE))
    secs = ["Entra SSO + RBAC", "Bedrock Guardrails", "PrivateLink / VPC",
            "KMS / MFA", "CloudWatch + X-Ray", "Audit / 21 CFR Part 11"]
    sw = (width - 1.4 * cm) / len(secs)
    for i, name in enumerate(secs):
        sx = 0.7 * cm + i * sw
        d.add(Rect(sx, sec_y + 0.15 * cm, sw - 0.2 * cm, 0.65 * cm,
                   fillColor=WHITE, strokeColor=DEEP_BLUE))
        d.add(String(sx + (sw - 0.2 * cm) / 2, sec_y + 0.42 * cm, name,
                     fontName="Helvetica-Bold", fontSize=7,
                     textAnchor="middle", fillColor=DEEP_BLUE))
    return d


def data_model_diagram(width=17 * cm, height=11 * cm):
    """Eugene knowledge-graph schema: 9 node labels + relationship edges."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "Eugene Knowledge Graph — Schema (9 node labels, principal edges)",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    # Node positions (centre of bubble)
    nodes = {
        "Drug":          (4.3*cm,  8.5*cm, CSL_RED),
        "Disease":       (8.5*cm,  9.0*cm, ORANGE),
        "GeneProtein":   (12.7*cm, 8.5*cm, PURPLE),
        "ClinicalTrial": (4.3*cm,  5.5*cm, STEEL_BLUE),
        "Organization":  (8.5*cm,  5.5*cm, TEAL),
        "Patent":        (12.7*cm, 5.5*cm, GREEN),
        "Publication":   (4.3*cm,  2.5*cm, GRAY_DARK),
        "Annotation":    (8.5*cm,  2.5*cm, GRAY_MID),
        "Therapeutic\nArea": (12.7*cm, 2.5*cm, CSL_RED_DARK),
    }
    edges = [
        ("Drug",          "Disease",       "INDICATES"),
        ("Drug",          "GeneProtein",   "TARGETS"),
        ("GeneProtein",   "Disease",       "ASSOCIATED_WITH"),
        ("Drug",          "ClinicalTrial", "STUDIED_IN"),
        ("ClinicalTrial", "Organization",  "CONDUCTED_BY"),
        ("Organization",  "Patent",        "OWNS_PATENT_ON"),
        ("Patent",        "Drug",          "PATENT_OF"),
        ("Publication",   "Drug",          "PUBLISHED_IN"),
        ("Drug",          "Therapeutic\nArea", "BELONGS_TO"),
        ("Annotation",    "Disease",       "ANNOTATES"),
    ]
    # Draw edges first (under bubbles)
    for a, b, lbl in edges:
        ax, ay, _ = nodes[a]
        bx, by, _ = nodes[b]
        d.add(Line(ax, ay, bx, by, strokeColor=GRAY_MID, strokeWidth=0.6))
        # arrowhead
        import math
        dx, dy = bx - ax, by - ay
        ll = math.hypot(dx, dy) or 1
        ux, uy = dx / ll, dy / ll
        head_x = bx - ux * 0.55 * cm
        head_y = by - uy * 0.55 * cm
        # perpendicular vector for label offset
        d.add(Polygon([head_x, head_y,
                       head_x - ux * 6 + uy * 4,
                       head_y - uy * 6 - ux * 4,
                       head_x - ux * 6 - uy * 4,
                       head_y - uy * 6 + ux * 4],
                      fillColor=GRAY_MID, strokeColor=GRAY_MID))
        # label at midpoint
        mx, my = (ax + bx) / 2, (ay + by) / 2
        d.add(String(mx, my + 2, lbl, fontName="Helvetica",
                     fontSize=6, textAnchor="middle", fillColor=GRAY_DARK))

    # Draw bubbles
    for name, (x, y, col) in nodes.items():
        d.add(Circle(x, y, 0.85 * cm, fillColor=col, strokeColor=col))
        # node name (multi-line aware)
        lines = name.split("\n")
        for i, line in enumerate(lines):
            offset = (len(lines) - 1) / 2 - i
            d.add(String(x, y - 3 + offset * 9, line,
                         fontName="Helvetica-Bold", fontSize=7.5,
                         textAnchor="middle", fillColor=WHITE))

    # Counts band at bottom
    d.add(String(width / 2, 0.6 * cm,
                 "Approx. 484k nodes  •  21M edges  •  Bolt protocol  •  parameterised Cypher only",
                 fontName="Helvetica-Oblique", fontSize=8,
                 textAnchor="middle", fillColor=GRAY_DARK))
    return d


def auth_flow_diagram(width=17 * cm, height=10 * cm):
    """Two-layer authentication: Entra ID → eugene_ws JWT → downstream."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "Authentication Flow — Entra ID → Eugene JWT → Service Mesh",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    boxes = [
        ("User Browser",            1.0*cm,  height-2.2*cm, 3.4*cm, 1.0*cm, GRAY_LIGHT, BLACK),
        ("Microsoft\nEntra ID",     6.0*cm,  height-2.2*cm, 3.4*cm, 1.0*cm, BLUE_PALE,  DEEP_BLUE),
        ("eugene_ws\n/login",       11.0*cm, height-2.2*cm, 3.4*cm, 1.0*cm, ORANGE_LIGHT, ORANGE),
        ("Eugene JWT (HS256)\nclaims: iss, aud, sub, roles, upn, exp",
                                    3.0*cm,  height-5.0*cm, 11.0*cm, 1.2*cm, CSL_RED_LIGHT, CSL_RED),
        ("eugene-agent-ws",         1.0*cm,  height-7.5*cm, 3.4*cm, 1.0*cm, ORANGE_LIGHT, ORANGE),
        ("eugene-mcp",              6.0*cm,  height-7.5*cm, 3.4*cm, 1.0*cm, PURPLE_LIGHT, PURPLE),
        ("eugene-ws (API)",         11.0*cm, height-7.5*cm, 3.4*cm, 1.0*cm, BLUE_PALE,    STEEL_BLUE),
    ]
    # Draw boxes
    centres = []
    for label, x, y, w, h, bg, fg in boxes:
        d.add(Rect(x, y, w, h, fillColor=bg, strokeColor=fg, strokeWidth=1.2))
        for i, line in enumerate(label.split("\n")):
            offset = (len(label.split("\n")) - 1) / 2 - i
            d.add(String(x + w / 2, y + h / 2 - 4 + offset * 10, line,
                         fontName="Helvetica-Bold", fontSize=8,
                         textAnchor="middle", fillColor=fg))
        centres.append((x + w / 2, y + h / 2, x + w, y, x, y + h))

    # Numbered arrows
    def arrow_label(x1, y1, x2, y2, n, label, color=BLACK):
        d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
        # arrowhead
        import math
        dx, dy = x2 - x1, y2 - y1
        ll = math.hypot(dx, dy) or 1
        ux, uy = dx / ll, dy / ll
        d.add(Polygon([x2, y2,
                       x2 - ux * 8 + uy * 4,
                       y2 - uy * 8 - ux * 4,
                       x2 - ux * 8 - uy * 4,
                       y2 - uy * 8 + ux * 4],
                      fillColor=color, strokeColor=color))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        d.add(Circle(mx, my, 7, fillColor=color, strokeColor=color))
        d.add(String(mx, my - 2.5, str(n), fontName="Helvetica-Bold",
                     fontSize=7, textAnchor="middle", fillColor=WHITE))
        d.add(String(mx + 12, my - 2, label, fontName="Helvetica",
                     fontSize=7, fillColor=GRAY_DARK))

    # Sequence:
    # 1: User → Entra; 2: Entra → User (id_token); 3: User → eugene_ws (code);
    # 4: eugene_ws → JWT bag; 5: JWT → agent; 6: JWT → mcp; 7: JWT → core api
    arrow_label(centres[0][0]+1.7*cm, centres[0][1], centres[1][0]-1.7*cm, centres[1][1], 1, "OAuth login")
    arrow_label(centres[1][0]-1.7*cm, centres[1][1]-12, centres[0][0]+1.7*cm, centres[0][1]-12, 2, "id_token (RS256)", color=DEEP_BLUE)
    arrow_label(centres[0][0]+1.7*cm, centres[0][1]-24, centres[2][0]-1.7*cm, centres[2][1]-24, 3, "exchange code")
    arrow_label(centres[2][0], centres[2][1]-h, centres[2][0], height-3.8*cm, 4, "issue Eugene JWT", color=CSL_RED)
    # JWT → 3 services
    arrow_label(centres[4][0], height-3.8*cm-1.2*cm, centres[4][0], centres[4][1]+0.5*cm, 5, "Bearer JWT", color=ORANGE)
    arrow_label(centres[5][0], height-3.8*cm-1.2*cm, centres[5][0], centres[5][1]+0.5*cm, 6, "Bearer JWT", color=PURPLE)
    arrow_label(centres[6][0], height-3.8*cm-1.2*cm, centres[6][0], centres[6][1]+0.5*cm, 7, "Bearer JWT", color=STEEL_BLUE)

    d.add(String(width / 2, 0.4 * cm,
                 "Local mode (ENVIRONMENT=local) bypasses steps 1–3 and issues a development JWT directly.",
                 fontName="Helvetica-Oblique", fontSize=7.5,
                 textAnchor="middle", fillColor=GRAY_DARK))
    return d


def react_loop_diagram(width=17 * cm, height=9 * cm):
    """ReAct loop: Think → Act → Observe → repeat → Synthesise."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "Strands ReAct Loop — Think / Act / Observe / Synthesise",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    cx, cy = width / 2, height / 2 - 0.3*cm
    radius = 3.2 * cm
    nodes = [
        ("THINK\n(LLM reasons)",     cx,            cy + radius,   GREEN),
        ("ACT\n(call MCP tool)",     cx + radius,   cy,            ORANGE),
        ("OBSERVE\n(tool result)",   cx,            cy - radius,   PURPLE),
        ("PLAN\n(next step?)",       cx - radius,   cy,            STEEL_BLUE),
    ]
    # Draw circular arrows connecting them clockwise
    import math
    positions = [(x, y) for _, x, y, _ in nodes]
    for i in range(len(positions)):
        x1, y1 = positions[i]
        x2, y2 = positions[(i + 1) % len(positions)]
        # Curve as a simple line; arrowhead at target side
        dx, dy = x2 - x1, y2 - y1
        ll = math.hypot(dx, dy)
        ux, uy = dx / ll, dy / ll
        sx, sy = x1 + ux * 1.15 * cm, y1 + uy * 1.15 * cm
        ex, ey = x2 - ux * 1.15 * cm, y2 - uy * 1.15 * cm
        d.add(Line(sx, sy, ex, ey, strokeColor=GRAY_MID, strokeWidth=1.2))
        d.add(Polygon([ex, ey,
                       ex - ux * 8 + uy * 5,
                       ey - uy * 8 - ux * 5,
                       ex - ux * 8 - uy * 5,
                       ey - uy * 8 + ux * 5],
                      fillColor=GRAY_MID, strokeColor=GRAY_MID))

    # Draw bubbles on top
    for label, x, y, col in nodes:
        d.add(Circle(x, y, 1.1 * cm, fillColor=col, strokeColor=col))
        for i, line in enumerate(label.split("\n")):
            offset = (len(label.split("\n")) - 1) / 2 - i
            d.add(String(x, y - 2 + offset * 10, line,
                         fontName="Helvetica-Bold", fontSize=8,
                         textAnchor="middle", fillColor=WHITE))

    # Centre badge
    d.add(Circle(cx, cy, 1.3 * cm, fillColor=CSL_RED, strokeColor=CSL_RED))
    d.add(String(cx, cy + 6, "Eugene", fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=WHITE))
    d.add(String(cx, cy - 6, "Agent", fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=WHITE))

    # Stop conditions sidebar
    sb_x = 0.5 * cm
    d.add(Rect(sb_x, 0.5 * cm, 5.5 * cm, 2.6 * cm,
               fillColor=GRAY_LIGHT, strokeColor=GRAY_MID))
    d.add(String(sb_x + 0.2*cm, 2.7*cm, "Stop conditions:",
                 fontName="Helvetica-Bold", fontSize=8, fillColor=DEEP_BLUE))
    for i, t in enumerate([
        "• Sufficient evidence to answer",
        "• Tool budget exhausted",
        "• max_iterations reached  (AGT-02)",
        "• timeout exceeded  (AGT-03)",
    ]):
        d.add(String(sb_x + 0.2*cm, 2.3*cm - i * 0.4*cm, t,
                     fontName="Helvetica", fontSize=7.5, fillColor=GRAY_DARK))

    # Synthesise side
    sx2 = width - 6 * cm
    d.add(Rect(sx2, 0.5 * cm, 5.5 * cm, 2.6 * cm,
               fillColor=BLUE_PALE, strokeColor=DEEP_BLUE))
    d.add(String(sx2 + 0.2*cm, 2.7*cm, "Synthesise:",
                 fontName="Helvetica-Bold", fontSize=8, fillColor=DEEP_BLUE))
    for i, t in enumerate([
        "• Tokens stream via SSE",
        "• Citations from graph nodes",
        "• Sliding-window memory (N turns)",
        "• Final answer to UI",
    ]):
        d.add(String(sx2 + 0.2*cm, 2.3*cm - i * 0.4*cm, t,
                     fontName="Helvetica", fontSize=7.5, fillColor=GRAY_DARK))

    return d


def tech_stack_diagram(width=17 * cm, height=9 * cm):
    """Technology stack as a layered bar chart."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "Technology Stack — Layered Inventory",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    layers = [
        ("Frontend",      ["Streamlit", "Next.js + TypeScript", "Cytoscape.js", "Chakra UI"],          CSL_RED),
        ("Agent",         ["Strands (ReAct)", "Anthropic Claude", "OpenAI GPT-4.1", "FastMCP client"], ORANGE),
        ("Tool / API",    ["FastMCP", "FastAPI", "Pydantic v2", "httpx / aiohttp"],                    PURPLE),
        ("Data",          ["Neo4j 5.26 CE", "APOC", "GDS", "Milvus", "sentence-transformers"],         TEAL),
        ("DevOps",        ["Docker", "ECS Fargate", "ECR", "Terraform", "GitHub Actions"],             STEEL_BLUE),
        ("Quality",       ["Black", "Ruff", "isort", "Pytest", "MLflow", "pre-commit"],                GREEN),
    ]
    row_h = (height - 1.6 * cm) / len(layers)
    for i, (lyr, items, col) in enumerate(layers):
        y = height - 1.0 * cm - (i + 1) * row_h + 0.1 * cm
        d.add(Rect(0.6 * cm, y, 3.0 * cm, row_h - 0.2 * cm,
                   fillColor=col, strokeColor=col))
        d.add(String(0.6 * cm + 1.5 * cm, y + (row_h - 0.2 * cm) / 2 - 4, lyr,
                     fontName="Helvetica-Bold", fontSize=10,
                     textAnchor="middle", fillColor=WHITE))
        # Items
        per = (width - 4.4 * cm) / max(1, len(items))
        for j, it in enumerate(items):
            ix = 3.8 * cm + j * per
            d.add(Rect(ix, y, per - 0.15 * cm, row_h - 0.2 * cm,
                       fillColor=WHITE, strokeColor=col, strokeWidth=1))
            d.add(String(ix + (per - 0.15 * cm) / 2,
                         y + (row_h - 0.2 * cm) / 2 - 3, it,
                         fontName="Helvetica-Bold", fontSize=8,
                         textAnchor="middle", fillColor=col))
    return d


def deploy_diagram(width=17 * cm, height=10 * cm):
    """AWS deployment topology diagram (current state)."""
    d = Drawing(width, height)
    d.add(String(width / 2, height - 0.4 * cm,
                 "AWS Production Deployment Topology",
                 fontName="Helvetica-Bold", fontSize=10,
                 textAnchor="middle", fillColor=DEEP_BLUE))

    # Internet box
    d.add(Rect(width / 2 - 1.5 * cm, height - 1.4 * cm, 3 * cm, 0.6 * cm,
               fillColor=GRAY_LIGHT, strokeColor=GRAY_MID))
    d.add(String(width / 2, height - 1.15 * cm, "User (corporate VPN)",
                 fontName="Helvetica-Bold", fontSize=8,
                 textAnchor="middle", fillColor=GRAY_DARK))

    # ALB
    alb_y = height - 2.6 * cm
    d.add(Rect(width / 2 - 4 * cm, alb_y, 8 * cm, 0.8 * cm,
               fillColor=DEEP_BLUE, strokeColor=DEEP_BLUE))
    d.add(String(width / 2, alb_y + 0.45 * cm,
                 "Internal Application Load Balancer  (TLS termination)",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=WHITE))
    d.add(String(width / 2, alb_y + 0.18 * cm,
                 "Listener rules: /agent/ui/*  •  /agent/api/*  •  /docs  •  /labels  •  ...",
                 fontName="Helvetica", fontSize=7,
                 textAnchor="middle", fillColor=WHITE))

    # ECS Fargate band
    ecs_y = height - 5.6 * cm
    d.add(Rect(0.5 * cm, ecs_y, width - 1 * cm, 2.6 * cm,
               fillColor=ORANGE_LIGHT, strokeColor=ORANGE,
               strokeDashArray=[3, 3]))
    d.add(String(width / 2, ecs_y + 2.3 * cm,
                 "AWS ECS Fargate cluster — VPC private subnets",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=ORANGE))
    services = [
        ("eugene-agent-ui",  "Streamlit UI",            CSL_RED),
        ("eugene-agent-ws",  "Strands Agent",           ORANGE),
        ("eugene-mcp",       "MCP Server",              PURPLE),
        ("eugene-ws",        "Core API (FastAPI)",      STEEL_BLUE),
    ]
    sv = (width - 2 * cm) / len(services)
    for i, (svc, role, col) in enumerate(services):
        sx = 1 * cm + i * sv
        d.add(Rect(sx, ecs_y + 0.4 * cm, sv - 0.3 * cm, 1.4 * cm,
                   fillColor=WHITE, strokeColor=col, strokeWidth=1.2))
        d.add(String(sx + (sv - 0.3 * cm) / 2, ecs_y + 1.5 * cm, svc,
                     fontName="Helvetica-Bold", fontSize=8,
                     textAnchor="middle", fillColor=col))
        d.add(String(sx + (sv - 0.3 * cm) / 2, ecs_y + 1.05 * cm, role,
                     fontName="Helvetica", fontSize=7,
                     textAnchor="middle", fillColor=GRAY_DARK))
        d.add(String(sx + (sv - 0.3 * cm) / 2, ecs_y + 0.65 * cm, "ECS task",
                     fontName="Helvetica-Oblique", fontSize=6.5,
                     textAnchor="middle", fillColor=GRAY_MID))

    # Neo4j on EC2
    n4_y = ecs_y - 1.6 * cm
    d.add(Rect(width / 2 - 4 * cm, n4_y, 8 * cm, 1.2 * cm,
               fillColor=TEAL_LIGHT, strokeColor=TEAL))
    d.add(String(width / 2, n4_y + 0.85 * cm, "Neo4j 5.26 CE on EC2",
                 fontName="Helvetica-Bold", fontSize=9,
                 textAnchor="middle", fillColor=TEAL))
    d.add(String(width / 2, n4_y + 0.5 * cm,
                 "manually provisioned  •  Bolt 7687  •  484k nodes / 21M edges",
                 fontName="Helvetica", fontSize=7,
                 textAnchor="middle", fillColor=GRAY_DARK))
    d.add(String(width / 2, n4_y + 0.2 * cm,
                 "no automated S3 snapshot policy",
                 fontName="Helvetica-Oblique", fontSize=6.5,
                 textAnchor="middle", fillColor=GRAY_MID))

    return d


# ════════════════════════════════════════════════════════════════════════
# PDF — book-format renderer
# ════════════════════════════════════════════════════════════════════════
class CSLBookDocTemplate(BaseDocTemplate):
    """Custom doc template with stage1-style header/footer, TOC support,
    and a canvas-painted cover page on page 1."""

    def __init__(self, filename, doc_title, doc_subtitle, **kw):
        kw.setdefault("pagesize", A4)
        kw.setdefault("leftMargin", 1.8 * cm)
        kw.setdefault("rightMargin", 1.8 * cm)
        kw.setdefault("topMargin", 1.5 * cm)
        kw.setdefault("bottomMargin", 1.1 * cm)
        kw.setdefault("title", doc_title)
        kw.setdefault("author", "CSL Behring — Eugene Programme")
        super().__init__(filename, **kw)
        self.doc_title = doc_title
        self.doc_subtitle = doc_subtitle
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="content")
        # Landscape A4 frame (for wide diagrams that don't fit portrait)
        ls_w, ls_h = landscape(A4)
        ls_frame = Frame(self.leftMargin, self.bottomMargin,
                         ls_w - self.leftMargin - self.rightMargin,
                         ls_h - self.topMargin - self.bottomMargin,
                         id="landscape_content")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame], onPage=self._on_cover_page),
            PageTemplate(id="body",  frames=[frame], onPage=self._on_body_page),
            PageTemplate(id="landscape", pagesize=landscape(A4), frames=[ls_frame],
                         onPage=self._on_landscape_page),
        ])

    def _draw_header_footer(self, canvas_obj, doc):
        canvas_obj.saveState()
        w, h = A4
        # Header — stage 1 style: deep blue strip with title on left, document
        # name on right, page number on far right of footer.
        canvas_obj.setFillColor(DEEP_BLUE)
        canvas_obj.rect(0, h - 1.0 * cm, w, 1.0 * cm, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        # CSL logo top-left, on the band
        renderPDF.draw(csl_logo_drawing(width=2.6 * cm, height=0.78 * cm),
                       canvas_obj, 0.6 * cm, h - 0.92 * cm)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawString(3.6 * cm, h - 0.6 * cm,
                              "EUGENE PLATFORM  |  " + self.doc_title.upper())
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawRightString(w - 0.6 * cm, h - 0.6 * cm,
                                   "CONFIDENTIAL — CSL BEHRING")

        # Footer — deep blue strip, date / centre tag-line / page number
        canvas_obj.setFillColor(DEEP_BLUE)
        canvas_obj.rect(0, 0, w, 0.75 * cm, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawString(0.6 * cm, 0.27 * cm, f"Date: {TODAY}")
        canvas_obj.drawCentredString(
            w / 2, 0.27 * cm,
            "Eugene Knowledge Graph — Agentic AI Platform")
        canvas_obj.drawRightString(w - 0.6 * cm, 0.27 * cm,
                                   f"Page {doc.page - 1}")  # cover is page 0
        canvas_obj.restoreState()

    def _on_cover_page(self, canvas_obj, doc):
        _build_cover_page(canvas_obj, self.doc_title, self.doc_subtitle)

    def _on_body_page(self, canvas_obj, doc):
        self._draw_header_footer(canvas_obj, doc)

    def _on_landscape_page(self, canvas_obj, doc):
        """Header / footer for the landscape page (page geometry differs)."""
        canvas_obj.saveState()
        w, h = landscape(A4)
        # Header
        canvas_obj.setFillColor(DEEP_BLUE)
        canvas_obj.rect(0, h - 1.0 * cm, w, 1.0 * cm, fill=1, stroke=0)
        renderPDF.draw(csl_logo_drawing(width=2.6 * cm, height=0.78 * cm),
                       canvas_obj, 0.6 * cm, h - 0.92 * cm)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawString(3.6 * cm, h - 0.6 * cm,
                              "EUGENE PLATFORM  |  " + self.doc_title.upper())
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawRightString(w - 0.6 * cm, h - 0.6 * cm,
                                   "CONFIDENTIAL — CSL BEHRING")
        # Footer
        canvas_obj.setFillColor(DEEP_BLUE)
        canvas_obj.rect(0, 0, w, 0.75 * cm, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawString(0.6 * cm, 0.27 * cm, f"Date: {TODAY}")
        canvas_obj.drawCentredString(
            w / 2, 0.27 * cm,
            "Eugene Knowledge Graph — Agentic AI Platform")
        canvas_obj.drawRightString(w - 0.6 * cm, 0.27 * cm,
                                   f"Page {max(1, doc.page - 1)}")
        canvas_obj.restoreState()

    def afterFlowable(self, flowable):
        """Wire ColorBand and TocHeading flowables into the TOC."""
        level = getattr(flowable, "_csl_toc_level", None)
        if level is None:
            return
        text = flowable.getPlainText() if hasattr(flowable, "getPlainText") \
               else flowable.text
        # page numbering: cover is page 1; TOC is page 2 — we display "Page 1"
        # on the TOC, so subtract 1 from doc.page.
        self.notify("TOCEntry", (level, text, max(1, self.page - 1)))


def _styles():
    base = getSampleStyleSheet()
    s = {
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=10, leading=14.5, spaceAfter=6, textColor=BLACK,
            fontName="Helvetica", alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
            fontSize=10, leading=14, leftIndent=14, bulletIndent=4,
            spaceAfter=3, fontName="Helvetica"),
        "part": ParagraphStyle("part", parent=base["Heading1"],
            fontSize=22, leading=28, spaceBefore=20, spaceAfter=14,
            textColor=CSL_RED, fontName="Helvetica-Bold",
            alignment=TA_LEFT),
        "chapter": ParagraphStyle("chapter", parent=base["Heading1"],
            fontSize=16, leading=20, spaceBefore=14, spaceAfter=8,
            textColor=DEEP_BLUE, fontName="Helvetica-Bold"),
        "section": ParagraphStyle("section", parent=base["Heading2"],
            fontSize=12, leading=16, spaceBefore=10, spaceAfter=4,
            textColor=STEEL_BLUE, fontName="Helvetica-Bold"),
        "subsec": ParagraphStyle("subsec", parent=base["Heading3"],
            fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3,
            textColor=TEAL, fontName="Helvetica-Bold"),
        "callout": ParagraphStyle("callout", parent=base["Normal"],
            fontSize=9.5, leading=13, textColor=ORANGE,
            fontName="Helvetica-Oblique",
            leftIndent=10, rightIndent=10, borderColor=ORANGE,
            borderWidth=0.5, borderPadding=8, backColor=ORANGE_LIGHT,
            spaceBefore=6, spaceAfter=8),
        "code": ParagraphStyle("code", parent=base["Code"],
            fontSize=8, leading=11, fontName="Courier",
            textColor=DEEP_BLUE, backColor=BLUE_PALE,
            leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4),
        "title_main": ParagraphStyle("title_main", parent=base["Title"],
            fontSize=28, leading=34, alignment=TA_LEFT, textColor=CSL_RED,
            fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8),
        "title_sub": ParagraphStyle("title_sub", parent=base["Normal"],
            fontSize=14, leading=20, alignment=TA_LEFT, textColor=DEEP_BLUE,
            fontName="Helvetica", spaceAfter=20),
        "cover_meta": ParagraphStyle("cover_meta", parent=base["Normal"],
            fontSize=10.5, leading=14, textColor=GRAY_DARK,
            fontName="Helvetica", spaceAfter=4),
        "toc_h1": ParagraphStyle("toc_h1", parent=base["Normal"],
            fontSize=11, leading=16, fontName="Helvetica-Bold",
            textColor=CSL_RED, spaceBefore=10, spaceAfter=2),
        "toc_h2": ParagraphStyle("toc_h2", parent=base["Normal"],
            fontSize=10, leading=14, fontName="Helvetica-Bold",
            textColor=DEEP_BLUE, leftIndent=12),
        "toc_h3": ParagraphStyle("toc_h3", parent=base["Normal"],
            fontSize=9.5, leading=13, fontName="Helvetica",
            textColor=STEEL_BLUE, leftIndent=24),
    }
    return s


class TocHeading(Paragraph):
    """A Paragraph that registers itself with the doc template's TOC."""
    def __init__(self, text, style, level):
        super().__init__(text, style)
        self._csl_toc_level = level


def _findings_rows(severity):
    if severity == "ALL":
        rows = [["ID", "Severity", "Title", "Description", "Remediation", "Effort"]]
        for sev in ("CRITICAL", "HIGH", "MEDIUM"):
            for f in FINDINGS[sev]:
                rows.append([f[0], sev] + list(f[1:]))
        return rows
    rows = [["ID", "Title", "Description", "Remediation", "Effort"]]
    for f in FINDINGS[severity]:
        rows.append(list(f))
    return rows


def _positives_rows():
    rows = [["Strength", "Detail"]]
    rows.extend([list(p) for p in POSITIVES])
    return rows


def _wrap_table(data, header_color):
    n_cols = len(data[0])
    avail = W - 4 * cm
    widths = [avail / n_cols] * n_cols
    cell_style = ParagraphStyle("cell", fontSize=8.5, leading=11,
                                fontName="Helvetica", textColor=BLACK)
    hdr_style  = ParagraphStyle("hdr",  fontSize=9, leading=11,
                                fontName="Helvetica-Bold", textColor=WHITE)
    wrapped = []
    for ridx, row in enumerate(data):
        wrapped.append([Paragraph(str(c), hdr_style if ridx == 0 else cell_style)
                        for c in row])
    t = Table(wrapped, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRAY_MID),
    ]))
    return t


def _diagram_image(kind):
    builders = {
        "ARCH":      architecture_diagram,
        "SEQ":       sequence_diagram,
        "NEXTGEN":   nextgen_diagram,
        "DEPLOY":    deploy_diagram,
        "DATAMODEL": data_model_diagram,
        "AUTHFLOW":  auth_flow_diagram,
        "REACT":     react_loop_diagram,
        "TECHSTACK": tech_stack_diagram,
    }
    fn = builders.get(kind)
    if fn is None:
        return None
    drawing = fn()
    img = RLImage(BytesIO(render_drawing_to_png_bytes(drawing, dpi=200)),
                  width=W - 4 * cm,
                  height=(W - 4 * cm) * (drawing.height / drawing.width))
    return img


# ─── Stage 1-style ColorBand flowable (full-width strip heading) ─────────
class ColorBand(Flowable):
    """Full-width coloured rectangle with a left-aligned title; mimics the
    stage 1 audit report's section-header style."""
    def __init__(self, text, color=DEEP_BLUE, text_color=WHITE,
                 height=1.0 * cm, font_size=12, toc_level=None):
        super().__init__()
        self.text = text
        self.color = color
        self.text_color = text_color
        self.height = height
        self.font_size = font_size
        self._csl_toc_level = toc_level  # picked up by afterFlowable for TOC

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height + 0.15 * cm

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.setFillColor(self.text_color)
        self.canv.setFont("Helvetica-Bold", self.font_size)
        self.canv.drawString(10, self.height / 2 - self.font_size / 2 + 1,
                             self.text)

    def getPlainText(self):
        return self.text


def _finding_box(severity, fid, title, desc, remediation, effort):
    """Stage 1-style colour-coded finding box, suitable for one finding per box."""
    color_map = {
        "CRITICAL": (CSL_RED,    CSL_RED_LIGHT,  "CRITICAL"),
        "HIGH":     (ORANGE,     ORANGE_LIGHT,   "HIGH"),
        "MEDIUM":   (PURPLE,     PURPLE_LIGHT,   "MEDIUM"),
        "POSITIVE": (GREEN,      GREEN_LIGHT,    "POSITIVE"),
    }
    border, bg, label = color_map.get(severity, (DEEP_BLUE, BLUE_PALE, severity))

    title_style = ParagraphStyle("fb_title", fontName="Helvetica-Bold",
                                 fontSize=9.5, leading=12, textColor=WHITE)
    body_style  = ParagraphStyle("fb_body",  fontName="Helvetica",
                                 fontSize=8.5, leading=11.5, textColor=BLACK)
    bold_body   = ParagraphStyle("fb_bold",  fontName="Helvetica-Bold",
                                 fontSize=8.5, leading=11.5, textColor=border)

    title_tbl = Table([[Paragraph(f"[{label}] &nbsp; {fid} &nbsp;—&nbsp; {title}",
                                  title_style)]],
                      colWidths=[W - 4 * cm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    body_tbl = Table([[Paragraph(
        f"<b>Description.</b> {desc}<br/>"
        f"<b>Remediation.</b> {remediation}<br/>"
        f"<b>Effort.</b> {effort}",
        body_style)]], colWidths=[W - 4 * cm])
    body_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), bg),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("BOX",            (0, 0), (-1, -1), 0.5, border),
    ]))
    return KeepTogether([title_tbl, body_tbl, Spacer(1, 0.18 * cm)])


def _findings_boxes(severity):
    """Return a list of finding-box flowables for the given severity."""
    if severity == "ALL":
        out = []
        for sev in ("CRITICAL", "HIGH", "MEDIUM"):
            for fid, title, desc, rem, eff in FINDINGS[sev]:
                out.append(_finding_box(sev, fid, title, desc, rem, eff))
        return out
    return [_finding_box(severity, *f) for f in FINDINGS[severity]]


def _positive_boxes():
    out = []
    for title, detail in POSITIVES:
        out.append(_finding_box("POSITIVE", "POS", title, detail, "—", "—"))
    return out


def _build_cover_page(canvas_obj, doc_title, doc_subtitle):
    """Stage 1-style cover: deep-blue panel filling the upper portion, with
    CSL logo top-left, white title, classification line, and metadata."""
    canvas_obj.saveState()
    w, h = A4
    # Full-page deep-blue background
    canvas_obj.setFillColor(DEEP_BLUE)
    canvas_obj.rect(0, 0, w, h, fill=1, stroke=0)
    # Accent strip (CSL red) along top
    canvas_obj.setFillColor(CSL_RED)
    canvas_obj.rect(0, h - 1.0 * cm, w, 1.0 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.drawString(1.5 * cm, h - 0.65 * cm,
                          "CSL BEHRING  |  CONFIDENTIAL")
    canvas_obj.drawRightString(w - 1.5 * cm, h - 0.65 * cm,
                               f"DOCUMENT DATE  •  {TODAY.upper()}")

    # CSL logo block (white-bg badge sits well on dark cover)
    renderPDF.draw(csl_logo_drawing(width=4.5 * cm, height=1.5 * cm),
                   canvas_obj, 1.5 * cm, h - 3.4 * cm)

    # Title block
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 28)
    # Word-wrap title manually
    canvas_obj.drawString(1.5 * cm, h - 7.2 * cm, "EUGENE PLATFORM")
    canvas_obj.setFillColor(CSL_RED_LIGHT)
    canvas_obj.setFont("Helvetica-Bold", 18)
    # Use sub-line of doc_title (after the em-dash)
    sub_a = doc_title.split("—", 1)[-1].strip() if "—" in doc_title else doc_title
    canvas_obj.drawString(1.5 * cm, h - 8.4 * cm, sub_a)
    # Decorative line
    canvas_obj.setStrokeColor(CSL_RED)
    canvas_obj.setLineWidth(2)
    canvas_obj.line(1.5 * cm, h - 9.0 * cm, 8 * cm, h - 9.0 * cm)
    # Subtitle
    canvas_obj.setFillColor(BLUE_PALE)
    canvas_obj.setFont("Helvetica", 12)
    # naive 70-char wrap
    words = doc_subtitle.split()
    line, lines = "", []
    for wd in words:
        if len(line) + len(wd) > 70:
            lines.append(line.strip()); line = wd + " "
        else:
            line += wd + " "
    if line:
        lines.append(line.strip())
    for i, ln in enumerate(lines):
        canvas_obj.drawString(1.5 * cm, h - 10.0 * cm - i * 0.6 * cm, ln)

    # Lower metadata band
    band_top = 6 * cm
    canvas_obj.setFillColor(STEEL_BLUE)
    canvas_obj.rect(0, band_top - 4.2 * cm, w, 4.2 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 10)
    meta = [
        ("PREPARED FOR",  "CSL Behring — Business Development & R&D"),
        ("PROGRAMME",     "Eugene Knowledge Graph & Agentic AI Platform"),
        ("DATE",          TODAY),
        ("CLASSIFICATION", "Confidential — Internal Use Only"),
        ("VERSION",       "2.1  (Book Edition)"),
    ]
    for i, (k, v) in enumerate(meta):
        y = band_top - 1.0 * cm - i * 0.65 * cm
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.setFillColor(BLUE_PALE)
        canvas_obj.drawString(1.5 * cm, y, k)
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.drawString(5.0 * cm, y, v)

    # Bottom red strip with footer text
    canvas_obj.setFillColor(CSL_RED)
    canvas_obj.rect(0, 0, w, 1.0 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.drawCentredString(w / 2, 0.35 * cm,
                                 "EUGENE PLATFORM  •  STAKEHOLDER REPORT  •  CSL BEHRING")
    canvas_obj.restoreState()


def _build_pdf_story(book, styles, doc_title, doc_subtitle):
    """Convert the BOOK sequence into ReportLab flowables.

    Cover is rendered directly by canvas (see CSLBookDocTemplate); the story
    starts on page 2 (TOC).
    """
    story = []

    # ─── TABLE OF CONTENTS ────────────────────────────────────────────────
    story.append(ColorBand("TABLE OF CONTENTS", color=DEEP_BLUE,
                           height=1.0 * cm, font_size=12))
    story.append(Spacer(1, 0.4 * cm))
    toc = TableOfContents()
    toc.levelStyles = [styles["toc_h1"], styles["toc_h2"], styles["toc_h3"]]
    story.append(toc)
    story.append(PageBreak())

    # ─── BODY ──────────────────────────────────────────────────────────────
    for tag, payload in book:
        if tag == "PART":
            # Inline ColorBand divider — no blank page either side.
            story.append(Spacer(1, 0.4 * cm))
            story.append(ColorBand(payload.upper(), color=CSL_RED,
                                   height=1.2 * cm, font_size=14, toc_level=0))
            story.append(Spacer(1, 0.2 * cm))
        elif tag == "CHAPTER":
            story.append(Spacer(1, 0.25 * cm))
            story.append(ColorBand(payload, color=DEEP_BLUE,
                                   height=1.0 * cm, font_size=12, toc_level=1))
            story.append(Spacer(1, 0.2 * cm))
        elif tag == "SECTION":
            story.append(Paragraph(payload, styles["section"]))
        elif tag == "SUBSEC":
            story.append(Paragraph(payload, styles["subsec"]))
        elif tag == "PARA":
            story.append(Paragraph(payload, styles["body"]))
        elif tag == "BULLETS":
            for b in payload:
                story.append(Paragraph("• " + b, styles["bullet"]))
            story.append(Spacer(1, 0.12 * cm))
        elif tag == "NUMBERED":
            for i, b in enumerate(payload, 1):
                story.append(Paragraph(f"{i}. {b}", styles["bullet"]))
            story.append(Spacer(1, 0.12 * cm))
        elif tag == "TABLE":
            story.append(_wrap_table(payload, DEEP_BLUE))
            story.append(Spacer(1, 0.2 * cm))
        elif tag == "FINDINGS_TABLE":
            for box in _findings_boxes(payload):
                story.append(box)
        elif tag == "POSITIVES_TABLE":
            for box in _positive_boxes():
                story.append(box)
        elif tag == "DIAGRAM":
            img = _diagram_image(payload)
            if img is not None:
                story.append(KeepTogether([img, Spacer(1, 0.2 * cm)]))
        elif tag == "IMAGE":
            # payload is a path to a PNG on disk
            try:
                from PIL import Image as PILImage
                with PILImage.open(payload) as im:
                    iw, ih = im.size
                ratio = ih / iw
            except Exception:
                ratio = 0.6
            target_w = W - 4 * cm
            img = RLImage(payload, width=target_w,
                          height=min(target_w * ratio, H - 6 * cm))
            story.append(KeepTogether([img, Spacer(1, 0.2 * cm)]))
        elif tag == "LANDSCAPE_IMAGE":
            # payload is (path, optional_caption_str) or just a path string.
            # Renders the image on a dedicated landscape page sized to fill
            # the available landscape body, then returns to portrait.
            if isinstance(payload, tuple):
                img_path, ls_caption = payload
            else:
                img_path, ls_caption = payload, ""
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as im:
                    iw, ih = im.size
                ratio = ih / iw
            except Exception:
                ratio = 0.6
            ls_w, ls_h = landscape(A4)
            avail_w = ls_w - 3.6 * cm    # ~ side margins
            avail_h = ls_h - 4.0 * cm    # leave room for header / footer / caption
            # Fit by whichever bounds first
            width  = avail_w
            height = width * ratio
            if height > avail_h:
                height = avail_h
                width  = height / ratio
            img = RLImage(img_path, width=width, height=height)
            story.append(NextPageTemplate("landscape"))
            story.append(PageBreak())
            story.append(img)
            if ls_caption:
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph(
                    ls_caption,
                    ParagraphStyle("ls_cap", fontSize=9, leading=12,
                                   alignment=TA_CENTER,
                                   fontName="Helvetica-Oblique",
                                   textColor=GRAY_DARK)))
            story.append(NextPageTemplate("body"))
            story.append(PageBreak())
        elif tag == "CAPTION":
            story.append(Paragraph(
                payload,
                ParagraphStyle("cap", fontSize=8.5, leading=11,
                               alignment=TA_CENTER, fontName="Helvetica-Oblique",
                               textColor=GRAY_DARK, spaceAfter=8)))
        elif tag == "CALLOUT":
            story.append(Paragraph("⚑  " + payload, styles["callout"]))
        elif tag == "CODE":
            txt = payload.replace("&", "&amp;").replace("<", "&lt;") \
                          .replace(">", "&gt;").replace("\n", "<br/>")
            story.append(Paragraph(txt, styles["code"]))
            story.append(Spacer(1, 0.12 * cm))
        elif tag == "QUOTE":
            story.append(Paragraph("“" + payload + "”",
                ParagraphStyle("quote", parent=styles["body"],
                               fontName="Helvetica-Oblique",
                               leftIndent=18, rightIndent=18,
                               textColor=GRAY_DARK)))
        elif tag == "PAGEBREAK":
            # Honoured only after the cover/TOC and at end of major sections.
            story.append(PageBreak())

    return story


def render_pdf(book, doc_title, doc_subtitle, out_path):
    styles = _styles()
    doc = CSLBookDocTemplate(out_path, doc_title, doc_subtitle)
    # Page 1 uses the "cover" PageTemplate (canvas-painted, no flowables on it).
    # Switch to "body" template before any body flowable lands, then PageBreak.
    story = [
        Spacer(1, 0.1),                      # forces page 1 to exist
        NextPageTemplate("body"),
        PageBreak(),
    ]
    story.extend(_build_pdf_story(book, styles, doc_title, doc_subtitle))
    doc.multiBuild(story)


# ════════════════════════════════════════════════════════════════════════
# DOCX — book-format renderer
# ════════════════════════════════════════════════════════════════════════
def _shade_cell(cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_run(run, text, *, bold=False, size=10.5, color=None, italic=False,
             name="Calibri"):
    run.text = text
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = name
    if color is not None:
        run.font.color.rgb = color


def _add_para(doc, text, *, bold=False, size=10.5, color=None, italic=False,
              align=None, space_after=4):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run()
    _set_run(r, text, bold=bold, size=size, color=color, italic=italic)
    return p


def _add_heading(doc, text, level=1):
    """level: 0 part, 1 chapter, 2 section, 3 sub."""
    if level == 0:
        size, color, bold, before, after = 24, DOCX_CSL_RED,    True, 18, 12
        outline_lvl = "0"
    elif level == 1:
        size, color, bold, before, after = 17, DOCX_DEEP_BLUE,  True, 14, 8
        outline_lvl = "1"
    elif level == 2:
        size, color, bold, before, after = 13, DOCX_STEEL_BLUE, True, 10, 4
        outline_lvl = "2"
    else:
        size, color, bold, before, after = 11, DOCX_TEAL,       True, 8, 3
        outline_lvl = "3"
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after  = Pt(after)
    # Mark as heading (so Word's TOC field recognises it)
    pPr = p._p.get_or_add_pPr()
    ol = OxmlElement("w:outlineLvl")
    ol.set(qn("w:val"), outline_lvl)
    pPr.append(ol)
    r = p.add_run()
    _set_run(r, text, bold=bold, size=size, color=color)
    return p


def _add_table(doc, data, *, header_color="1B3A6B"):
    n_cols = len(data[0])
    table = doc.add_table(rows=len(data), cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"
    for ridx, row in enumerate(data):
        for cidx, val in enumerate(row):
            cell = table.rows[ridx].cells[cidx]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run()
            if ridx == 0:
                _set_run(r, str(val), bold=True, size=9, color=DOCX_WHITE)
                _shade_cell(cell, header_color)
            else:
                _set_run(r, str(val), size=9, color=DOCX_BLACK)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    doc.add_paragraph()
    return table


def _add_bullets(doc, items, *, numbered=False):
    for i, b in enumerate(items, 1):
        style = "List Number" if numbered else "List Bullet"
        p = doc.add_paragraph(style=style)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run()
        _set_run(r, b, size=10.5)


def _add_callout(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(8)
    r = p.add_run()
    _set_run(r, "⚑  " + text, italic=True, size=10, color=DOCX_CSL_RED)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "FFF3E0")
    pPr.append(shd)


def _add_code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.4)
    p.paragraph_format.right_indent = Cm(0.4)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    r = p.add_run()
    _set_run(r, text, size=9, color=DOCX_DEEP_BLUE, name="Consolas")
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "E3F2FD")
    pPr.append(shd)


def _add_diagram(doc, kind):
    if kind == "ARCH":
        drawing = architecture_diagram()
    elif kind == "SEQ":
        drawing = sequence_diagram()
    elif kind == "NEXTGEN":
        drawing = nextgen_diagram()
    elif kind == "DEPLOY":
        drawing = deploy_diagram()
    else:
        return
    png = render_drawing_to_png_bytes(drawing, dpi=220)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(BytesIO(png), width=Inches(6.5))


def _add_toc_field(doc):
    """Insert a Word TOC field that auto-populates on open."""
    p = doc.add_paragraph()
    run = p.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = r'TOC \o "1-3" \h \z \u'
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    fldChar3 = OxmlElement("w:t")
    fldChar3.text = "Right-click and choose 'Update Field' to populate the table of contents."
    fldChar4 = OxmlElement("w:fldChar")
    fldChar4.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)
    run._r.append(fldChar4)


def _set_docx_header_footer(doc, doc_title):
    section = doc.sections[0]
    section.top_margin    = Cm(2.4)
    section.bottom_margin = Cm(1.8)
    section.left_margin   = Cm(2.0)
    section.right_margin  = Cm(2.0)

    header = section.header
    htbl = header.add_table(rows=1, cols=2, width=Cm(17))
    htbl.autofit = False
    htbl.columns[0].width = Cm(5)
    htbl.columns[1].width = Cm(12)
    logo_cell = htbl.rows[0].cells[0]
    logo_p = logo_cell.paragraphs[0]
    logo_run = logo_p.add_run()
    png = render_drawing_to_png_bytes(
        csl_logo_drawing(width=3.5 * cm, height=1.1 * cm), dpi=220)
    logo_run.add_picture(BytesIO(png), width=Cm(3.4))
    right_p = htbl.rows[0].cells[1].paragraphs[0]
    right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = right_p.add_run()
    _set_run(r, "CSL BEHRING  |  EUGENE PLATFORM",
             bold=True, size=8, color=DOCX_CSL_RED)
    right_p.add_run("\n")
    r3 = right_p.add_run()
    _set_run(r3, doc_title, size=8, color=DOCX_DEEP_BLUE)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run()
    _set_run(fr,
             f"Confidential — CSL Behring Internal Use Only   •   Generated {TODAY}",
             size=8, italic=True, color=DOCX_GRAY)


def render_docx(book, doc_title, doc_subtitle, out_path):
    doc = Document()
    # Default body style
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    _set_docx_header_footer(doc, doc_title)

    # ─── Cover ──────────────────────────────────────────────────────────
    p_logo = doc.add_paragraph()
    p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    rlogo = p_logo.add_run()
    rlogo.add_picture(BytesIO(render_drawing_to_png_bytes(
        csl_logo_drawing(width=4.5 * cm, height=1.6 * cm), dpi=240)),
        width=Cm(4.5))
    doc.add_paragraph()

    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_after = Pt(2)
    r_t = p_t.add_run()
    _set_run(r_t, doc_title, bold=True, size=26, color=DOCX_CSL_RED)
    p_s = doc.add_paragraph()
    r_s = p_s.add_run()
    _set_run(r_s, doc_subtitle, size=14, color=DOCX_DEEP_BLUE)
    doc.add_paragraph()

    for k, v in [
        ("Prepared for:",   "CSL Behring — Business Development & R&D Stakeholders"),
        ("Programme:",      "Eugene Knowledge Graph & Agentic AI Platform"),
        ("Date:",           TODAY),
        ("Classification:", "Confidential — Internal Use Only"),
        ("Version:",        "2.0  (Book Edition)"),
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(); _set_run(r1, k + " ", bold=True, size=10.5,
                                    color=DOCX_DEEP_BLUE)
        r2 = p.add_run(); _set_run(r2, v, size=10.5, color=DOCX_BLACK)

    doc.add_paragraph()
    p_note = doc.add_paragraph()
    rn = p_note.add_run()
    _set_run(rn,
             "This document is a synthesised, book-format evaluation distilled from "
             "the Eugene Project Validation Document, the Stage 1 Assessment & Audit "
             "Report, the Developer Guide, and the canonical architecture diagram.",
             italic=True, size=9, color=DOCX_GRAY)

    doc.add_page_break()

    # ─── Table of Contents (Word field) ─────────────────────────────────
    _add_heading(doc, "Table of Contents", level=1)
    _add_toc_field(doc)
    doc.add_page_break()

    # ─── Body ───────────────────────────────────────────────────────────
    for tag, payload in book:
        if tag == "PART":
            doc.add_page_break()
            _add_heading(doc, payload, level=0)
            doc.add_page_break()
        elif tag == "CHAPTER":
            _add_heading(doc, payload, level=1)
        elif tag == "SECTION":
            _add_heading(doc, payload, level=2)
        elif tag == "SUBSEC":
            _add_heading(doc, payload, level=3)
        elif tag == "PARA":
            _add_para(doc, payload, size=10.5, color=DOCX_BLACK,
                      align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6)
        elif tag == "BULLETS":
            _add_bullets(doc, payload, numbered=False)
        elif tag == "NUMBERED":
            _add_bullets(doc, payload, numbered=True)
        elif tag == "TABLE":
            _add_table(doc, payload)
        elif tag == "FINDINGS_TABLE":
            color_map = {"CRITICAL": "A6192E", "HIGH": "E65100",
                         "MEDIUM": "4A148C",   "ALL": "1B3A6B"}
            _add_table(doc, _findings_rows(payload),
                       header_color=color_map.get(payload, "1B3A6B"))
        elif tag == "POSITIVES_TABLE":
            _add_table(doc, _positives_rows(), header_color="1B5E20")
        elif tag == "DIAGRAM":
            _add_diagram(doc, payload)
        elif tag == "IMAGE":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(payload, width=Inches(6.4))
            except Exception:
                _set_run(p.add_run(), f"[image not found: {payload}]",
                         italic=True, color=DOCX_GRAY, size=9)
        elif tag == "LANDSCAPE_IMAGE":
            # In DOCX, render the image on its own page at a larger width
            # (we keep the document portrait — Word readers can rotate the
            # view if they wish; this still gives the diagram a dedicated
            # page and a wider rendering than inline IMAGE).
            if isinstance(payload, tuple):
                img_path, ls_caption = payload
            else:
                img_path, ls_caption = payload, ""
            doc.add_page_break()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(img_path, width=Inches(9.5))
            except Exception:
                _set_run(p.add_run(), f"[image not found: {img_path}]",
                         italic=True, color=DOCX_GRAY, size=9)
            if ls_caption:
                cp = doc.add_paragraph()
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = cp.add_run()
                _set_run(r, ls_caption, italic=True, size=9, color=DOCX_GRAY)
            doc.add_page_break()
        elif tag == "CAPTION":
            cp = doc.add_paragraph()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.space_after = Pt(8)
            r = cp.add_run()
            _set_run(r, payload, italic=True, size=9, color=DOCX_GRAY)
        elif tag == "CALLOUT":
            _add_callout(doc, payload)
        elif tag == "CODE":
            _add_code(doc, payload)
        elif tag == "QUOTE":
            _add_para(doc, "“" + payload + "”", italic=True, size=10.5,
                      color=DOCX_GRAY)
        elif tag == "PAGEBREAK":
            doc.add_page_break()

    doc.save(out_path)


# ════════════════════════════════════════════════════════════════════════
# DRIVER
# ════════════════════════════════════════════════════════════════════════
def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    deliverables = [
        (DOC1_BOOK, DOC1_TITLE, DOC1_SUBTITLE, DOC1_FILE_PDF, DOC1_FILE_DOCX),
        (DOC2_BOOK, DOC2_TITLE, DOC2_SUBTITLE, DOC2_FILE_PDF, DOC2_FILE_DOCX),
    ]

    for book, title, subtitle, pdf_name, docx_name in deliverables:
        pdf_path  = os.path.join(DOCS_DIR, pdf_name)
        docx_path = os.path.join(DOCS_DIR, docx_name)
        print(f"-- {title}")
        print(f"   PDF  -> {pdf_path}")
        render_pdf(book, title, subtitle, pdf_path)
        print(f"   DOCX -> {docx_path}")
        render_docx(book, title, subtitle, docx_path)

    print()
    print("All four deliverables generated successfully:")
    for _, _, _, p, d in deliverables:
        print(f"   - docs/{p}")
        print(f"   - docs/{d}")


if __name__ == "__main__":
    main()
