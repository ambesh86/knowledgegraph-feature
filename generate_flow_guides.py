"""
Generate two developer-oriented end-to-end PDF walkthroughs, in the same
style as docs/EUGENE_PATENT_FLOW_GUIDE.pdf:

   docs/EUGENE_DRUG_ALIAS_FLOW_GUIDE.pdf
   docs/EUGENE_AGENT_CHAT_FLOW_GUIDE.pdf

Run: /usr/local/opt/python@3.11/bin/python3.11 generate_flow_guides.py
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


DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


# ---------- styles ----------------------------------------------------------

ACCENT = HexColor("#0B3D91")
MUTED = HexColor("#555555")
CODE_BG = HexColor("#F4F6F8")
RULE = HexColor("#CFD8DC")

styles = getSampleStyleSheet()

H_TITLE = ParagraphStyle(
    "H_TITLE", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=ACCENT, spaceAfter=6,
)
H_SUB = ParagraphStyle(
    "H_SUB", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=14,
    textColor=MUTED, spaceAfter=18,
)
H1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=16, leading=20,
    textColor=ACCENT, spaceBefore=14, spaceAfter=8,
)
H2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    textColor=black, spaceBefore=10, spaceAfter=4,
)
BODY = ParagraphStyle(
    "BODY", parent=styles["BodyText"],
    fontName="Helvetica", fontSize=10, leading=14,
    alignment=TA_LEFT, spaceAfter=6,
)
BULLET = ParagraphStyle(
    "BULLET", parent=BODY,
    leftIndent=14, bulletIndent=2, spaceAfter=3,
)
CODE = ParagraphStyle(
    "CODE", parent=styles["Code"],
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


# ---------- doc 1: Drug Alias Flow -----------------------------------------

def build_drug_alias_guide():
    story = []

    story += [
        p("Eugene Drug Alias Search &mdash; End-to-End Flow", H_TITLE),
        p("Developer walkthrough: CSV ETL &rarr; Neo4j alias subgraph &rarr; APOC traversal &rarr; FastAPI router &rarr; response", H_SUB),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers who need to understand how the canonical drug node fans out into "
            "its synonyms and product names, and how the "
            "<font face='Courier'>GET /drugs/aliases/{drug_name}</font> endpoint walks that "
            "subgraph at query time. Every reference uses the form "
            "<font face='Courier'>path/to/file.py:line</font>.",
        ),
        p("Reference endpoints", H2),
        *bullets([
            "<font face='Courier'>GET /drugs/aliases/{drug_name}?fuzzy_match=false</font> &mdash; look up by display name (e.g. <i>Adderall</i>).",
            "<font face='Courier'>GET /drugs/aliases/id/{drug_id}</font> &mdash; look up by DrugBank id (e.g. <i>DB00182</i>).",
        ]),
        p("Caveat", H2),
        p(
            "The ETL orchestrator (<font face='Courier'>DrugAliasesUpdateOrchestrator</font>) "
            "is marked <b>@deprecated</b> in its docstring &mdash; the organization data model "
            "evolved away from this aliases shape. The CSV ingest still works and the "
            "<font face='Courier'>:HAS_DRUG_ALIAS</font> edges it produces are still what the "
            "read endpoint walks, so the flow remains correct for current data on disk; "
            "treat this guide as accurate-for-now and confirm before extending it.",
        ),
        PageBreak(),
    ]

    # 0. schema
    story += [
        p("0. Schema (read this first)", H1),
        p("The alias subgraph uses three node labels and one relationship type:"),
        code(
            "(:drug          { node_id, node_name, drug_bank_id, ... })\n"
            "(:drug_product  { node_id, node_name, drug_bank_id })\n"
            "(:drug_synonym  { node_id, node_name, drug_bank_id })\n"
            "(:drug)-[:has_drug_alias]-(:drug_product)\n"
            "(:drug)-[:has_drug_alias]-(:drug_synonym)"
        ),
        *bullets([
            "Labels come from <font face='Courier'>FoundationalNodeEnum.DRUG / DRUG_PRODUCT / DRUG_SYNONYM</font> in <font face='Courier'>src/foundation/model/foundational_node_enum.py</font>.",
            "Relationship type is <font face='Courier'>FoundationalRelationshipEnum.HAS_DRUG_ALIAS</font> (line 24) in <font face='Courier'>src/foundation/model/foundational_relationship_enum.py</font>.",
            "Canonical <font face='Courier'>:drug</font> nodes must already exist (seeded via <font face='Courier'>bin/seed/*.cypher</font>). Aliases are attached to whatever canonical drug already has a matching <font face='Courier'>drug_bank_id</font>.",
            "Like the rest of Eugene there are no Neo4j CREATE CONSTRAINTs &mdash; idempotency comes from <font face='Courier'>MERGE</font> on <font face='Courier'>node_id</font>.",
        ]),
        PageBreak(),
    ]

    # 1. ETL CLI
    story += [
        p("1. ETL entry point", H1),
        p("<font face='Courier'>src/ingest_drug_aliases.py</font>", PATH),
        p(
            "A small CLI that loads <font face='Courier'>.env</font>, asks the DI factory for "
            "the orchestrator, and calls <font face='Courier'>update(...)</font> with two CSV "
            "paths (defaults under <font face='Courier'>resources/data/drug/</font>):",
        ),
        code(
            "drug_update_orchestrator = drug_aliases_update_orchestrator()\n"
            "drug_update_orchestrator.update(\n"
            "    product_names_csv=args.product_names_csv,\n"
            "    synonyms_csv=args.synynoms_csv,\n"
            ")"
        ),
        p(
            "DI factory: <font face='Courier'>src/foundation/conf/conf.py:275-289</font>. It "
            "wires together <font face='Courier'>DrugProductNamesLoader</font>, "
            "<font face='Courier'>DrugSynonymsLoader</font>, and "
            "<font face='Courier'>Neo4jDrugAliasesAdapter</font> (driver from "
            "<font face='Courier'>_neo4j_driver()</font>).",
        ),
        Spacer(1, 8),
        p("CSV inputs", H2),
        *bullets([
            "<b>Product names</b>: <font face='Courier'>resources/data/drug/eugene_drug_productnames.csv</font> with columns <font face='Courier'>drugbank_id, product_names</font>. Loader at <font face='Courier'>src/foundation/load/drug_product_names_loader.py</font>.",
            "<b>Synonyms</b>: <font face='Courier'>resources/data/drug/eugene_drug_synonyms.csv</font> with columns <font face='Courier'>node_index, node_id, node_name, Synonyms</font>. Loader at <font face='Courier'>src/foundation/load/drug_synonyms_loader.py</font>.",
            "Each loader returns <font face='Courier'>list[DrugAliases]</font> &mdash; one object per drug, holding a set of product names <i>or</i> a set of synonyms but not both.",
        ]),
        PageBreak(),
    ]

    # 2. orchestrator
    story += [
        p("2. Orchestrator &mdash; merge + upsert", H1),
        p("<font face='Courier'>src/foundation/provider/drug_aliases_update_orchestrator.py</font>", PATH),
        p("<font face='Courier'>update()</font> at line 31:"),
        *bullets([
            "Loads both CSVs (each is optional &mdash; missing path just yields an empty list).",
            "<font face='Courier'>_merge()</font> (line 62) keys both lists by <font face='Courier'>drug_bank_id</font>, builds the union of ids, and produces one <font face='Courier'>DrugAliases</font> per drug with both <font face='Courier'>product_names</font> and <font face='Courier'>synonyms</font> populated.",
            "Calls <font face='Courier'>neo4j_drug_aliases_adapter.upsert_drug_aliases(drugs)</font> &mdash; the only write path.",
        ]),
        p("DrugAliases model", H2),
        p("<font face='Courier'>src/foundation/model/drug_aliases.py</font>", PATH),
        code(
            "DrugAliases(\n"
            "    drug_bank_id: str,\n"
            "    node_index:   str,   # taken from the synonyms CSV row, used for joins\n"
            "    drug_name:    str,\n"
            "    synonyms:     set[str],\n"
            "    product_names: set[str],\n"
            ")"
        ),
        PageBreak(),
    ]

    # 3. Neo4j upsert
    story += [
        p("3. Neo4j upsert &mdash; building the alias subgraph", H1),
        p("<font face='Courier'>src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py</font>", PATH),
        *bullets([
            "<font face='Courier'>upsert_drug_aliases</font> (line 54) loops one transaction per drug.",
            "<font face='Courier'>_upsert_drug_aliases</font> (line 67) does the work in three parts: anchor MATCH, batched MERGEs, return.",
        ]),
        p("Anchor MATCH (line 68-72)", H2),
        code(
            "OPTIONAL MATCH (drug:`drug` { node_id: $drug_bank_id })"
        ),
        p(
            "Note: <font face='Courier'>OPTIONAL MATCH</font>. If the canonical drug is "
            "missing, the upsert simply produces no rows &mdash; orphaned aliases are "
            "<b>not</b> created. This is why seed data must run first.",
        ),
        p("Per-alias MERGE blocks (lines 199-293)", H2),
        p(
            "<font face='Courier'>_generate_product_name_upserts</font> and "
            "<font face='Courier'>_generate_synonyms_upserts</font> each emit one Cypher "
            "snippet per alias, building parameter names like "
            "<font face='Courier'>$product0_node_id</font>, "
            "<font face='Courier'>$synonym3_node_name</font>, etc. The synthetic node id "
            "follows the pattern <font face='Courier'>drug_&lt;drugbank_id&gt;_product_&lt;n&gt;</font> / "
            "<font face='Courier'>drug_&lt;drugbank_id&gt;_synonym_&lt;n&gt;</font>.",
        ),
        code(
            "WITH drug\n"
            "MERGE (product:`drug_product` { node_id: $drug_bank_id })\n"
            "ON MATCH  SET product.refresh_date = datetime()\n"
            "ON CREATE SET product.refresh_date = datetime(),\n"
            "              product.node_id      = $product0_node_id,\n"
            "              product.drug_bank_id = $product0_drug_bank_id,\n"
            "              product.node_name    = $product0_node_name\n"
            "MERGE (drug)-[:`has_drug_alias`]-(product)"
        ),
        p(
            "The synonym block is identical except for the label "
            "<font face='Courier'>:drug_synonym</font>.",
        ),
        p("Batching (lines 84-105)", H2),
        p(
            "Aliases are upserted in chunks of 200 (<font face='Courier'>step_size</font>) to "
            "keep individual transactions manageable. Each chunk is joined into one big "
            "Cypher script: the anchor MATCH followed by N chained "
            "<font face='Courier'>WITH drug ... MERGE</font> blocks, terminated by "
            "<font face='Courier'>RETURN drug.node_id</font>.",
        ),
        PageBreak(),
    ]

    # 4. Read path
    story += [
        p("4. Read path &mdash; the router", H1),
        p("<font face='Courier'>src/foundation/router/drug_alias_search_router.py</font>", PATH),
        *bullets([
            "Module-load DI at lines 24-25: <font face='Courier'>neo4j_drug_aliases_adapter()</font> + <font face='Courier'>drug_aliases_result_mapper()</font>.",
            "<font face='Courier'>GET /drugs/aliases/{drug_name}</font> (line 33) &mdash; accepts <font face='Courier'>fuzzy_match: bool</font> query flag. When true, the WHERE clause becomes a case-insensitive regex match.",
            "<font face='Courier'>GET /drugs/aliases/id/{drug_id}</font> (line 65) &mdash; normalizes the id via <font face='Courier'>normalize_drug_id</font> and matches on <font face='Courier'>node_id</font>.",
            "Both wrap a missing/empty result as <font face='Courier'>DrugAliasSearchResult(drug=&hellip;, count=0, results=[])</font> rather than returning 404.",
        ]),
        p("Search Cypher (lines 309-319)", H2),
        code(
            "MATCH (n)\n"
            "WHERE n.node_name = $drug_name\n"
            "  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "CALL apoc.path.subgraphNodes([n],\n"
            "      { relationshipFilter: \"has_drug_alias\" }) YIELD node\n"
            "RETURN DISTINCT node.node_name              AS name,\n"
            "                toStringOrNull(node.node_id) AS node_id,\n"
            "                toStringOrNull(node.drug_bank_id) AS drug_bank_id,\n"
            "                toBoolean(\"drug\" in labels(node)) AS is_canonical"
        ),
        *bullets([
            "Anchors on any node by name (or id), then uses <b>APOC</b> (<font face='Courier'>apoc.path.subgraphNodes</font>) to expand along <font face='Courier'>:has_drug_alias</font> edges and return the whole alias cluster.",
            "<font face='Courier'>is_canonical</font> tells the response renderer which row is the canonical <font face='Courier'>:drug</font> node vs. its aliases.",
            "Hidden nodes (<font face='Courier'>n.is_hidden = true</font>) are filtered out at the anchor.",
            "Fuzzy mode swaps the WHERE for <font face='Courier'>n.node_name =~ '(?i).*&lt;term&gt;.*'</font> &mdash; built in <font face='Courier'>_generate_drug_alias_search_by_value</font> (line 295).",
        ]),
        p("Response shape", H2),
        p(
            "Adapter returns a pandas DataFrame; "
            "<font face='Courier'>DrugAliasesResultMapper.map(search_id, df)</font> "
            "(<font face='Courier'>src/foundation/mapper/drug_aliases_result_mapper.py</font>) "
            "wraps it as "
            "<font face='Courier'>DrugAliasSearchResult{ drug, count, results: [{name, node_id, drug_bank_id, is_canonical}, &hellip;] }</font>.",
        ),
        PageBreak(),
    ]

    # 5. debug walk + index
    story += [
        p("5. Suggested debugging walk", H1),
        *bullets([
            "Spin Neo4j + the API up via <font face='Courier'>docker-compose up eugene_neo4j eugene_ws</font>.",
            "Run the seed: <font face='Courier'>cypher-shell &lt; bin/seed/csl_behring_assets.cypher</font> (creates the canonical <font face='Courier'>:drug</font> nodes).",
            "Run the ETL: <font face='Courier'>python src/ingest_drug_aliases.py</font>. Breakpoint at <font face='Courier'>drug_aliases_update_orchestrator.py:31</font> to watch <font face='Courier'>_merge</font> combine the two CSVs.",
            "Step into <font face='Courier'>neo4j_drug_aliases_adapter.py:67</font> and observe the assembled <font face='Courier'>upsert_tx</font> string &mdash; copy/paste it into Neo4j Browser with the params dict to feel how it runs.",
            "Hit <font face='Courier'>GET /drugs/aliases/Adderall</font>; breakpoint at <font face='Courier'>drug_alias_search_router.py:52</font>. Verify the APOC traversal returns a row per alias plus the canonical drug.",
            "Toggle <font face='Courier'>?fuzzy_match=true</font> to watch the WHERE clause flip to the regex form (and consider whether your input is sanitized &mdash; it is interpolated into the Cypher).",
        ]),
        Spacer(1, 10),
        p("6. Reference index", H1),
        code(
            "Schema\n"
            "  src/foundation/model/foundational_node_enum.py        # DRUG, DRUG_PRODUCT, DRUG_SYNONYM\n"
            "  src/foundation/model/foundational_relationship_enum.py # HAS_DRUG_ALIAS (line 24)\n\n"
            "ETL\n"
            "  src/ingest_drug_aliases.py\n"
            "  src/foundation/load/drug_product_names_loader.py\n"
            "  src/foundation/load/drug_synonyms_loader.py\n"
            "  src/foundation/provider/drug_aliases_update_orchestrator.py\n"
            "  src/foundation/model/drug_aliases.py\n\n"
            "Read path\n"
            "  src/foundation/router/drug_alias_search_router.py\n"
            "  src/foundation/conf/conf.py                          # factories L191-196, L237\n"
            "  src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py\n"
            "  src/foundation/mapper/drug_aliases_result_mapper.py\n"
            "  src/foundation/model/drug/drug_alias_search_result.py\n\n"
            "Seed data\n"
            "  bin/seed/csl_behring_assets.cypher\n"
            "  bin/seed/biogen_assets.cypher\n"
            "  bin/seed/csl_drug_node_properties.cypher\n"
        ),
    ]

    return story


# ---------- doc 2: Agent Chat Flow ------------------------------------------

def build_agent_chat_guide():
    story = []

    story += [
        p("Eugene Agent Chat &mdash; End-to-End Flow", H_TITLE),
        p("Developer walkthrough: chat request &rarr; intent classifier &rarr; Strands agent + MCP tools &rarr; graph &rarr; streamed response", H_SUB),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers who need to understand how Eugene answers natural-language "
            "questions on top of the same Neo4j graph that the REST endpoints serve. "
            "Unlike <font face='Courier'>/patents/*</font> the agent path does not run a "
            "single hand-written Cypher &mdash; an LLM reasons over MCP tools and produces a "
            "narrative answer with citations. Every reference uses the form "
            "<font face='Courier'>path/to/file.py:line</font>.",
        ),
        p("Reference endpoints", H2),
        *bullets([
            "<font face='Courier'>POST /agent/api/query</font> &mdash; single-shot, returns a complete <font face='Courier'>ChatQueryResponse</font>.",
            "<font face='Courier'>POST /agent/api/query/stream</font> &mdash; newline-delimited JSON stream of <font face='Courier'>{type, content, tool, tool_input, ...}</font> envelopes that the Next.js UI uses to render a live tool-call trace + context graph.",
        ]),
        p("Service map", H2),
        *bullets([
            "<b>eugene-agent-ws</b> (this guide) &mdash; FastAPI service hosting the Strands agent. Codebase under <font face='Courier'>agents/eugene-agent-ws/</font>.",
            "<b>eugene-mcp</b> &mdash; MCP server exposing Eugene's read-only graph tools (<font face='Courier'>fetch_*</font>, <font face='Courier'>lookup_*</font>, <font face='Courier'>find_organization_*</font>). Codebase under <font face='Courier'>agents/eugene-mcp/src/tools/</font>.",
            "<b>eugene_ws</b> &mdash; the core REST API the MCP tools ultimately call.",
        ]),
        PageBreak(),
    ]

    # 1. boot
    story += [
        p("1. Boot &amp; routing", H1),
        p("<font face='Courier'>agents/eugene-agent-ws/src/eugene_chat_ws.py</font>", PATH),
        *bullets([
            "FastAPI app is mounted under <font face='Courier'>root_path=\"/agent/api\"</font> (line 54).",
            "Routers wired by <font face='Courier'>add_routers()</font> at lines 30-37: <font face='Courier'>auth_router, root_router, health_router, chat_query_agent_router</font>.",
            "Shared middleware (JSON logging, rate limiting, request-id, CORS) mirrors the core eugene_ws service.",
        ]),
        p("Router file", H2),
        p("<font face='Courier'>agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py</font>", PATH),
        *bullets([
            "Module-load DI at line 26: <font face='Courier'>eugene_agent = eugene_data_agent()</font> &mdash; the Strands agent is constructed once and reused.",
            "Auth: every request goes through <font face='Courier'>get_current_token</font> + <font face='Courier'>get_current_user</font> dependencies (MS Entra JWT validation).",
            "<font face='Courier'>POST /query</font> (line 29) &mdash; awaits <font face='Courier'>eugene_agent.execute(...)</font> and wraps the result with <font face='Courier'>unwrap_agent_result()</font>.",
            "<font face='Courier'>POST /query/stream</font> (line 74) &mdash; returns a <font face='Courier'>StreamingResponse</font> over <font face='Courier'>generate_chat_response()</font>, which serializes each event chunk as JSON + newline.",
        ]),
        PageBreak(),
    ]

    # 2. intent classifier
    story += [
        p("2. Intent classifier &mdash; pruning the toolset", H1),
        p("<font face='Courier'>agents/eugene-agent-ws/src/query/util/intent_classifier.py</font>", PATH),
        p(
            "Before the agent runs, the streaming endpoint calls "
            "<font face='Courier'>classify_intent(prompt, user_selected)</font>. The classifier "
            "is intentionally a small set of regexes &mdash; the docstring explains why: "
            "fewer tools means shorter system prompt, smaller ReAct surface area, and >90% "
            "precision on Eugene's well-defined domain without an extra LLM call.",
        ),
        p("Regex buckets", H2),
        code(
            "_GRAPH_RE   matches: drug, disease, gene, protein, pathway, trial,\n"
            "                    indication, organization, target, neighbors,\n"
            "                    biogen, roche, csl, hemophilia, factor, ...\n"
            "_WEB_RE     matches: web, internet, online, google, latest, news, ...\n"
            "_PATENT_RE  matches: patent, uspto, ip, assignee, patent number\n"
            "_PUBMED_RE  matches: pubmed, publication, paper, literature, ..."
        ),
        p("Rules", H2),
        *bullets([
            "Graph-concept match &rarr; add <font face='Courier'>ToolRequestEnum.EUGENE</font> (MCP tools).",
            "Web / pubmed / patent match &rarr; add <font face='Courier'>ToolRequestEnum.HTTP</font> (search_pubmed, search_patents_web, http_request).",
            "Nothing matched &rarr; default to <font face='Courier'>EUGENE</font> &mdash; graph queries are read-only and bounded, the safest fallback.",
            "Whatever the user ticked in the UI is always included.",
        ]),
        p(
            "Output: <font face='Courier'>IntentResult(tools, reason)</font>. The reason "
            "string is logged so you can grep for misclassifications.",
        ),
        PageBreak(),
    ]

    # 3. agent + system prompt
    story += [
        p("3. The Strands agent", H1),
        p("<font face='Courier'>agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py</font>", PATH),
        p("DI", H2),
        p(
            "<font face='Courier'>agents/eugene-agent-ws/src/query/conf/conf.py</font> "
            "constructs <font face='Courier'>EugeneDataAgent(eugene_mcp_server_url, model)</font>. "
            "The model is selected by <font face='Courier'>LLM_PROVIDER</font> env var "
            "(falls back to whichever API key is set):",
        ),
        *bullets([
            "<b>Anthropic</b> (default if <font face='Courier'>ANTHROPIC_API_KEY</font> present): <font face='Courier'>claude-sonnet-4-20250514</font>, override via <font face='Courier'>ANTHROPIC_MODEL_ID</font>.",
            "<b>OpenAI</b> fallback: <font face='Courier'>gpt-4.1-mini</font>, override via <font face='Courier'>OPENAI_MODEL_ID</font>.",
            "Wired in <font face='Courier'>LlmFactory</font> at <font face='Courier'>agents/eugene-agent-ws/src/query/infra/llm/llm_factory.py</font>.",
        ]),
        p("System prompt (eugene_data_agent.py:41-59)", H2),
        code(
            "You are Eugene, an agent that answers biomedical competitive-\n"
            "intelligence questions by querying the CSL Behring Eugene knowledge\n"
            "graph.\n"
            "Scope: drugs, diseases, gene/proteins, pathways, patents, clinical\n"
            "trials, organizations, and the relationships between them.\n\n"
            "Follow the ReAct pattern (Reason -> Act -> Observe). Prefer MCP\n"
            "tools (fetch_*, find_*, lookup_*) for facts. When the graph does\n"
            "not contain the requested information, state that clearly and\n"
            "stop -- do not loop.\n\n"
            "TOOL GUIDE:\n"
            "- Graph lookup (ingested drugs, genes, ...): MCP fetch_/lookup_/find_*\n"
            "- Latest patents on the open web: search_patents_web(query)\n"
            "- Biomedical literature (PubMed): search_pubmed(query, max_results)\n"
            "- Arbitrary URL fetch: http_request (only non-biomedical pages)\n\n"
            "HARD RULES:\n"
            "1. No calculator / current_time unless the question is about that.\n"
            "2. No retrying the same tool with same args more than twice.\n"
            "3. No invented data. If no tool answers, say so + provide a search link.\n"
            "4. <= 20 tool calls per turn.\n\n"
            "Citation requirement: when asserting a fact from a tool result, cite\n"
            "[node_id=<id>, tool=<tool_name>] so the UI can render a context graph."
        ),
        PageBreak(),
    ]

    # 4. tools
    story += [
        p("4. Tools", H1),
        p("Local tools (eugene_data_agent.py:246-260)", H2),
        *bullets([
            "<font face='Courier'>calculator</font>, <font face='Courier'>current_time</font> &mdash; opt-in only via <font face='Courier'>EUGENE_ALLOW_UTILITY_TOOLS=true</font>. They caused runaway ReAct loops on simple data questions, so they ship disabled.",
            "<font face='Courier'>python_repl</font> &mdash; opt-in via <font face='Courier'>EUGENE_ALLOW_PYTHON_REPL=true</font>.",
            "<font face='Courier'>search_pubmed</font> &amp; <font face='Courier'>search_patents_web</font> &mdash; added only when the request includes the HTTP tool group. Implementations at <font face='Courier'>agents/eugene-agent-ws/src/query/tools/external_tools.py</font>.",
            "<font face='Courier'>http_request</font> (Strands built-in) &mdash; only added alongside the search tools.",
        ]),
        p("MCP tools (eugene-mcp service)", H2),
        p(
            "Listed dynamically via <font face='Courier'>mcp_client.list_tools_sync()</font> "
            "(line 259) when the request includes "
            "<font face='Courier'>ToolRequestEnum.EUGENE</font>. The MCP server lives at "
            "<font face='Courier'>agents/eugene-mcp/src/eugene_mcp.py</font> and exposes one "
            "tool file per domain:",
        ),
        code(
            "agents/eugene-mcp/src/tools/eugene_drug_tools.py\n"
            "agents/eugene-mcp/src/tools/eugene_graph_tools.py\n"
            "agents/eugene-mcp/src/tools/eugene_node_tools.py\n"
            "agents/eugene-mcp/src/tools/eugene_organization_tools.py\n"
            "agents/eugene-mcp/src/tools/eugene_fetch_tools.py\n"
            "agents/eugene-mcp/src/tools/eugene_fact_tools.py"
        ),
        p(
            "Each tool ultimately HTTP-calls a REST endpoint on eugene_ws (the same routers "
            "covered by the patent and drug-alias guides). The MCP layer exists so the "
            "agent gets a typed, discoverable interface; it does not bypass the REST API."
        ),
        p("MCP transport", H2),
        p(
            "<font face='Courier'>_build_mcp_client</font> (line 283) uses "
            "<font face='Courier'>streamable_http_client</font> over an "
            "<font face='Courier'>httpx.AsyncClient</font> with the user's bearer token "
            "forwarded as <font face='Courier'>Authorization</font>. SSL verify defaults "
            "true; dev opt-out via <font face='Courier'>EUGENE_MCP_VERIFY_SSL=false</font>. "
            "Timeouts: connect 10s / read 60s / write 30s.",
        ),
        PageBreak(),
    ]

    # 5. ReAct loop
    story += [
        p("5. ReAct execution &amp; safety rails", H1),
        p("execute() &mdash; non-streaming (line 71)", H2),
        *bullets([
            "Builds a per-request MCP client, then <font face='Courier'>_init_agent(...)</font> with a per-conversation <font face='Courier'>SlidingWindowConversationManager(window_size=10, per_turn=2)</font> &mdash; AGT-01 fix (was shared across concurrent users).",
            "<font face='Courier'>FileSessionManager(session_id=conversation_id)</font> persists the conversation to disk for resumability.",
            "Runs the agent inside <font face='Courier'>with mcp_client:</font> &mdash; MCP session is alive for exactly one user turn.",
        ]),
        p("execute_stream() &mdash; streaming (line 99)", H2),
        p(
            "Same setup, but yields <font face='Courier'>{type, content, tool, tool_input, tool_id, tool_output}</font> "
            "events as the agent advances. Three kinds of safety rail are wrapped around "
            "the stream:",
        ),
        *bullets([
            "<b>Hard tool-call budget</b> &mdash; <font face='Courier'>_HARD_TOOL_CALL_BUDGET</font> (default 25, env <font face='Courier'>EUGENE_MAX_TOOL_CALLS</font>). When exhausted, the loop is killed with a visible warning.",
            "<b>Duplicate-input breaker</b> &mdash; if the agent calls the same <font face='Courier'>(tool, json(args))</font> more than <font face='Courier'>_MAX_DUPLICATE_TOOL_CALLS=2</font> times, the loop is killed (AGT-02).",
            "<b>Wall-clock timeout</b> &mdash; <font face='Courier'>_AGENT_STREAM_TIMEOUT_S</font> (default 180s) via <font face='Courier'>_with_timeout</font>. Stalled MCP/LLM cannot hold the HTTP connection open indefinitely (AGT-03).",
            "<b>Iteration cap</b> &mdash; <font face='Courier'>_AGENT_MAX_ITERATIONS</font> (default 20) is set post-construction on the Strands Agent (line 275-279). Belt-and-braces in case Strands drops the kwarg between versions.",
        ]),
        p("Event extraction (lines 302-403)", H2),
        *bullets([
            "<font face='Courier'>_extract_tool_events</font> emits tool_call/tool_result events from mid-stream Strands events &mdash; defensive, because event shapes differ across providers and Strands versions.",
            "<font face='Courier'>_harvest_messages</font> walks <font face='Courier'>agent.messages</font> after the stream completes &mdash; this is the authoritative path, since <font face='Courier'>agent.messages</font> is stable across versions.",
            "<font face='Courier'>_flatten_tool_output</font> parses JSON blocks so the UI can extract nodes/relationships and build the live context graph.",
        ]),
        PageBreak(),
    ]

    # 6. debug walk + index
    story += [
        p("6. Suggested debugging walk", H1),
        *bullets([
            "Start the stack: <font face='Courier'>docker-compose up eugene_neo4j eugene_ws eugene_mcp eugene_agent_ws</font>. Confirm <font face='Courier'>EUGENE_MCP_SERVER_URL</font> and an LLM API key are set in <font face='Courier'>docker.env</font>.",
            "Get a JWT via <font face='Courier'>POST /agent/api/auth/...</font> (see <font face='Courier'>router/auth/auth_router.py</font>).",
            "Hit the non-streaming endpoint with curl: <font face='Courier'>POST /agent/api/query</font> body <font face='Courier'>{\"prompt\": \"List drugs that target ABL1\", \"include_tools\": []}</font>. Breakpoint at <font face='Courier'>chat_query_agent_router.py:51</font>.",
            "Step into <font face='Courier'>EugeneDataAgent.execute</font>. Inspect <font face='Courier'>agent.tool_names</font> after <font face='Courier'>_init_agent</font> to confirm the intent-pruned toolset.",
            "Switch to the streaming endpoint: <font face='Courier'>curl -N -d ... /agent/api/query/stream</font>. Tail logs to watch <font face='Courier'>tool_call</font> / <font face='Courier'>tool_result</font> envelopes flow.",
            "Force a runaway: ask a prompt that tempts the model to call <font face='Courier'>current_time</font> repeatedly (with <font face='Courier'>EUGENE_ALLOW_UTILITY_TOOLS=true</font>) &mdash; observe the duplicate-input breaker fire in <font face='Courier'>_register_tool_call</font>.",
            "Trace one MCP tool: pick e.g. <font face='Courier'>fetch_drug_by_id</font> in <font face='Courier'>agents/eugene-mcp/src/tools/eugene_drug_tools.py</font> and follow its HTTP call to eugene_ws &mdash; ends up at the same <font face='Courier'>/drugs/...</font> router covered in the drug-alias guide.",
        ]),
        Spacer(1, 10),
        p("7. Reference index", H1),
        code(
            "Boot & routing\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py\n"
            "  agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py\n"
            "  agents/eugene-agent-ws/src/router/auth/auth.py\n\n"
            "Intent & request shape\n"
            "  agents/eugene-agent-ws/src/query/util/intent_classifier.py\n"
            "  agents/eugene-agent-ws/src/query/util/validation.py\n"
            "  agents/eugene-agent-ws/src/query/model/chat_query_request.py\n"
            "  agents/eugene-agent-ws/src/query/model/chat_query_response.py\n"
            "  agents/eugene-agent-ws/src/query/model/tool_request_enum.py\n\n"
            "Agent\n"
            "  agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py\n"
            "  agents/eugene-agent-ws/src/query/conf/conf.py\n"
            "  agents/eugene-agent-ws/src/query/infra/llm/llm_factory.py\n"
            "  agents/eugene-agent-ws/src/query/util/agent_debug.py\n"
            "  agents/eugene-agent-ws/src/query/util/response.py\n\n"
            "Local tools\n"
            "  agents/eugene-agent-ws/src/query/tools/external_tools.py\n\n"
            "MCP server (separate service)\n"
            "  agents/eugene-mcp/src/eugene_mcp.py\n"
            "  agents/eugene-mcp/src/tools/eugene_drug_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_graph_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_node_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_organization_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_fetch_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_fact_tools.py\n\n"
            "Env knobs (defaults shown)\n"
            "  EUGENE_AGENT_MAX_ITERATIONS = 20\n"
            "  EUGENE_AGENT_STREAM_TIMEOUT_S = 180\n"
            "  EUGENE_MAX_TOOL_CALLS = 25\n"
            "  EUGENE_MCP_VERIFY_SSL = true\n"
            "  EUGENE_ALLOW_PYTHON_REPL = false\n"
            "  EUGENE_ALLOW_UTILITY_TOOLS = false\n"
            "  LLM_PROVIDER = anthropic | openai (auto-detected from key)\n"
            "  ANTHROPIC_MODEL_ID = claude-sonnet-4-20250514\n"
            "  OPENAI_MODEL_ID    = gpt-4.1-mini\n"
        ),
    ]

    return story


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    render(
        build_drug_alias_guide(),
        "EUGENE_DRUG_ALIAS_FLOW_GUIDE.pdf",
        "Eugene Drug Alias Search - End-to-End Flow",
    )
    render(
        build_agent_chat_guide(),
        "EUGENE_AGENT_CHAT_FLOW_GUIDE.pdf",
        "Eugene Agent Chat - End-to-End Flow",
    )


if __name__ == "__main__":
    main()
