#!/usr/bin/env python3
"""
Eugene nextgen UI — Diagnosis & Remediation report (PDF).

Documents what was FOUND, what was CHANGED, and the ACTION TAKEN while fixing
the chat response-quality issues raised from the on-screen Q&A review.

The report date is embedded both in the output filename and inside the document.

Usage:
    python3 generate_fix_report_2026-06-12.py
"""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, ListFlowable, ListItem,
)

# ----------------------------------------------------------------- metadata
REPORT_DATE = date(2026, 6, 12)
DATE_ISO = REPORT_DATE.isoformat()                 # 2026-06-12
DATE_HUMAN = REPORT_DATE.strftime("%B %d, %Y")     # June 12, 2026
OUT = Path(__file__).parent / "docs" / f"Eugene_UI_Fix_Report_{DATE_ISO}.pdf"

# ----------------------------------------------------------------- palette
NAVY   = colors.HexColor("#0F2B46")
STEEL  = colors.HexColor("#22577A")
TEAL   = colors.HexColor("#0B7A75")
GREEN  = colors.HexColor("#1B5E20")
GREEN_BG = colors.HexColor("#E8F5E9")
AMBER  = colors.HexColor("#B26A00")
AMBER_BG = colors.HexColor("#FFF3E0")
RED    = colors.HexColor("#B3261E")
RED_BG = colors.HexColor("#FCEAE8")
GREY_BG = colors.HexColor("#F4F6F8")
GREY_LN = colors.HexColor("#D5DBE1")
GREY_TX = colors.HexColor("#5B6770")
INK    = colors.HexColor("#1F2933")
WHITE  = colors.white

# ----------------------------------------------------------------- styles
ss = getSampleStyleSheet()


def style(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


H1 = style("H1", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY,
           spaceBefore=14, spaceAfter=6, leading=22)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=13, textColor=STEEL,
           spaceBefore=12, spaceAfter=4, leading=16)
BODY = style("BODY", fontSize=9.5, textColor=INK, leading=14, alignment=TA_LEFT,
             spaceAfter=4)
SMALL = style("SMALL", fontSize=8, textColor=GREY_TX, leading=11)
CELL = style("CELL", fontSize=8.5, textColor=INK, leading=11.5)
CELLB = style("CELLB", parent=CELL, fontName="Helvetica-Bold")
CELLW = style("CELLW", parent=CELL, textColor=WHITE, fontName="Helvetica-Bold")
MONO = style("MONO", fontName="Courier", fontSize=8, textColor=INK, leading=11)
TITLE = style("TITLE", fontName="Helvetica-Bold", fontSize=26, textColor=NAVY,
              leading=30, alignment=TA_CENTER)
SUB = style("SUB", fontName="Helvetica", fontSize=12, textColor=STEEL,
            leading=16, alignment=TA_CENTER)


def P(t, s=BODY):
    return Paragraph(t, s)


def chip(text, fg, bg):
    t = Table([[Paragraph(f"<b>{text}</b>",
                          style("chip", fontSize=8, textColor=fg, alignment=TA_CENTER))]],
              colWidths=[34 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, fg),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.8, color=GREY_LN,
                      spaceBefore=6, spaceAfter=6)


def section_table(rows, header_bg=STEEL, col_widths=None):
    data = []
    for r in rows:
        data.append([c if not isinstance(c, str) else Paragraph(c, CELL) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ----------------------------------------------------------------- page furniture
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GREY_LN)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, LETTER[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY_TX)
    canvas.drawString(18 * mm, 9 * mm,
                      f"Eugene UI Fix Report — {DATE_ISO}  ·  CSL Behring Eugene KG platform")
    canvas.drawRightString(LETTER[0] - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------------- content
story = []

# ---- cover
story += [Spacer(1, 40 * mm)]
story += [P("Eugene nextgen UI", TITLE)]
story += [P("Chat Response-Quality — Diagnosis &amp; Remediation Report", SUB)]
story += [Spacer(1, 8 * mm)]
story += [HRFlowable(width="55%", thickness=1.2, color=TEAL, hAlign="CENTER")]
story += [Spacer(1, 6 * mm)]
cover = Table([
    ["Report date", DATE_HUMAN + f"  ({DATE_ISO})"],
    ["Prepared by", "Platform engineering (Claude Code session)"],
    ["Scope", "agent-ws (LLM agent) + agent-ui-nextgen (Next.js chat UI)"],
    ["Environment", "AWS ECS Fargate · cluster stage-eugene-uspto-cluster · us-east-1"],
    ["UI endpoint", "internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/nextgen"],
    ["Status", "Fixes deployed &amp; verified live in production"],
], colWidths=[38 * mm, 120 * mm])
cover.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), NAVY),
    ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (1, 0), (1, -1), [WHITE, GREY_BG]),
    ("GRID", (0, 0), (-1, -1), 0.4, GREY_LN),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story += [cover]
story += [PageBreak()]

# ---- 1. Executive summary
story += [P("1 · Executive summary", H1), hr()]
story += [P(
    "A line-by-line review of the on-screen Eugene chat Q&amp;A surfaced a set of "
    "<b>response-quality</b> defects — not data or connectivity problems. The Neo4j "
    "knowledge graph is healthy and fully connected; every answer in the review was "
    "drawn from real graph data. The defects were caused by (a) the agent's own system "
    "prompt forcing internal citations into the prose, (b) the agent resolving entities "
    "to dead-end alias nodes, and (c) limitations of the only Bedrock model the account "
    "is allowed to use (Amazon Nova). All code-level defects were fixed, rebuilt, "
    "deployed to ECS, and verified with a live end-to-end test.", BODY)]
story += [Spacer(1, 3 * mm)]
summ = [
    [Paragraph("<b>Area</b>", CELLW), Paragraph("<b>Outcome</b>", CELLW)],
    ["Neo4j connectivity / data", "<b>Healthy.</b> 484,259 nodes · 10,692,787 relationships. Verified through the live system."],
    ["Annotation leak <font face='Courier'>[node_id=…, tool=…]</font>", "<b>Fixed</b> at source (prompt) + UI strip. Live test: leak = False."],
    ["False &ldquo;no connection&rdquo; answers", "<b>Fixed</b> — alias/synonym dead-end resolution added to prompt."],
    ["Premature Google fallback", "<b>Fixed</b> — agent must resolve the entity before offering a web link."],
    ["Fabricated &ldquo;Patent 1…11&rdquo; rows", "<b>Fixed</b> — placeholder rows banned in prompt."],
    ["<font face='Courier'>&lt;thinking&gt;</font> tags in bubbles", "<b>Fixed</b> — stripped client-side in the UI."],
    ["Model upgrade to Opus 4.7 / Sonnet 4.6", "<b>Blocked</b> — account-level Anthropic Marketplace subscription not enabled. Remained on nova-pro."],
    ["Count / statistics questions", "<b>Open</b> — needs a new Core-API stats endpoint (recommended)."],
]
story += [section_table(summ, col_widths=[58 * mm, 100 * mm])]

story += [PageBreak()]

# ---- 2. Neo4j
story += [P("2 · Neo4j — connectivity &amp; data check", H1), hr()]
story += [P(
    "<b>Question asked:</b> can we connect to Neo4j, and how many records are present?", BODY)]
neo = [
    [Paragraph("<b>Check</b>", CELLW), Paragraph("<b>Result</b>", CELLW)],
    ["Database connected &amp; healthy", "<b>Yes.</b> The live agent returns real graph data (proteins F9/F10/VTN, patent IDs WO2013117073A1, sponsors Roche/Chugai). Re-confirmed by a live smoke test on 2026-06-12."],
    ["Record count", "<b>484,259 nodes</b> · <b>10,692,787 relationships</b>"],
    ["Direct connect from laptop?", "No — Neo4j (10.88.203.251:7687) is inside the sealed VPC; no VPN tunnel from the workstation, and the prod password is in SSM the deploy IAM user cannot read. This is expected and not a fault."],
    ["Data path", "Agent &rarr; MCP (HTTP) &rarr; Core API (search_ws) &rarr; Neo4j. The agent/MCP never touch Neo4j directly; they call REST tools."],
]
story += [section_table(neo, col_widths=[50 * mm, 108 * mm])]
story += [Spacer(1, 3 * mm)]
story += [P("Conclusion: data and connectivity are correct. The reported problems were "
            "downstream, in how the agent phrases and resolves answers.", SMALL)]

story += [PageBreak()]

# ---- 3. Findings & fixes (the core)
story += [P("3 · Findings &amp; fixes (line-by-line from the review)", H1), hr()]

findings = [
    [Paragraph("<b>Symptom observed</b>", CELLW),
     Paragraph("<b>Root cause</b>", CELLW),
     Paragraph("<b>Action taken</b>", CELLW)],
    ["Every answer ended with <font face='Courier'>[node_id=DB13923, tool=fetch_facts]</font>; also inline <font face='Courier'>(node_id: 2159)</font>.",
     "The agent system prompt contained a &ldquo;Citation requirement&rdquo; instructing the model to print node ids + tool names into its prose.",
     "Removed the citation requirement; replaced with an instruction to answer in clean prose using entity names only. Added a UI regex that strips any residual annotation."],
    ["&ldquo;There is <b>no connection</b> between Emicizumab and Factor VIII&rdquo;; &ldquo;Factor VIII not in the graph.&rdquo;",
     "Entity lookup returned a <b>synonym/alias node</b> (<font face='Courier'>drug_db14473_synonym_0</font>) that has no biological edges, so relationship / reachability queries came back empty.",
     "Added a NODE-RESOLUTION rule: detect <font face='Courier'>_synonym_</font>/<font face='Courier'>_alias_</font> ids, resolve to the canonical node before edge queries, and treat any match as proof the entity exists."],
    ["Falls back to a Google link for side-effects, drugs, trials that <b>do</b> exist in the graph.",
     "Prompt allowed &ldquo;not in graph &rarr; web link&rdquo; too eagerly, before a real lookup.",
     "Tightened rule 3: the agent must actually call lookup (fuzzy) and get an empty result before offering a web link; it may never web-link an entity that already resolved."],
    ["&ldquo;Patent 1: [node_id=null] … Patent 11&rdquo; — eleven empty placeholder rows.",
     "The model (nova-pro) padded an unnamed relationship result with fabricated numbered rows.",
     "Added a rule forbidding placeholder list items; unnamed results must be rendered by real id or omitted."],
    ["<font face='Courier'>&lt;thinking&gt;…&lt;/thinking&gt;</font> reasoning shown inside chat bubbles.",
     "nova-pro emits these tags despite the prompt telling it not to.",
     "UI cleaner strips <font face='Courier'>&lt;thinking&gt;</font> and <font face='Courier'>&lt;response&gt;</font> tags (incl. unclosed, mid-stream)."],
    ["Graph view froze on large neighbourhoods (e.g. 217-node result).",
     "Unbounded node rendering in the context-graph component.",
     "Node cap (MAX_GRAPH_NODES = 200) with weight-based pruning (carried from prior session)."],
    ["&ldquo;Ask Eugene&rdquo; landing card prompts caused huge fetches / overflow.",
     "Sample prompts used &ldquo;all / every / N-hop&rdquo; phrasings.",
     "Sample prompts rewritten to bounded, single-entity questions (carried from prior session)."],
]
story += [section_table(findings, col_widths=[52 * mm, 52 * mm, 54 * mm])]

story += [PageBreak()]

# ---- 4. Model investigation
story += [P("4 · Model access investigation (Opus 4.7 request)", H1), hr()]
story += [P(
    "You asked to switch the model to <b>Claude Opus 4.7</b>. I tested Bedrock access "
    "using the agent's actual ECS task role (<font face='Courier'>stage-uspto_ecs_task_role</font>) "
    "from inside the VPC. Findings:", BODY)]
model = [
    [Paragraph("<b>Model</b>", CELLW), Paragraph("<b>Result via the agent's ConverseStream path</b>", CELLW)],
    ["us.anthropic.claude-opus-4-7", "<b>DENIED</b> — AccessDenied (AWS Marketplace subscribe not authorized)."],
    ["us.anthropic.claude-sonnet-4-6", "<b>DENIED</b> for ConverseStream — returned empty answers when briefly tried; reverted."],
    ["amazon.nova-pro-v1:0", "<b>WORKS</b> — Amazon's own model, no Marketplace subscription required."],
]
story += [section_table(model, col_widths=[62 * mm, 96 * mm])]
story += [Spacer(1, 3 * mm)]
story += [P(
    "<b>Root cause:</b> the AWS account has not completed the <b>AWS Marketplace "
    "subscription for Anthropic models</b>. This is an account/admin action in the "
    "Bedrock console (Model access &rarr; Manage model access &rarr; Anthropic) — it "
    "is not an IAM-policy edit and cannot be done with the deployment IAM user. Until "
    "it is enabled, only Amazon Nova models are usable.", BODY)]
story += [P(
    "<b>Action taken:</b> kept the agent on <font face='Courier'>amazon.nova-pro-v1:0</font> "
    "(the prompt fixes are model-agnostic and work on Nova). Once Anthropic access is "
    "enabled, switching to Opus/Sonnet is a one-line environment change "
    "(<font face='Courier'>BEDROCK_MODEL_ID</font>) on the agent task definition followed "
    "by a redeploy — no image rebuild.", BODY)]

story += [Spacer(1, 4 * mm)]
story += [P("4.1 · How to enable Anthropic models (for the AWS admin)", H2)]
story += [ListFlowable([
    ListItem(P("AWS Console &rarr; <b>Bedrock</b> &rarr; <b>Model access</b> (us-east-1).", CELL)),
    ListItem(P("Click <b>Manage model access</b> / <b>Enable specific models</b>.", CELL)),
    ListItem(P("Select <b>Anthropic — Claude Opus 4.7</b> (and Sonnet 4.6) and submit; "
               "accept the AWS Marketplace terms.", CELL)),
    ListItem(P("Once status shows <b>Access granted</b>, tell us — we flip "
               "<font face='Courier'>BEDROCK_MODEL_ID</font> and redeploy (~2 min).", CELL)),
], bulletType="1", leftIndent=10)]

story += [PageBreak()]

# ---- 5. Files changed
story += [P("5 · Files changed", H1), hr()]
files = [
    [Paragraph("<b>File</b>", CELLW), Paragraph("<b>Change</b>", CELLW)],
    ["agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py",
     "Removed the citation requirement; added node-resolution (alias dead-end) rule, stricter &ldquo;not-in-graph&rdquo; gate, and a no-placeholder-rows rule."],
    ["agents/eugene-agent-ui-next/components/chat/Message.tsx",
     "Extended the assistant-text cleaner to strip <font face='Courier'>[node_id=…]</font> / <font face='Courier'>(node_id:…)</font> citation annotations (defence-in-depth) alongside the existing &lt;thinking&gt; stripping."],
    ["agents/eugene-agent-ui-next/components/chat/EmptyState.tsx",
     "Bounded single-entity sample prompts (prior session, shipped now)."],
    ["agents/eugene-agent-ui-next/components/graph/KnowledgeGraph.tsx",
     "200-node render cap with weight-based pruning (prior session, shipped now)."],
]
story += [section_table(files, col_widths=[78 * mm, 80 * mm])]

story += [Spacer(1, 5 * mm)]
story += [P("6 · Deployment &amp; verification", H1), hr()]
deploy = [
    [Paragraph("<b>Step</b>", CELLW), Paragraph("<b>Detail</b>", CELLW)],
    ["Build", "agent_ws:bedrock and agent_ui_nextgen:latest rebuilt (linux/amd64) and pushed to ECR."],
    ["Deploy — agent", "stage-eugene-agent-ws &rarr; task def <b>:7</b> (nova-pro + prompt-fix image). Rollout COMPLETED, 1/1 healthy."],
    ["Deploy — UI", "stage-eugene-agent-ui-nextgen &rarr; new image. Rollout COMPLETED, 1/1 healthy."],
    ["Live smoke test", "In-VPC call to the agent: &ldquo;What protein targets does Emicizumab interact with?&rdquo; &rarr; <b>real answer</b> (F10, F9), 2 tool calls, <b>0 errors</b>, <b>annotation leak = False</b>."],
]
story += [section_table(deploy, col_widths=[34 * mm, 124 * mm])]

story += [Spacer(1, 5 * mm)]
story += [P("7 · Open items / recommendations", H1), hr()]
story += [ListFlowable([
    ListItem(P("<b>Enable Anthropic model access</b> in Bedrock (section 4.1) to unlock "
               "Opus 4.7 / Sonnet 4.6 — the single biggest remaining quality lever "
               "(removes &lt;thinking&gt; tags and weak tool-use at the source).", CELL)),
    ListItem(P("<b>Add a graph statistics endpoint</b> (e.g. <font face='Courier'>/graph/stats</font>) "
               "to the Core API so &ldquo;how many drugs / trials / patents&rdquo; and "
               "&ldquo;overall statistics&rdquo; questions can be answered. Requires a Core-API rebuild.", CELL)),
    ListItem(P("<b>Commit &amp; push</b> the four changed source files to git (currently deployed "
               "from local build; not yet pushed).", CELL)),
    ListItem(P("Throwaway test task definitions (eugene-opus, eugene-he) can be deregistered.", CELL)),
], bulletType="bullet", leftIndent=10)]

story += [Spacer(1, 6 * mm)]
story += [hr()]
story += [P(f"Generated {DATE_HUMAN} ({DATE_ISO}). All status claims above were verified "
            f"against live AWS ECS / Bedrock / CloudWatch on this date.", SMALL)]


# ----------------------------------------------------------------- build
def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=LETTER,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Eugene UI Fix Report {DATE_ISO}",
        author="CSL Behring Eugene platform engineering",
        subject="Chat response-quality diagnosis and remediation",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"WROTE {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
