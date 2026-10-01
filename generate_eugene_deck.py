#!/usr/bin/env python3
"""Eugene app — quick presentation deck (16:9 PDF).

A self-contained slide deck rendered with reportlab. Dark theme matching the
Eugene UI (cyan -> blue -> magenta). Grounded in the live system: 129,375 nodes
/ 4,050,064 relationships, three sources (Eugene KG / Web / PubMed), source-
badged provenance, interactive reasoning graph.
"""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "docs" / "Eugene_App_Presentation.pdf"
W, H = 13.333 * inch, 7.5 * inch  # 16:9

# palette
BG = HexColor("#0B0E14")
PANEL = HexColor("#121826")
CYAN = HexColor("#1BB8E0")
BLUE = HexColor("#4256F5")
MAG = HexColor("#FF2A9D")
GREEN = HexColor("#22C55E")
TEXT = HexColor("#E6EAF2")
MUTED = HexColor("#93A0B4")
LINE = HexColor("#26304A")

ML = 0.95 * inch  # left margin


def bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # top accent bar (gradient feel via 3 segments)
    seg = W / 3
    for i, col in enumerate((CYAN, BLUE, MAG)):
        c.setFillColor(col)
        c.rect(i * seg, H - 6, seg, 6, fill=1, stroke=0)


def footer(c, n):
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(ML, 0.42 * inch, "Eugene — Biomedical Knowledge Intelligence")
    c.drawRightString(W - 0.7 * inch, 0.42 * inch, f"{n}")


def kicker(c, text, y=H - 1.15 * inch):
    c.setFillColor(CYAN)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(ML, y, text.upper())


def title(c, text, y=H - 1.75 * inch, size=30, color=TEXT):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    for line in text.split("\n"):
        c.drawString(ML, y, line)
        y -= size + 6
    return y


def bullets(c, items, y, gap=0.62 * inch, size=15, dot=BLUE, x=ML):
    for it in items:
        if isinstance(it, tuple):
            head, sub = it
        else:
            head, sub = it, None
        c.setFillColor(dot)
        c.circle(x + 5, y + 5, 4, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", size)
        c.drawString(x + 20, y, head)
        if sub:
            c.setFillColor(MUTED)
            c.setFont("Helvetica", size - 3)
            c.drawString(x + 20, y - (size + 1), sub)
            y -= gap + (size - 3)
        else:
            y -= gap
    return y


def stat_cards(c, cards, y):
    n = len(cards)
    pad = 0.25 * inch
    cw = (W - 2 * ML - (n - 1) * pad) / n
    ch = 1.7 * inch
    x = ML
    for (big, label, col) in cards:
        c.setFillColor(PANEL)
        c.roundRect(x, y - ch, cw, ch, 10, fill=1, stroke=0)
        c.setFillColor(col)
        c.rect(x, y - 6, cw, 6, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(x + cw / 2, y - ch / 2 + 6, big)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 12)
        c.drawCentredString(x + cw / 2, y - ch + 0.35 * inch, label)
        x += cw + pad


def chip(c, x, y, w, label, col):
    c.setFillColor(col)
    c.roundRect(x, y, w, 0.42 * inch, 8, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x + w / 2, y + 0.14 * inch, label)


def new(c):
    c.showPage()


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H))

    # 1 — Title
    bg(c)
    c.setFillColor(CYAN)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(ML, H - 2.6 * inch, "BIOMEDICAL KNOWLEDGE INTELLIGENCE")
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 64)
    c.drawString(ML, H - 3.7 * inch, "Eugene")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 18)
    c.drawString(ML, H - 4.4 * inch,
                 "A proprietary knowledge graph fused with live web & literature —")
    c.drawString(ML, H - 4.4 * inch - 26,
                 "answers you can see, trust, and trace.")
    for i, (lab, col) in enumerate(((" Eugene KG ", BLUE), (" Web ", CYAN), (" PubMed ", MAG))):
        chip(c, ML + i * 1.7 * inch, H - 5.4 * inch, 1.5 * inch, lab.strip(), col)
    footer(c, 1)
    new(c)

    # 2 — The problem
    bg(c)
    kicker(c, "Why Eugene")
    title(c, "Generic LLMs fall short in biomedicine")
    bullets(c, [
        ("No proprietary data", "They don't know your internal drugs, targets, trials, patents, or org portfolio"),
        ("They hallucinate links", "Confident but unverifiable drug–gene–disease connections"),
        ("Stale knowledge", "Frozen at a training cutoff — no live trials or this-month's papers"),
        ("No provenance", "You can't see where an answer came from or trace the reasoning"),
    ], y=H - 2.55 * inch, dot=MAG)
    footer(c, 2)
    new(c)

    # 3 — What is Eugene
    bg(c)
    kicker(c, "What it is")
    title(c, "One agent. Three sources. Full provenance.")
    bullets(c, [
        ("Eugene Knowledge Graph", "A 4M-relationship biomedical graph — drugs, genes, diseases, trials, patents, orgs"),
        ("Live Web", "Real-time ClinicalTrials.gov, Google Patents, and open-web fetch"),
        ("Live PubMed / Europe PMC", "Current biomedical literature with downloadable papers"),
        ("Every answer is source-badged", "Green badge shows Eugene KG / Web / PubMed — and an interactive reasoning graph"),
    ], y=H - 2.55 * inch, dot=BLUE)
    footer(c, 3)
    new(c)

    # 4 — The graph (stats)
    bg(c)
    kicker(c, "The knowledge graph")
    title(c, "PrimeKG-scale biomedical graph")
    stat_cards(c, [
        ("129,375", "Entities (nodes)", CYAN),
        ("4.05M", "Relationships", BLUE),
        ("10", "Entity types", MAG),
        ("31", "Relationship types", GREEN),
    ], y=H - 2.9 * inch)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 13)
    c.drawString(ML, H - 5.5 * inch,
                 "Entity types: drug · gene/protein · disease · pathway · anatomy · phenotype ·")
    c.drawString(ML, H - 5.5 * inch - 22,
                 "biological process · molecular function · cellular component · exposure")
    footer(c, 4)
    new(c)

    # 5 — Architecture
    bg(c)
    kicker(c, "How it works")
    title(c, "Architecture")
    tiers = [
        ("Next.js UI", "Chat + interactive Cytoscape reasoning graph, source tabs", CYAN),
        ("Agent (Strands + LLM)", "Plans, routes to the selected source, calls tools, cites sources", BLUE),
        ("MCP tools + live tools", "Graph lookups/paths/facts · PubMed · ClinicalTrials · Patents", MAG),
        ("Neo4j + GDS", "4M-edge graph, fulltext-indexed lookups, graph-data-science algorithms", GREEN),
    ]
    y = H - 2.55 * inch
    for name, desc, col in tiers:
        c.setFillColor(PANEL)
        c.roundRect(ML, y - 0.75 * inch, W - 2 * ML, 0.72 * inch, 8, fill=1, stroke=0)
        c.setFillColor(col)
        c.roundRect(ML, y - 0.75 * inch, 0.12 * inch, 0.72 * inch, 4, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(ML + 0.4 * inch, y - 0.32 * inch, name)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 12)
        c.drawString(ML + 3.6 * inch, y - 0.32 * inch, desc)
        y -= 0.92 * inch
    footer(c, 5)
    new(c)

    # 6 — Strengths
    bg(c)
    kicker(c, "Real strengths")
    title(c, "What only Eugene can do")
    bullets(c, [
        ("Multi-hop reasoning", "drug → target protein → disease, chained automatically"),
        ("Explainable paths", "Shortest path between any two entities, visualized"),
        ("Drug intelligence", "Targets, interactions, contraindications, side effects"),
    ], y=H - 2.55 * inch, dot=CYAN, x=ML)
    bullets(c, [
        ("Live evidence", "Recruiting trials & this-year's papers, on demand"),
        ("Provenance built-in", "Source-badged answers + evidence chains"),
        ("See & download", "Reasoning graph + downloadable research papers"),
    ], y=H - 2.55 * inch, dot=MAG, x=ML + 6.0 * inch)
    footer(c, 6)
    new(c)

    # 7 — See it / trust it / trace it
    bg(c)
    kicker(c, "Experience")
    title(c, "See it. Trust it. Trace it.")
    cards = [
        ("See it", "Interactive reasoning graph — expand, collapse, find paths, 20 nodes at a time", CYAN),
        ("Trust it", "Green source badge on every answer: Eugene KG / Web / PubMed", GREEN),
        ("Trace it", "Evidence chains + downloadable papers (Read / Download PDF)", MAG),
    ]
    n = len(cards)
    pad = 0.3 * inch
    cw = (W - 2 * ML - (n - 1) * pad) / n
    ch = 2.7 * inch
    x = ML
    y = H - 2.7 * inch
    for head, body, col in cards:
        c.setFillColor(PANEL)
        c.roundRect(x, y - ch, cw, ch, 12, fill=1, stroke=0)
        c.setFillColor(col)
        c.rect(x, y - 6, cw, 6, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(x + 0.3 * inch, y - 0.7 * inch, head)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 12.5)
        # wrap body
        words = body.split()
        line = ""
        yy = y - 1.15 * inch
        for w in words:
            if c.stringWidth(line + " " + w, "Helvetica", 12.5) > cw - 0.6 * inch:
                c.drawString(x + 0.3 * inch, yy, line)
                yy -= 18
                line = w
            else:
                line = (line + " " + w).strip()
        c.drawString(x + 0.3 * inch, yy, line)
        x += cw + pad
    footer(c, 7)
    new(c)

    # 8 — Demo
    bg(c)
    kicker(c, "Demo narrative")
    title(c, 'One theme, three sources: "Clozapine"')
    rows = [
        ("Eugene KG", BLUE, "What proteins does Clozapine target, and what are its side effects?"),
        ("Web", CYAN, "List current recruiting clinical trials for clozapine, with phases & sponsors."),
        ("PubMed", MAG, "Find recent papers on clozapine-induced agranulocytosis — with links."),
    ]
    y = H - 2.7 * inch
    for tab, col, q in rows:
        chip(c, ML, y - 0.42 * inch, 1.7 * inch, tab, col)
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 15)
        c.drawString(ML + 2.0 * inch, y - 0.28 * inch, q)
        y -= 1.0 * inch
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(ML, y - 0.1 * inch,
                 "Same question, three lenses — proprietary graph + live web + live literature, each source-badged.")
    footer(c, 8)
    new(c)

    # 9 — Closing
    bg(c)
    c.setFillColor(CYAN)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(ML, H - 2.4 * inch, "THE BOTTOM LINE")
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(ML, H - 3.3 * inch, "Deep biomedical reasoning,")
    c.drawString(ML, H - 3.3 * inch - 42, "made visible and trustworthy.")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 16)
    c.drawString(ML, H - 4.6 * inch,
                 "Eugene fuses a 4M-relationship knowledge graph with live web & PubMed —")
    c.drawString(ML, H - 4.6 * inch - 24,
                 "answering questions a generic LLM can't, with full, traceable provenance.")
    for i, (lab, col) in enumerate(((" Eugene KG ", BLUE), (" Web ", CYAN), (" PubMed ", MAG))):
        chip(c, ML + i * 1.7 * inch, H - 5.6 * inch, 1.5 * inch, lab.strip(), col)
    footer(c, 9)
    new(c)

    c.save()
    print(f"✔ deck written: {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
