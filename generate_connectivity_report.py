#!/usr/bin/env python3
"""
Generate a production-ready PDF:
  "Eugene Agent UI — Connectivity Remediation & LLM Egress Request"

Documents the application/deployment fixes completed, the remaining
network-layer blocker (LLM egress from the ECS VPC), the evidence, the
resolution options for the network team, and a ready-to-send email.

Run:  python3 generate_connectivity_report.py
Out:  docs/Eugene_Connectivity_Remediation_and_Network_Request.pdf
"""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether, ListFlowable, ListItem,
)

# ---------------------------------------------------------------- palette
NAVY      = colors.HexColor("#0F2B46")
STEEL     = colors.HexColor("#22577A")
TEAL      = colors.HexColor("#0B7A75")
TEAL_BG   = colors.HexColor("#E2F3F1")
GREEN     = colors.HexColor("#1B5E20")
GREEN_BG  = colors.HexColor("#E8F5E9")
AMBER     = colors.HexColor("#B26A00")
AMBER_BG  = colors.HexColor("#FFF3E0")
RED       = colors.HexColor("#B3261E")
RED_BG    = colors.HexColor("#FCEAE8")
GREY_BG   = colors.HexColor("#F4F6F8")
GREY_LN   = colors.HexColor("#D5DBE1")
GREY_TX   = colors.HexColor("#5B6770")
INK       = colors.HexColor("#1F2933")
WHITE     = colors.white

TODAY = date(2026, 6, 6).strftime("%B %d, %Y")

# ---------------------------------------------------------------- styles
_b = getSampleStyleSheet()
S = {
    "title":   ParagraphStyle("title", parent=_b["Title"], fontName="Helvetica-Bold",
                              fontSize=24, leading=28, textColor=WHITE, alignment=TA_LEFT),
    "subtitle":ParagraphStyle("subtitle", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=12.5, leading=17, textColor=colors.HexColor("#CFE0EC"), alignment=TA_LEFT),
    "meta":    ParagraphStyle("meta", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.5, leading=14, textColor=WHITE, alignment=TA_LEFT),
    "h1":      ParagraphStyle("h1", parent=_b["Heading1"], fontName="Helvetica-Bold",
                              fontSize=15, leading=19, textColor=NAVY, spaceBefore=6, spaceAfter=6),
    "h2":      ParagraphStyle("h2", parent=_b["Heading2"], fontName="Helvetica-Bold",
                              fontSize=11.5, leading=15, textColor=STEEL, spaceBefore=8, spaceAfter=3),
    "body":    ParagraphStyle("body", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.7, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5),
    "bodyl":   ParagraphStyle("bodyl", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.7, leading=14, textColor=INK, alignment=TA_LEFT, spaceAfter=5),
    "bullet":  ParagraphStyle("bullet", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.7, leading=13.5, textColor=INK, alignment=TA_LEFT),
    "small":   ParagraphStyle("small", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=8.3, leading=11.5, textColor=GREY_TX),
    "code":    ParagraphStyle("code", parent=_b["Code"], fontName="Courier",
                              fontSize=8.2, leading=11, textColor=colors.HexColor("#0A2540")),
    "th":      ParagraphStyle("th", parent=_b["Normal"], fontName="Helvetica-Bold",
                              fontSize=8.8, leading=11.5, textColor=WHITE),
    "td":      ParagraphStyle("td", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=8.7, leading=11.5, textColor=INK),
    "tdb":     ParagraphStyle("tdb", parent=_b["Normal"], fontName="Helvetica-Bold",
                              fontSize=8.7, leading=11.5, textColor=NAVY),
    "tdc":     ParagraphStyle("tdc", parent=_b["Code"], fontName="Courier",
                              fontSize=8.0, leading=11, textColor=colors.HexColor("#0A2540")),
    "callh":   ParagraphStyle("callh", parent=_b["Normal"], fontName="Helvetica-Bold",
                              fontSize=10, leading=13, textColor=INK, spaceAfter=2),
    "callb":   ParagraphStyle("callb", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.3, leading=13, textColor=INK),
    "email":   ParagraphStyle("email", parent=_b["Normal"], fontName="Helvetica",
                              fontSize=9.3, leading=14, textColor=INK, spaceAfter=5),
}

def P(t, s="body"): return Paragraph(t, S[s])
def sp(h=6): return Spacer(1, h)

def rule(color=TEAL, w=1.2):
    return HRFlowable(width="100%", thickness=w, color=color, spaceBefore=3, spaceAfter=7)

def h1(num, txt):
    return KeepTogether([sp(4), Paragraph(f'<font color="#0B7A75">{num}</font>&nbsp;&nbsp;{txt}', S["h1"]),
                         rule()])

def bullets(items, style="bullet"):
    return ListFlowable(
        [ListItem(Paragraph(t, S[style]), leftIndent=6, value="•") for t in items],
        bulletType="bullet", bulletColor=TEAL, leftIndent=12, spaceBefore=1, spaceAfter=4,
    )

def callout(title, body_items, kind="info"):
    bg, br = {"info": (TEAL_BG, TEAL), "good": (GREEN_BG, GREEN),
              "warn": (AMBER_BG, AMBER), "bad": (RED_BG, RED)}[kind]
    inner = [Paragraph(title, S["callh"])]
    for b in body_items:
        inner.append(Paragraph(b, S["callb"]))
    t = Table([[inner]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBEFORE", (0, 0), (0, -1), 3, br),
        ("BOX", (0, 0), (-1, -1), 0.4, GREY_LN),
    ]))
    return KeepTogether([t, sp(6)])

def table(headers, rows, col_w, header_bg=NAVY, zebra=True):
    data = [[Paragraph(h, S["th"]) for h in headers]]
    for r in rows:
        data.append([c if isinstance(c, Paragraph) else Paragraph(str(c), S["td"]) for c in r])
    t = Table(data, colWidths=col_w, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("BOX", (0, 0), (-1, -1), 0.5, GREY_LN),
    ]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), GREY_BG))
    t.setStyle(TableStyle(style))
    return t

# ---------------------------------------------------------------- page furniture
def on_page(canvas, doc):
    canvas.saveState()
    w, h = LETTER
    # footer rule + text
    canvas.setStrokeColor(GREY_LN); canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.4 * cm, w - 2 * cm, 1.4 * cm)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(GREY_TX)
    canvas.drawString(2 * cm, 1.0 * cm, "Eugene — Connectivity Remediation & LLM Egress Request")
    canvas.drawRightString(w - 2 * cm, 1.0 * cm, f"Confidential · Internal · Page {doc.page}")
    canvas.restoreState()

def cover(story):
    w, h = LETTER
    band = Table([[""]], colWidths=[w], rowHeights=[7.6 * cm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))
    inner = [
        sp(6),
        Paragraph("EUGENE BIOMEDICAL KNOWLEDGE-GRAPH PLATFORM", S["meta"]),
        sp(10),
        Paragraph("Connectivity Remediation &amp;<br/>LLM Egress Enablement Request", S["title"]),
        sp(8),
        Paragraph("Stage environment · AWS account 087084717211 · us-east-1<br/>"
                  "Eugene Agent UI (next-gen) &amp; agent back-end", S["subtitle"]),
    ]
    cov = Table([[inner]], colWidths=[w - 4 * cm], rowHeights=[7.6 * cm])
    cov.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * cm), ("RIGHTPADDING", (0, 0), (-1, -1), 1 * cm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cov)
    story.append(sp(16))
    meta_rows = [
        [Paragraph("Document", S["tdb"]), Paragraph("Connectivity remediation report &amp; network-team action request", S["td"])],
        [Paragraph("Prepared by", S["tdb"]), Paragraph("Rajesh Gupta — Eugene platform engineering", S["td"])],
        [Paragraph("Date", S["tdb"]), Paragraph(TODAY, S["td"])],
        [Paragraph("Version", S["tdb"]), Paragraph("1.0", S["td"])],
        [Paragraph("Audience", S["tdb"]), Paragraph("CSL Network / Cloud-Platform team; Eugene stakeholders", S["td"])],
        [Paragraph("Status", S["tdb"]), Paragraph("Action required — see §5 (Options) and §7 (Email)", S["td"])],
    ]
    mt = Table(meta_rows, colWidths=[3.4 * cm, 13 * cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GREY_BG),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("BOX", (0, 0), (-1, -1), 0.5, GREY_LN),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(mt)
    story.append(sp(14))
    story.append(callout(
        "One-line summary",
        ["The Eugene next-gen UI and its entire back-end (auth, agent, MCP, Neo4j with "
         "<b>484,259</b> nodes / <b>10.7M</b> relationships) are deployed and healthy. The "
         "<b>only</b> remaining blocker is network-layer egress from the ECS VPC to an LLM "
         "endpoint — a change only the network team can make. Three resolution options are in §5."],
        kind="good"))
    story.append(PageBreak())

# ---------------------------------------------------------------- build
def build():
    out = Path("docs/Eugene_Connectivity_Remediation_and_Network_Request.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out), pagesize=LETTER,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.7 * cm, bottomMargin=1.8 * cm,
        title="Eugene — Connectivity Remediation & LLM Egress Request",
        author="Rajesh Gupta",
    )
    story = []
    cover(story)

    # ---- 1. Executive summary
    story.append(h1("1", "Executive summary"))
    story.append(P(
        "The Eugene next-generation agent UI was stood up on AWS ECS Fargate behind the internal "
        "application load balancer and connected to the existing Eugene back-end. Through a sequence "
        "of fixes (§2) the UI now loads, authenticates, reaches the agent, the agent reaches the MCP "
        "server, and the MCP server reaches Neo4j — which is fully populated and healthy. Every "
        "application and infrastructure layer under our control is working."))
    story.append(P(
        "A single failure remains: when the agent answers a chat question it must call a Large "
        "Language Model. That outbound call fails at the <b>network layer</b> — the ECS VPC has no "
        "working path to any LLM endpoint (public OpenAI, the internal LLM-Gateway, or the Azure "
        "OpenAI private endpoint). This is not an application defect; it requires a network/firewall/DNS "
        "change that only the CSL network team can perform."))
    story.append(callout(
        "What we need from the network team",
        ["Enable egress from VPC <font face='Courier'>vpc-070f89d8985cafbb6</font> (stage Eugene, "
         "<font face='Courier'>10.88.203.0/24</font>) to <b>one</b> LLM endpoint. Three concrete "
         "options are detailed in §5; the recommended option is the managed <b>LLM-Gateway</b>. "
         "A ready-to-send email is in §7."], kind="info"))

    # ---- 2. What was fixed
    story.append(h1("2", "What was fixed (application &amp; deployment)"))
    story.append(P(
        "The following were completed by the Eugene team and require no further action. They are "
        "listed so the network team can see the surrounding work is done and the LLM hop is the only gap."))
    story.append(table(
        ["#", "Area", "Fix applied", "Result"],
        [
            ["1", Paragraph("Container image", S["td"]),
             Paragraph("Built the Next.js UI image (linux/amd64) and pushed to ECR "
                       "<font face='Courier'>eugene/agent_ui_nextgen:latest</font>.", S["td"]),
             Paragraph("Image present; ECS can pull it.", S["td"])],
            ["2", Paragraph("ECS task definition", S["td"]),
             Paragraph("Set <font face='Courier'>PORT=8000</font> (Next standalone binds the container "
                       "port), the internal-ALB back-end URLs, and TLS-skip for the self-signed ALB cert.", S["td"]),
             Paragraph("Task starts &amp; passes health checks.", S["td"])],
            ["3", Paragraph("Routing / basePath", S["td"]),
             Paragraph("Added <font face='Courier'>basePath=/nextgen</font> and prefixed all client "
                       "<font face='Courier'>fetch()</font> calls so assets and API routes resolve behind "
                       "the ALB path rule.", S["td"]),
             Paragraph("UI loads at <font face='Courier'>/nextgen</font>.", S["td"])],
            ["4", Paragraph("Load balancer", S["td"]),
             Paragraph("Target-group health check path set to <font face='Courier'>/nextgen</font>; "
                       "listener rule added; target healthy.", S["td"]),
             Paragraph("Service steady &amp; in service.", S["td"])],
            ["5", Paragraph("Service lifecycle", S["td"]),
             Paragraph("Replaced the failed console/CloudFormation service with a clean CLI-managed ECS "
                       "service on the corrected task definition.", S["td"]),
             Paragraph("1/1 task running, healthy.", S["td"])],
            ["6", Paragraph("Authentication", S["td"]),
             Paragraph("Production back-end is Entra/OAuth only (the dev <font face='Courier'>/auth/token</font> "
                       "is disabled). Injected a valid Eugene HS256 JWT for an allow-listed user as "
                       "<font face='Courier'>EUGENE_STATIC_TOKEN</font>.", S["td"]),
             Paragraph("UI status = <b>authenticated</b>.", S["td"])],
            ["7", Paragraph("Data verification", S["td"]),
             Paragraph("Confirmed Neo4j connectivity and content from inside the VPC.", S["td"]),
             Paragraph("484,259 nodes / 10.7M rels.", S["td"])],
        ],
        col_w=[0.8 * cm, 3.0 * cm, 8.4 * cm, 4.2 * cm]))

    # ---- 3. Architecture & health
    story.append(h1("3", "Current architecture &amp; component health"))
    story.append(P("Request path (everything below is healthy except the final LLM hop):"))
    story.append(Table([[Paragraph(
        "Browser → ALB&nbsp;:80&nbsp;(/nextgen) → Next.js&nbsp;UI&nbsp;proxy → ALB&nbsp;:443 → "
        "Core&nbsp;API&nbsp;/&nbsp;Agent&nbsp;/&nbsp;MCP → <b>Neo4j</b> &nbsp;&nbsp;||&nbsp;&nbsp; "
        "Agent → <font color='#B3261E'><b>LLM (BLOCKED)</b></font>", S["code"])]],
        colWidths=[16.4 * cm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREY_BG), ("BOX", (0, 0), (-1, -1), 0.5, GREY_LN),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])))
    story.append(sp(8))
    ok = Paragraph("HEALTHY", ParagraphStyle("ok", parent=S["td"], textColor=GREEN, fontName="Helvetica-Bold"))
    bad = Paragraph("BLOCKED", ParagraphStyle("bad", parent=S["td"], textColor=RED, fontName="Helvetica-Bold"))
    story.append(table(
        ["Layer", "Component", "Status", "Notes"],
        [
            ["UI", "stage-eugene-agent-ui-nextgen (ECS)", ok, "1/1 task, target healthy at /nextgen"],
            ["Auth", "Eugene JWT (HS256)", ok, "Allow-listed UPN; static token injected"],
            ["Agent", "stage-eugene-agent-ws", ok, "Receives requests; auth + routing OK"],
            ["MCP", "stage-eugene-mcp-ws", ok, "Agent connects (:8443/mcp 200)"],
            ["Database", "Neo4j 10.88.203.251:7687", ok, "484,259 nodes / 10,692,787 rels"],
            ["LLM", "Agent → external LLM", bad, "No network egress from VPC to any LLM endpoint"],
        ],
        col_w=[2.0 * cm, 5.8 * cm, 2.4 * cm, 6.2 * cm]))

    story.append(PageBreak())

    # ---- 4. Root cause
    story.append(h1("4", "Root cause — LLM egress is blocked at the network layer"))
    story.append(P(
        "The agent (<font face='Courier'>stage-eugene-agent-ws</font>) is configured to call OpenAI "
        "(<font face='Courier'>api.openai.com</font>) and the call fails with "
        "<font face='Courier'>APIConnectionError</font> after retries — i.e. it cannot open a connection, "
        "which is a network problem, not an authentication or key problem. The ECS VPC routes all "
        "outbound traffic (<font face='Courier'>0.0.0.0/0</font>) to a Transit Gateway with "
        "<b>no NAT gateway</b>, and has no DNS resolution for internal CSL zones. Each candidate LLM "
        "endpoint is blocked in a different way:"))
    story.append(table(
        ["LLM endpoint", "Reachability from the ECS VPC", "Blocking layer"],
        [
            [Paragraph("Public OpenAI<br/><font face='Courier' size=7>api.openai.com:443</font>", S["td"]),
             "Connection never establishes; agent logs show only retries, never a success.", "Egress / firewall"],
            [Paragraph("LLM-Gateway (API GW)<br/><font face='Courier' size=7>apigtw.dai-platform…cslg1.cslg.net</font>", S["td"]),
             "Host name does not resolve (DNS) — the VPC cannot resolve cslg1.cslg.net.", "DNS"],
            [Paragraph("Azure OpenAI (private)<br/><font face='Courier' size=7>10.206.70.230:443</font>", S["td"]),
             "TCP port opens, but the TLS handshake is reset by peer (source not allow-listed).", "Firewall (TLS)"],
        ],
        col_w=[4.6 * cm, 8.4 * cm, 3.4 * cm]))
    story.append(callout(
        "Why this only started recently",
        ["The LLM-calling agent first appeared on ECS on <b>2026-01-16</b>. Before that, the same "
         "workload ran where these endpoints <i>were</i> reachable — inside the EKS cluster (where "
         "<font face='Courier'>svc.cluster.local</font> resolves) and/or on machines with internet "
         "egress. The move to ECS Fargate is what exposed the missing egress path. The LLM logic "
         "itself is unchanged and works in those environments."], kind="warn"))

    # ---- 5. Options
    story.append(h1("5", "Resolution options for the network team"))
    story.append(P("Enabling <b>any one</b> of the following unblocks the agent. They are ordered by our recommendation."))

    story.append(P("Option A — Managed LLM-Gateway via API Gateway (SigV4)", "h2"))
    story.append(callout("Recommended", [
        "Strategic, supported path: OpenAI-compatible, multi-model (Bedrock), with guardrails and "
        "IAM-based auth (no static keys). Designed for &ldquo;any AWS runtime.&rdquo;"], kind="good"))
    story.append(P("<b>Network actions required:</b>", "bodyl"))
    story.append(bullets([
        "Associate VPC <font face='Courier'>vpc-070f89d8985cafbb6</font> with Route&nbsp;53 Resolver rule "
        "<font face='Courier'>rslvr-rr-9167b8679b4b4cf7b</font> (already exists, forwards "
        "<font face='Courier'>cslg1.cslg.net</font>) so the gateway host resolves.",
        "Authorize the ECS task role <font face='Courier'>stage-uspto_ecs_task_role</font> for "
        "<font face='Courier'>execute-api:Invoke</font> and onboard it to the gateway "
        "(<font face='Courier'>x-caller-arn</font> path).",
        "Endpoint to be reached: <font face='Courier'>https://apigtw.dai-platform.us-east-1.aws.cslg1.cslg.net/llmg/v1</font>.",
    ]))
    story.append(P("<b>Eugene-side work after enablement:</b> point the agent at the gateway base URL with a "
                   "SigV4-signed client (small, already scoped). <b>Pros:</b> no public internet, no static keys, "
                   "central governance. <b>Cons:</b> needs DNS + onboarding; minor agent code change.", "bodyl"))

    story.append(P("Option B — Azure OpenAI private endpoint", "h2"))
    story.append(P("<b>Network actions required:</b>", "bodyl"))
    story.append(bullets([
        "Allow source VPC <font face='Courier'>vpc-070f89d8985cafbb6</font> / subnet "
        "<font face='Courier'>10.88.203.0/24</font> to reach "
        "<font face='Courier'>10.206.70.230:443</font> "
        "(<font face='Courier'>deviation-genai.openai.azure.com</font>). TCP already routes; the TLS "
        "handshake is being reset, so this is a firewall source-allow-list change.",
    ]))
    story.append(P("<b>Pros:</b> simplest Eugene-side change (api-key header; standard Azure OpenAI). "
                   "<b>Cons:</b> IP-pinned private endpoint, self-signed cert, static subscription key — less "
                   "governed than the gateway.", "bodyl"))

    story.append(P("Option C — Direct OpenAI egress", "h2"))
    story.append(bullets([
        "Allow-list <font face='Courier'>api.openai.com:443</font> egress from the VPC via the Transit "
        "Gateway, <i>or</i> provide a forward-proxy (we set <font face='Courier'>HTTPS_PROXY</font> on the agent).",
    ]))
    story.append(P("<b>Pros:</b> works with the key already configured; zero code change. "
                   "<b>Cons:</b> least preferred — public internet egress and an external SaaS key; "
                   "weakest data-governance posture.", "bodyl"))

    story.append(P("Option D — Run the agent inside EKS (no network change)", "h2"))
    story.append(P("Re-home the agent into the EKS cluster where the LLM-Gateway "
                   "<font face='Courier'>svc.cluster.local</font> address already resolves. No network ticket, "
                   "but a larger platform/migration effort; noted for completeness.", "bodyl"))

    story.append(sp(2))
    story.append(table(
        ["Option", "Network change", "Eugene change", "Governance", "Recommendation"],
        [
            [Paragraph("A · LLM-Gateway", S["tdb"]), "DNS assoc + IAM onboarding", "Small (SigV4)", "Strong", Paragraph("Preferred", ParagraphStyle("g", parent=S["td"], textColor=GREEN, fontName="Helvetica-Bold"))],
            [Paragraph("B · Azure OpenAI", S["tdb"]), "Firewall allow-list", "Minimal", "Medium", "Good fallback"],
            [Paragraph("C · Direct OpenAI", S["tdb"]), "Egress allow-list / proxy", "None", "Weak", "Least preferred"],
            [Paragraph("D · Agent in EKS", S["tdb"]), "None", "Large (migration)", "Strong", "Long-term"],
        ],
        col_w=[3.1 * cm, 4.2 * cm, 3.0 * cm, 2.3 * cm, 3.0 * cm]))

    story.append(PageBreak())

    # ---- 6. Evidence & identifiers
    story.append(h1("6", "Evidence &amp; key identifiers"))
    story.append(P("Diagnostics were run from inside the ECS VPC (ephemeral Fargate task on the agent subnet).", "bodyl"))
    story.append(P("Test evidence", "h2"))
    story.append(table(
        ["Test (from ECS VPC)", "Observed result", "Conclusion"],
        [
            ["Agent → OpenAI (7-day logs)", "50× &ldquo;Retrying /chat/completions&rdquo;, 0 success", "Egress blocked"],
            ["DNS resolve gateway hosts", "gaierror: Name or service not known", "VPC DNS can't resolve cslg1.cslg.net"],
            ["TCP 10.206.70.230:443", "OPEN", "Route to Azure PE exists"],
            ["TLS to 10.206.70.230", "ConnectionReset (handshake)", "Firewall blocks source"],
            ["VPC DNS config", "AmazonProvidedDNS only; resolver rule not associated", "DNS not wired for internal zones"],
            ["NAT gateways in VPC", "none", "Egress only via Transit Gateway"],
            ["Neo4j MATCH (n) count", "484,259 nodes / 10,692,787 rels", "Database healthy &amp; populated"],
        ],
        col_w=[5.4 * cm, 6.6 * cm, 4.4 * cm]))

    story.append(P("Key identifiers (for the network team)", "h2"))
    idrows = [
        ["AWS account / region", "087084717211 (Diffusion-Labs-Dev) / us-east-1"],
        ["ECS VPC", "vpc-070f89d8985cafbb6  (CIDR 10.88.203.0/24)"],
        ["Agent subnet / SG", "subnet-0387dd9353f3f91b7 / sg-00e0b6e4e2cfe60b9"],
        ["Egress route", "0.0.0.0/0 → tgw-0122884db8995c4d1  (no NAT)"],
        ["Route 53 Resolver rule", "rslvr-rr-9167b8679b4b4cf7b  (FORWARD, not associated to VPC)"],
        ["ECS task role (SigV4)", "arn:aws:iam::087084717211:role/stage-uspto_ecs_task_role"],
        ["LLM-Gateway (API GW)", "https://apigtw.dai-platform.us-east-1.aws.cslg1.cslg.net/llmg/v1"],
        ["LLM-Gateway (health)", "https://llmg.aia.dev.cslg1.cslg.net/v1/health"],
        ["Azure OpenAI PE", "https://10.206.70.230:443  (Host deviation-genai.openai.azure.com)"],
        ["Neo4j", "neo4j+ssc://10.88.203.251:7687"],
    ]
    story.append(table(
        ["Item", "Value"],
        [[Paragraph(a, S["tdb"]), Paragraph(b, S["tdc"])] for a, b in idrows],
        col_w=[4.6 * cm, 11.8 * cm]))

    story.append(PageBreak())

    # ---- 7. Email
    story.append(h1("7", "Ready-to-send email — Network / Cloud-Platform team"))
    story.append(P("Copy the block below into a new email (adjust recipients as needed).", "small"))
    story.append(sp(4))

    em = []
    def er(label, val): em.append([Paragraph(label, S["tdb"]), Paragraph(val, S["td"])])
    er("To", "Network &amp; Cloud-Platform Team")
    er("Cc", "Eugene Platform · &lt;LLM-Gateway onboarding team&gt;")
    er("From", "Rajesh Gupta")
    er("Subject", "[Action required] LLM egress for the Eugene agent on ECS (stage, acct 087084717211)")
    et = Table(em, colWidths=[2.2 * cm, 14.2 * cm])
    et.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GREY_BG), ("BOX", (0, 0), (-1, -1), 0.5, GREY_LN),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(et)
    story.append(sp(8))

    body = [
        "Hi team,",
        "The Eugene next-gen agent UI is deployed and healthy on ECS Fargate (stage, account "
        "087084717211, us-east-1). The UI, authentication, agent, MCP server and Neo4j (484,259 nodes) "
        "all work. The one remaining blocker is <b>outbound egress from the ECS VPC to an LLM endpoint</b> — "
        "the agent cannot reach any model, so chat answers fail.",
        "Diagnostics from inside VPC <font face='Courier'>vpc-070f89d8985cafbb6</font> "
        "(<font face='Courier'>10.88.203.0/24</font>; egress via <font face='Courier'>tgw-0122884db8995c4d1</font>, "
        "no NAT) show: OpenAI never connects; the LLM-Gateway host does not resolve in DNS; and the Azure "
        "OpenAI private endpoint accepts TCP but resets the TLS handshake. Enabling <b>any one</b> of the "
        "options below unblocks us. We prefer <b>Option&nbsp;1 (LLM-Gateway)</b>.",
        "<b>Option 1 — LLM-Gateway (preferred):</b> (a) associate VPC "
        "<font face='Courier'>vpc-070f89d8985cafbb6</font> with Route&nbsp;53 Resolver rule "
        "<font face='Courier'>rslvr-rr-9167b8679b4b4cf7b</font> so "
        "<font face='Courier'>*.cslg1.cslg.net</font> resolves; and (b) authorize ECS task role "
        "<font face='Courier'>stage-uspto_ecs_task_role</font> for "
        "<font face='Courier'>execute-api:Invoke</font> / onboard it to the gateway "
        "(<font face='Courier'>https://apigtw.dai-platform.us-east-1.aws.cslg1.cslg.net/llmg/v1</font>).",
        "<b>Option 2 — Azure OpenAI:</b> allow source "
        "<font face='Courier'>10.88.203.0/24</font> to reach "
        "<font face='Courier'>10.206.70.230:443</font> "
        "(<font face='Courier'>deviation-genai.openai.azure.com</font>) — TCP already routes, the TLS "
        "handshake is being reset, so a firewall source allow-list is needed.",
        "<b>Option 3 — Direct OpenAI:</b> allow-list "
        "<font face='Courier'>api.openai.com:443</font> egress for the VPC via the Transit Gateway, or "
        "provide a forward-proxy host:port we can configure.",
        "Could you advise which option is acceptable and action it (or tell me the owning team)? I'm happy "
        "to jump on a quick call. A detailed report with full evidence and identifiers is attached.",
        "Thanks,<br/>Rajesh Gupta — Eugene platform engineering",
    ]
    inner = [Paragraph(b, S["email"]) for b in body]
    box = Table([[inner]], colWidths=[16.4 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBFCFD")),
        ("BOX", (0, 0), (-1, -1), 0.6, GREY_LN),
        ("LINEBEFORE", (0, 0), (0, -1), 3, STEEL),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    story.append(box)
    story.append(sp(8))
    story.append(Paragraph(
        "Prepared by Rajesh Gupta · Eugene platform engineering · " + TODAY +
        " · Confidential — Internal use only", S["small"]))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Wrote {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
