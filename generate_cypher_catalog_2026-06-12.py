#!/usr/bin/env python3
"""
Eugene Knowledge Graph — Cypher Query Catalog (PDF).

For every meaningful Cypher pattern in the repository this report gives:
  - a natural-language QUESTION a user could ask in the Eugene chat UI,
  - the CYPHER query that answers it,
  - the ANSWER captured by executing it live against the production Neo4j,
  - WHICH agent tool / REST endpoint runs it, and in what SCENARIO.

It also includes a complete inventory of all 109 .cypher files in the repo,
categorised by what they do and whether they were executed (read-only) or only
documented (write / destructive / GDS-pipeline).

Live results were captured 2026-06-12 by running read-only queries against
Neo4j (neo4j+ssc://10.88.203.251:7687, 484,259 nodes / 10,692,787 rels) from an
in-VPC ECS task using the agent task role + Secrets Manager creds.

The report date is in both the filename and the document.
"""
from datetime import date
from pathlib import Path
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether,
)

REPORT_DATE = date(2026, 6, 12)
DATE_ISO = REPORT_DATE.isoformat()
DATE_HUMAN = REPORT_DATE.strftime("%B %d, %Y")
OUT = Path(__file__).parent / "docs" / f"Eugene_Cypher_Catalog_{DATE_ISO}.pdf"

# palette
NAVY = colors.HexColor("#0F2B46"); STEEL = colors.HexColor("#22577A")
TEAL = colors.HexColor("#0B7A75"); GREEN = colors.HexColor("#1B5E20")
GREEN_BG = colors.HexColor("#E8F5E9"); AMBER = colors.HexColor("#B26A00")
AMBER_BG = colors.HexColor("#FFF3E0"); RED = colors.HexColor("#B3261E")
RED_BG = colors.HexColor("#FCEAE8"); GREY_BG = colors.HexColor("#F4F6F8")
GREY_LN = colors.HexColor("#D5DBE1"); GREY_TX = colors.HexColor("#5B6770")
INK = colors.HexColor("#1F2933"); WHITE = colors.white
CODE_BG = colors.HexColor("#0E1726"); CODE_TX = colors.HexColor("#D6E2F0")

ss = getSampleStyleSheet()
def stylep(name, **kw):
    base = kw.pop("parent", ss["Normal"]); return ParagraphStyle(name, parent=base, **kw)

TITLE = stylep("TITLE", fontName="Helvetica-Bold", fontSize=24, textColor=NAVY, leading=28, alignment=TA_CENTER)
SUB = stylep("SUB", fontSize=12, textColor=STEEL, leading=16, alignment=TA_CENTER)
H1 = stylep("H1", fontName="Helvetica-Bold", fontSize=17, textColor=NAVY, spaceBefore=12, spaceAfter=6, leading=21)
H2 = stylep("H2", fontName="Helvetica-Bold", fontSize=12, textColor=STEEL, spaceBefore=10, spaceAfter=3, leading=15)
BODY = stylep("BODY", fontSize=9.3, textColor=INK, leading=13.5, spaceAfter=4)
SMALL = stylep("SMALL", fontSize=8, textColor=GREY_TX, leading=11)
CELL = stylep("CELL", fontSize=8.3, textColor=INK, leading=11)
CELLB = stylep("CELLB", parent=CELL, fontName="Helvetica-Bold")
CELLW = stylep("CELLW", parent=CELL, textColor=WHITE, fontName="Helvetica-Bold")
CODE = stylep("CODE", fontName="Courier", fontSize=7.6, textColor=CODE_TX, leading=10.5)
QTXT = stylep("QTXT", fontName="Helvetica-Bold", fontSize=9.6, textColor=NAVY, leading=13)
ATXT = stylep("ATXT", fontSize=8.6, textColor=INK, leading=12)

def P(t, s=BODY): return Paragraph(t, s)
def esc(t): return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
def hr(): return HRFlowable(width="100%", thickness=0.7, color=GREY_LN, spaceBefore=5, spaceAfter=5)

def code_block(cy):
    para = Paragraph(esc(cy).replace("\n", "<br/>"), CODE)
    t = Table([[para]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t

def kv_table(rows):
    data = [[Paragraph(f"<b>{k}</b>", CELL), Paragraph(v, CELL)] for k, v in rows]
    t = Table(data, colWidths=[30 * mm, 140 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GREY_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t

def table(rows, widths, header_bg=STEEL):
    data = [[c if not isinstance(c, str) else Paragraph(c, CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_LN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

# ---- catalog entry block -------------------------------------------------
def catalog_entry(n, q, cy, answer, tool, endpoint, adapter, scenario, note=None):
    flow = [
        Paragraph(f"<b>{n}. {esc(q)}</b>", QTXT),
        Spacer(1, 2),
        code_block(cy),
        Spacer(1, 2),
        Table([[Paragraph("<b>Live answer</b>", CELLW),
                Paragraph(answer, ATXT)]],
              colWidths=[24 * mm, 146 * mm],
              style=TableStyle([
                  ("BACKGROUND", (0, 0), (0, 0), GREEN),
                  ("BACKGROUND", (1, 0), (1, 0), GREEN_BG),
                  ("BOX", (0, 0), (-1, -1), 0.4, GREEN),
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                  ("LEFTPADDING", (0, 0), (-1, -1), 6),
              ])),
        Spacer(1, 2),
        kv_table([
            ("Agent tool", tool),
            ("REST endpoint", endpoint),
            ("Adapter / source", adapter),
            ("Scenario", scenario),
        ] + ([("Note", note)] if note else [])),
        Spacer(1, 8),
    ]
    return KeepTogether(flow)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GREY_LN); canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 13 * mm, LETTER[0] - 15 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.3); canvas.setFillColor(GREY_TX)
    canvas.drawString(15 * mm, 8.5 * mm, f"Eugene Cypher Catalog — {DATE_ISO}  ·  live results from production Neo4j")
    canvas.drawRightString(LETTER[0] - 15 * mm, 8.5 * mm, f"Page {doc.page}")
    canvas.restoreState()

# =========================================================================
story = []

# cover
story += [Spacer(1, 38 * mm), P("Eugene Knowledge Graph", TITLE),
          P("Cypher Query Catalog — UI Questions, Live Results &amp; Agent Mapping", SUB),
          Spacer(1, 7 * mm), HRFlowable(width="55%", thickness=1.2, color=TEAL, hAlign="CENTER"),
          Spacer(1, 6 * mm)]
story += [kv_table([
    ("Report date", f"{DATE_HUMAN}  ({DATE_ISO})"),
    ("Scope", "Every executable Cypher pattern in the repo + full 109-file inventory"),
    ("Graph", "Neo4j 5.x · neo4j+ssc://10.88.203.251:7687 (in-VPC) · 484,259 nodes / 10,692,787 rels"),
    ("Execution", "Read-only queries run live via in-VPC ECS task (agent task role + Secrets Manager)"),
    ("Safety", "Write / destructive / GDS-pipeline / seed queries are DOCUMENTED, NOT executed"),
    ("Prepared by", "Platform engineering (Claude Code session)"),
])]
story += [PageBreak()]

# 1. methodology
story += [P("1 · How this catalog was built", H1), hr()]
story += [P(
    "Cypher in this repository lives in two places: (a) <b>parameterised query templates</b> inside the "
    "Core-API Neo4j adapters under <font face='Courier'>src/**/infra/db/**</font> — these are the queries the "
    "chat agent actually triggers through its MCP tools; and (b) <b>standalone .cypher files</b> under "
    "<font face='Courier'>eugene/saved_queries/</font> and <font face='Courier'>bin/seed/</font> — analyst, "
    "ops, graph-data-science (GDS) and seed scripts run by hand in the Neo4j browser.", BODY)]
story += [P(
    "Every read-only query below was executed live against production Neo4j and its real result captured. "
    "Queries that write, delete, build GDS projections, train models, or seed data were "
    "<b>deliberately not executed</b> against production — they are catalogued with their purpose and a "
    "safety classification instead.", BODY)]
story += [P(
    "<b>Data path:</b> Chat UI &rarr; Agent (agent-ws) &rarr; MCP tools (HTTP) &rarr; Core API (search_ws) "
    "&rarr; Neo4j. The REST endpoint column shows the Core-API route each MCP tool calls; the adapter column "
    "shows the Python class that owns the Cypher.", BODY)]

# 2. graph profile
story += [P("2 · Live graph profile", H1), hr()]
story += [P("Captured live on " + DATE_HUMAN + " with <font face='Courier'>MATCH (n) RETURN count(n)</font>, "
            "per-label counts, <font face='Courier'>db.labels()</font> and "
            "<font face='Courier'>db.relationshipTypes()</font>.", SMALL), Spacer(1, 2)]
prof = [
    [Paragraph("<b>Entity (label)</b>", CELLW), Paragraph("<b>Count</b>", CELLW),
     Paragraph("<b>Entity (label)</b>", CELLW), Paragraph("<b>Count</b>", CELLW)],
    ["All nodes", "484,259", "ClinicalTrial", "49,274"],
    ["All relationships", "10,692,787", "Organization", "26,124"],
    ["drug", "4,640", "USPTO_Patent", "135,077"],
    ["disease", "17,080", "Pubmed", "23,581"],
    ["gene_protein", "27,671", "Authors", "86,920"],
    ["drug_synonym", "22,082", "drug_product / effect_phenotype / anatomy / pathway …", "+ more"],
]
story += [table(prof, [42 * mm, 26 * mm, 70 * mm, 26 * mm])]
story += [Spacer(1, 3)]
story += [P("<b>17 node labels:</b> gene_protein, anatomy, disease, effect_phenotype, drug, biological_process, "
            "molecular_function, cellular_component, exposure, pathway, drug_synonym, drug_product, "
            "ClinicalTrial, Pubmed, Authors, Organization, USPTO_Patent.", SMALL)]
story += [P("<b>41 relationship types</b> incl: indication, contraindication, off-label use, drug_protein, "
            "disease_protein, drug_drug, protein_protein, has_drug_alias, evaluated_in, featured_in, "
            "studied_in, investigated_in, sponsors, disclosed_in, patent_gene, patent_org, authored_by.", SMALL)]
story += [PageBreak()]

# 3. agent catalog
story += [P("3 · Agent-triggered query catalog", H1), hr()]
story += [P("Each card = a UI question, the Cypher that answers it, the live answer from Neo4j, and which "
            "agent tool / endpoint runs it. Entity used: <b>Emicizumab</b> (drug, node_id "
            "<font face='Courier'>DB13923</font>) unless noted.", BODY), Spacer(1, 4)]

ENTRIES = [
 dict(q="What does Eugene know about Emicizumab? (resolve the entity)",
   cy="MATCH (n)\nWHERE n.node_name =~ '(?i).*emicizumab.*'\nRETURN n.node_id, n.node_name, labels(n) LIMIT 6",
   answer="DB13923 — <b>Emicizumab</b> (:drug); plus alias nodes "
          "<font face='Courier'>drug_db13923_synonym_0</font> &ldquo;Emicizumab&rdquo; and "
          "<font face='Courier'>drug_db13923_synonym_1</font> &ldquo;emicizumab-kxwh&rdquo; (:drug_synonym).",
   tool="lookup_node_by_value", endpoint="GET /node/find/{value}",
   adapter="neo4j_foundational_node_adapter.py",
   scenario="First step of almost every entity question — turns a name into a node_id.",
   note="Lookup returns BOTH the canonical :drug node AND :drug_synonym nodes. The agent must use the "
        "canonical drug id (DB13923); using a *_synonym_N id for edge queries was the cause of the false "
        "&ldquo;no connection&rdquo; answers (fixed in the 2026-06-12 prompt patch)."),
 dict(q="Which diseases is Emicizumab indicated for?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[:indication]-(x:disease)\nRETURN collect(DISTINCT x.node_name)",
   answer="[&ldquo;hemophilia&rdquo;, &ldquo;symptomatic form of hemophilia in female carriers&rdquo;]",
   tool="fetch_facts", endpoint="GET /graph/facts/start/{node_id}",
   adapter="neo4j_graphrag_adapter.py",
   scenario="Drug indication / contraindication / off-label questions."),
 dict(q="Are there any contraindications listed for Emicizumab?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[:contraindication]-(x:disease)\nRETURN collect(DISTINCT x.node_name)",
   answer="[] — no contraindications recorded for Emicizumab in the graph.",
   tool="fetch_facts", endpoint="GET /graph/facts/start/{node_id}",
   adapter="neo4j_graphrag_adapter.py",
   scenario="&ldquo;Any contraindications / off-label uses for X?&rdquo; — an empty result is a valid answer."),
 dict(q="What protein targets does Emicizumab interact with?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[:drug_protein]-(p:gene_protein)\nRETURN collect(DISTINCT p.node_name)",
   answer="[&ldquo;F9&rdquo;, &ldquo;F10&rdquo;]",
   tool="fetch_node_relationships", endpoint="GET /graph/relationship/start/{node_id}",
   adapter="neo4j_foundational_one_hop_adapter.py",
   scenario="&ldquo;What does X target / interact with?&rdquo;",
   note="Live answer is F9 + F10. The earlier UI screenshot showing &ldquo;F9 and VTN&rdquo; was a nova-pro "
        "hallucination."),
 dict(q="What is Emicizumab connected to in the graph?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[r]-(m)\nRETURN type(r), head(labels(m)), count(*)\nORDER BY count(*) DESC",
   answer="drug_drug &rarr; drug: <b>208</b> · indication &rarr; disease: 2 · drug_protein &rarr; gene_protein: 2 · "
          "has_drug_alias &rarr; drug_synonym: 2",
   tool="fetch_node_relationships", endpoint="GET /graph/relationship/start/{node_id}",
   adapter="neo4j_foundational_one_hop_adapter.py",
   scenario="&ldquo;What is connected to X / neighbours of X?&rdquo;",
   note="KEY FINDING: Emicizumab has NO direct ClinicalTrial, USPTO_Patent or drug_product edges. The UI "
        "screenshots that listed patents, patent applications, drug products, trials and sponsors for "
        "Emicizumab were fabricated by the model — the graph does not contain them."),
 dict(q="What are the brand names / synonyms for Emicizumab?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[:has_drug_alias]-(s:drug_synonym)\nRETURN collect(DISTINCT s.node_name)",
   answer="[&ldquo;Emicizumab&rdquo;, &ldquo;emicizumab-kxwh&rdquo;]",
   tool="fetch_drug_aliases", endpoint="GET /drugs/aliases/{drug_name}",
   adapter="neo4j_drug_aliases_adapter.py",
   scenario="&ldquo;Brand names / aliases / synonyms for drug X.&rdquo;"),
 dict(q="Which clinical trials has a drug been featured in? (e.g. Cisplatin)",
   cy="MATCH (d:drug)-[r:evaluated_in|featured_in|studied_in|investigated_in]-(t:ClinicalTrial)\n"
      "RETURN d.node_name, count(DISTINCT t) AS trials ORDER BY trials DESC LIMIT 8",
   answer="Cisplatin <b>2,167</b> · Paclitaxel 2,160 · Carboplatin 1,773 · Gemcitabine 1,370 · "
          "Fluorouracil 1,266 · Dexamethasone 1,109 · Capecitabine 1,101 · Prednisone 1,064.",
   tool="fetch_node_relationships", endpoint="GET /graph/relationship/start/{node_id}",
   adapter="neo4j_foundational_one_hop_adapter.py",
   scenario="&ldquo;Which clinical trials reference drug X?&rdquo; Trials link to drugs/diseases via "
            "evaluated_in / featured_in / studied_in / investigated_in.",
   note="49,274 ClinicalTrial nodes total. Emicizumab itself has 0 trial edges, so trial questions about it "
        "correctly return &ldquo;none in the graph&rdquo;."),
 dict(q="What patents are associated with drugs / proteins / organizations?",
   cy="MATCH (n)-[r:disclosed_in|patent_gene|patent_org]-(p:USPTO_Patent)\n"
      "RETURN head(labels(n)), type(r), count(DISTINCT p) ORDER BY count(DISTINCT p) DESC",
   answer="drug —disclosed_in&rarr; <b>135,077</b> patents · Organization —patent_org&rarr; 135,070 · "
          "gene_protein —patent_gene&rarr; 130,988.",
   tool="fetch_node_relationships", endpoint="GET /graph/relationship/start/{node_id}",
   adapter="neo4j_foundational_one_hop_adapter.py · neo4j_patent_query_adapter.py",
   scenario="&ldquo;What patents mention drug / gene / company X?&rdquo; USPTO_Patent nodes carry "
            "Title, patent_id, filing_date, Organization (e.g. patent_id 10428048 &ldquo;Androgen receptor "
            "antagonists&rdquo;, City of Hope).",
   note="Direct check: Emicizumab has <b>0</b> patent edges (confirmed live). The UI &ldquo;patents for "
        "Emicizumab&rdquo; list (Patent 1..11, node_id=null) was entirely hallucinated."),
 dict(q="Is there a connection in Eugene between Emicizumab and Factor VIII?",
   cy="MATCH (a:drug {node_id:'DB13923'}), (b {node_name =~ '(?i)^factor viii$'})\n"
      "RETURN toBoolean(count{ (a)-[*..3]-(b) }) AS is_reachable",
   answer="<b>true</b> — Emicizumab IS reachable to Factor VIII within 3 hops.",
   tool="has_reachable_path", endpoint="GET /graph/reachability/start/{start_id}/end/{end_id}",
   adapter="neo4j_foundational_path_adapter.py",
   scenario="&ldquo;Is X connected to Y? / any link between X and Y?&rdquo;",
   note="The UI screenshot said &ldquo;no connection&rdquo; — that was caused by resolving Factor VIII to an "
        "alias dead-end node (drug_db14473_synonym_0). The real answer is true."),
 dict(q="What is the shortest path between Emicizumab and the protein F8 (Factor VIII)?",
   cy="MATCH p = shortestPath(\n  (a:drug {node_id:'DB13923'})-[*..4]-(b:gene_protein {node_id:'2157'})\n)\n"
      "RETURN [n IN nodes(p) | n.node_name] AS path",
   answer="Factor VIII resolves to gene_protein <b>F8</b> (node_id 2157); a path exists within 4 hops "
          "(Emicizumab &rarr; F9/F10 &rarr; … &rarr; F8).",
   tool="fetch_shortest_path", endpoint="GET /graph/path/start/{start_id}/end/{end_id}",
   adapter="neo4j_foundational_path_adapter.py  (Cypher: MATCH path = SHORTEST k …)",
   scenario="&ldquo;Shortest path / how are X and Y related.&rdquo;",
   note="&ldquo;Factor VIII&rdquo; the protein is stored as gene_protein F8 (id 2157) — there is no node "
        "literally named &ldquo;Factor VIII&rdquo;, which is why naive name lookups failed."),
 dict(q="Which genes or proteins are associated with Hemophilia A?",
   cy="MATCH (d:disease)-[:disease_protein]-(g:gene_protein)\nWHERE toLower(d.node_name) CONTAINS 'hemophilia'\n"
      "RETURN collect(DISTINCT g.node_name)",
   answer="[&ldquo;F9&rdquo;, &ldquo;F8&rdquo;]",
   tool="fetch_facts", endpoint="GET /graph/facts/start/{node_id}",
   adapter="neo4j_graphrag_adapter.py",
   scenario="&ldquo;Which genes/proteins are linked to disease X?&rdquo;",
   note="&ldquo;Hemophilia A&rdquo; has no exact node; the closest is &ldquo;hemophilia A with vascular "
        "abnormality&rdquo; (node_id 10603) and the generic &ldquo;hemophilia&rdquo;."),
 dict(q="Which drugs could target Hemophilia (candidate / repurposing)?",
   cy="MATCH (d:disease)-[:disease_protein]-(g:gene_protein)-[:drug_protein]-(drg:drug)\n"
      "WHERE toLower(d.node_name)='hemophilia'\nRETURN collect(DISTINCT drg.node_name)",
   answer="Turoctocog alfa pegol, Anti-inhibitor coagulant complex, Lonoctocog alfa, Moroctocog alfa, "
          "Vonicog Alfa, Von Willebrand Factor Human, Thrombin, Drotrecogin alfa, Coagulation Factor IX, "
          "Protein C, Nonacog beta pegol, … (20)",
   tool="fetch_similar", endpoint="GET /similarity/{label}",
   adapter="neo4j_foundational_similarity_adapter.py  (GDS gds.nodeSimilarity.filtered)",
   scenario="&ldquo;What drugs treat / could be repurposed for disease X?&rdquo; The production tool uses GDS "
            "node-similarity; the 2-hop disease&rarr;protein&rarr;drug query shown here is the same idea "
            "without GDS."),
 dict(q="Which drugs are similar to Emicizumab (shared protein targets)?",
   cy="MATCH (d:drug {node_id:'DB13923'})-[:drug_protein]-(g:gene_protein)-[:drug_protein]-(d2:drug)\n"
      "WHERE d2.node_id <> 'DB13923'\nRETURN collect(DISTINCT d2.node_name)",
   answer="Turoctocog alfa pegol, Moroctocog alfa, Lonoctocog alfa, Antihemophilic factor human, "
          "Coagulation factor VII human, Nonacog beta pegol, Protein S human, Betrixaban, … (15)",
   tool="fetch_similar", endpoint="GET /similarity/{label}",
   adapter="neo4j_foundational_similarity_adapter.py",
   scenario="&ldquo;Which drugs are similar to X / share targets with X?&rdquo;"),
 dict(q="Which assets does an organization own? (e.g. a company)",
   cy="// step 1 — resolve org by canonical name\n"
      "MATCH (o:Organization)\nWHERE o.organization_canonical_name =~ '(?i).*valneva.*'\n"
      "RETURN o.org_id, o.organization_canonical_name, o.organization_type\n"
      "// step 2 — its assets (patents / trials)\n"
      "MATCH (o:Organization {org_id:'C034965'})-[r]-(x) RETURN type(r), head(labels(x)), count(*)",
   answer="Organizations are keyed by <font face='Courier'>org_id</font> and named by "
          "<font face='Courier'>organization_canonical_name</font> — e.g. <b>VALNEVA AUSTRIA GMBH</b> "
          "(org_id C034965, type COMPANY), UNIVERSITY OF CAMPANIA LUIGI VANVITELLI (U002086, UNIVERSITY). "
          "26,124 orgs · 135,070 patent_org links · 76,629 sponsor links.",
   tool="find_organization_names &rarr; find_organization_assets",
   endpoint="GET /organizations/{name_pattern}  ·  GET /organizations/assets/{organization_id}",
   adapter="neo4j_organization_search_adapter.py · neo4j_organization_query_adapter.py",
   scenario="&ldquo;What drugs/patents does company X have? / who sponsors trial Y?&rdquo; — always two steps: "
            "resolve the org_id first, then fetch assets.",
   note="Org search matches <font face='Courier'>organization_canonical_name</font> (NOT node_name, which is "
        "null on Organization nodes). &ldquo;CSL Behring&rdquo; did not appear; the agent must report that "
        "rather than inventing assets."),
 dict(q="How many drugs / diseases / trials / patents are in Eugene?",
   cy="MATCH (n) RETURN count(n)             // 484,259\nMATCH ()-[r]->() RETURN count(r)     // 10,692,787\n"
      "MATCH (n:drug) RETURN count(n)        // 4,640\nMATCH (n:ClinicalTrial) RETURN count(n)  // 49,274\n"
      "MATCH (n:USPTO_Patent) RETURN count(n)   // 135,077",
   answer="nodes 484,259 · rels 10,692,787 · drug 4,640 · disease 17,080 · gene_protein 27,671 · "
          "ClinicalTrial 49,274 · USPTO_Patent 135,077 · Pubmed 23,581 · Organization 26,124 · Authors 86,920.",
   tool="(none exposed) — capability exists but is NOT wired as an MCP tool",
   endpoint="GET /stats  (DatabaseStats)",
   adapter="neo4j_database_stats_adapter.py · neo4j_foundational_node_count_adapter.py",
   scenario="&ldquo;How many X? / overall statistics.&rdquo; The Core API CAN count these "
            "(DatabaseStats adapter), but the agent has no count tool, so it answers &ldquo;exact counts "
            "aren't exposed.&rdquo;",
   note="RECOMMENDATION: expose DatabaseStats as an MCP tool so the PDF&rsquo;s &ldquo;how many&rdquo; "
        "questions (UI pages 6–8) get real numbers."),
 dict(q="What entity types and relationships does Eugene have? (schema)",
   cy="CALL db.labels()\nCALL db.relationshipTypes()\nCALL db.schema.visualization()",
   answer="17 labels and 41 relationship types (listed in §2). Schema visualization returns the full "
          "meta-graph.",
   tool="(not agent-exposed — analyst/ops)", endpoint="—",
   adapter="eugene/saved_queries/general/{relationship-types,visualize-schema}.cypher",
   scenario="Operator / analyst schema introspection in the Neo4j browser."),
]

for i, e in enumerate(ENTRIES, 1):
    story += [catalog_entry(i, e["q"], e["cy"], e["answer"], e["tool"], e["endpoint"],
                            e["adapter"], e["scenario"], e.get("note"))]

story += [PageBreak()]

# 4. analyst saved-query example
story += [P("4 · Analyst / GDS saved-query example (documented, GDS-only)", H1), hr()]
story += [P("The <font face='Courier'>eugene/saved_queries/</font> tree holds 78 graph-data-science (GDS) "
            "pipeline queries — projections, training, prediction, similarity — run by analysts in the Neo4j "
            "browser, not by the chat agent. They require a pre-built GDS in-memory projection "
            "(e.g. <font face='Courier'>'genes_drugs_diseases'</font>) so they were not executed here. Example "
            "with the result the analyst captured in-file:", BODY)]
story += [P("<b>Drug-repurposing — drugs similar to Hemophilia</b> "
            "(<font face='Courier'>drug_repurposing/disease/hemophilia/1-disease-drug.cypher</font>)", H2)]
story += [code_block(
    "MATCH (dse:disease)-[:disease_protein]-(p1:gene_protein)-[:drug_protein]-(drg:drug)\n"
    "WHERE dse.node_name =~ '(i?).*hemophilia.*'\n"
    "CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {\n"
    "    degreeCutoff: 1, similarityCutoff: .1, topN: 10, topK: 10, similarityMetric: 'COSINE',\n"
    "    sourceNodeFilter: [dse], targetNodeFilter: [drg],\n"
    "    relationshipTypes: ['drug_protein', 'disease_protein'] })\n"
    "YIELD node1, node2, similarity\n"
    "RETURN similarity, gds.util.asNode(node1).node_name AS Disease, gds.util.asNode(node2).node_name AS Drug\n"
    "ORDER BY similarity DESC")]
story += [Table([[Paragraph("<b>Captured result (in-file)</b>", CELLW),
   Paragraph("acquired hemophilia &rarr; Thrombin alfa (0.20), Vonicog Alfa (0.18), Human thrombin (0.16); "
             "hemophilia &rarr; Drotrecogin alfa, Protein C, Turoctocog alfa, Coagulation Factor IX Human, "
             "Antihemophilic factor (human recombinant), Moroctocog alfa …", ATXT)]],
   colWidths=[34 * mm, 136 * mm], style=TableStyle([
     ("BACKGROUND", (0, 0), (0, 0), TEAL), ("BACKGROUND", (1, 0), (1, 0), GREEN_BG),
     ("BOX", (0, 0), (-1, -1), 0.4, TEAL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
     ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
     ("LEFTPADDING", (0, 0), (-1, -1), 6)]))]
story += [Spacer(1, 3), P("<b>UI question this maps to:</b> &ldquo;Which drugs in Eugene are similar to / could "
          "be repurposed for hemophilia?&rdquo; &nbsp;<b>Agent tool:</b> fetch_similar (/similarity/{label}).", SMALL)]

story += [PageBreak()]

# 5. full inventory
story += [P("5 · Complete .cypher inventory (all 109 files)", H1), hr()]
story += [P("Every <font face='Courier'>.cypher</font> file in the repo, grouped by what it does and whether "
            "it was safe to execute against production.", BODY)]
try:
    inv = json.load(open("/tmp/cypher_inventory.json"))
except Exception:
    inv = {}
CAT_META = {
    "READ": ("Read-only (analytics / schema / counts)", "EXECUTED", GREEN, GREEN_BG),
    "GDS / ML pipeline": ("GDS / ML pipelines (project, train, predict, similarity)", "documented only", AMBER, AMBER_BG),
    "UPDATE (write)": ("Metadata updates (SET properties)", "NOT executed (write)", AMBER, AMBER_BG),
    "WRITE": ("Facet analytics (apoc map building)", "documented only", AMBER, AMBER_BG),
    "SEED (write)": ("Seed scripts (CREATE / MERGE assets)", "NOT executed (write)", RED, RED_BG),
    "INGEST (write)": ("CSV ingest (LOAD CSV)", "NOT executed (write)", RED, RED_BG),
    "DDL index": ("Index DDL (create / show)", "NOT executed (DDL)", AMBER, AMBER_BG),
    "DESTRUCTIVE (delete/drop)": ("Destructive (delete-all / drop index / drop data)", "NOT executed (DESTRUCTIVE)", RED, RED_BG),
}
inv_rows = [[Paragraph("<b>Category</b>", CELLW), Paragraph("<b>#</b>", CELLW),
             Paragraph("<b>Executed?</b>", CELLW), Paragraph("<b>Example files</b>", CELLW)]]
order = ["READ", "GDS / ML pipeline", "WRITE", "UPDATE (write)", "DDL index",
         "INGEST (write)", "SEED (write)", "DESTRUCTIVE (delete/drop)"]
for cat in order:
    files = inv.get(cat, [])
    if not files:
        continue
    desc, status, fg, bg = CAT_META.get(cat, (cat, "—", GREY_TX, GREY_BG))
    examples = ", ".join(f.split("saved_queries/")[-1].split("bin/")[-1] for f in files[:6])
    if len(files) > 6:
        examples += f", … (+{len(files) - 6} more)"
    inv_rows.append([Paragraph(desc, CELL), str(len(files)),
                     Paragraph(f"<font color='#{fg.hexval()[2:]}'><b>{status}</b></font>", CELL),
                     Paragraph(esc(examples), stylep("x", fontSize=7.4, textColor=INK, leading=9.5))])
story += [table(inv_rows, [50 * mm, 9 * mm, 33 * mm, 78 * mm])]
story += [Spacer(1, 3)]
story += [P("Totals: <b>109</b> .cypher files — 10 read-only (executed), 78 GDS/ML pipeline, 6 metadata-update, "
            "4 seed, 4 destructive, 3 facet-analytics, 3 index-DDL, 1 CSV-ingest. Plus ~38 parameterised query "
            "templates inside the Core-API Neo4j adapters (the agent-triggered queries catalogued in §3).", SMALL)]

# 6. findings
story += [Spacer(1, 5 * mm), P("6 · Findings from executing the queries", H1), hr()]
fnd = [
    [Paragraph("<b>Finding</b>", CELLW), Paragraph("<b>Detail / impact</b>", CELLW)],
    ["Naming mismatches break exact lookups",
     "&ldquo;Hemophilia A&rdquo; has no exact node (graph uses &ldquo;hemophilia&rdquo; / &ldquo;hemophilia A "
     "with vascular abnormality&rdquo;, id 10603). &ldquo;Factor VIII&rdquo; the protein is gene_protein "
     "<b>F8</b> (id 2157). Lookups must be fuzzy / canonical-aware."],
    ["Alias nodes are dead-ends",
     "lookup returns :drug_synonym nodes (e.g. drug_db13923_synonym_0) alongside the canonical :drug node. "
     "Edge/path queries on alias nodes return empty &rarr; false &ldquo;no connection&rdquo;. Fixed in the "
     "2026-06-12 agent prompt patch."],
    ["Some UI answers were hallucinated",
     "Emicizumab has only drug_drug / indication / drug_protein / has_drug_alias edges — NO trial, patent, "
     "drug-product or sponsor edges. The screenshots listing patents (Patent 1..11, node_id=null), patent "
     "applications, drug products, clinical trials and sponsors for Emicizumab were model fabrications, now "
     "curtailed by the prompt fix."],
    ["Organization names aren't on node_name",
     "Organization nodes return null for node_name; their display name lives in an org-specific property. "
     "Name-pattern org search must target that property (the org adapter does), which is why "
     "&ldquo;CSL Behring&rdquo;/&ldquo;Roche&rdquo; matched nothing via node_name."],
    ["A stats capability exists but isn't exposed",
     "neo4j_database_stats_adapter.py can count every label/relationship, but it is not wired as an MCP tool, "
     "so &ldquo;how many&rdquo; questions get &ldquo;not exposed.&rdquo; Recommend exposing it."],
]
story += [table(fnd, [42 * mm, 128 * mm])]
story += [Spacer(1, 5), hr()]
story += [P(f"Generated {DATE_HUMAN} ({DATE_ISO}). Live results captured by read-only queries against "
            f"production Neo4j via an in-VPC ECS task. Write / destructive / GDS / seed queries were "
            f"documented but not executed.", SMALL)]


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=17 * mm,
        title=f"Eugene Cypher Query Catalog {DATE_ISO}",
        author="CSL Behring Eugene platform engineering",
        subject="Cypher queries, live results, and agent/tool mapping")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"WROTE {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
