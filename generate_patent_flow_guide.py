"""
Generate docs/EUGENE_PATENT_FLOW_GUIDE.pdf - a developer-oriented end-to-end
walkthrough of the Eugene patent search flow: ETL -> Neo4j schema -> LLM
extraction -> router -> response.

Run: python3 generate_patent_flow_guide.py
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


OUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "docs",
    "EUGENE_PATENT_FLOW_GUIDE.pdf",
)


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


# ---------- content ---------------------------------------------------------

def build():
    story = []

    # cover
    story += [
        p("Eugene Patent Search &mdash; End-to-End Flow", H_TITLE),
        p("Developer walkthrough: USPTO ETL &rarr; Neo4j graph &rarr; LLM extraction &rarr; FastAPI router &rarr; response", H_SUB),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who need a "
            "single, file-referenced trace of the patent flow. Every reference uses "
            "the form <font face='Courier'>path/to/file.py:line</font> so you can open "
            "it directly in your IDE and step through with a debugger.",
        ),
        p("Reference endpoint", H2),
        p(
            "<font face='Courier'>GET /patents/drugs?drug_id=DB00993&amp;page=1&amp;page_size=50</font> "
            "&mdash; declared in <font face='Courier'>src/foundation/router/patent_search_router.py</font>. "
            "The same trace applies to the <i>clinicaltrials</i> and <i>geneproteins</i> siblings.",
        ),
        p("How to read this guide", H2),
        *bullets([
            "Sections follow the request path in reverse: start at the HTTP boundary, then walk back through the ETL that fills the graph.",
            "Section 0 (Schema) is non-obvious and easy to miss: Eugene enforces graph structure by convention, not by Neo4j CREATE CONSTRAINT.",
            "Section 7 contains the verbatim LLM prompts used during patent ingestion.",
        ]),
        PageBreak(),
    ]

    # 0. schema
    story += [
        p("0. The graph schema (read this first)", H1),
        p(
            "Eugene does <b>not</b> use Neo4j <font face='Courier'>CREATE CONSTRAINT</font> "
            "statements. The schema is conventional, enforced by code:",
        ),
        *bullets([
            "<b>Node labels</b> are centralized as enums in "
            "<font face='Courier'>src/foundation/model/foundational_node_enum.py</font> "
            "&mdash; e.g. <font face='Courier'>DRUG = 8, \"drug\"</font>, "
            "<font face='Courier'>PATENT_APPLICATION = 31, \"Patent_Application\"</font>, "
            "<font face='Courier'>CLINICAL_TRIAL = 4, \"ClinicalTrial\"</font>, "
            "<font face='Courier'>GENE_PROTEIN = 12, \"gene_protein\"</font>.",
            "<b>Relationship types</b> live in "
            "<font face='Courier'>src/foundation/model/foundational_relationship_enum.py</font> "
            "&mdash; <font face='Courier'>DISCLOSED_IN</font>, "
            "<font face='Courier'>SUPPORTS_PATENT_APPLICATION</font>, "
            "<font face='Courier'>PATENT_APP_TARGET</font>.",
            "<b>Idempotency</b> comes from <font face='Courier'>MERGE</font> on a natural-key "
            "property (e.g. <font face='Courier'>application_number_text</font>, "
            "<font face='Courier'>node_id</font>) &mdash; not from a uniqueness constraint.",
            "The Neo4j container "
            "(<font face='Courier'>containers/eugene_neo4j_ce/Dockerfile</font>) ships only "
            "<font face='Courier'>neo4j.conf</font> + <font face='Courier'>apoc.conf</font>; "
            "no schema init runs.",
            "<b>Seed data</b> (CSL/Biogen drug assets, drug node properties) lives as plain "
            "Cypher in <font face='Courier'>bin/seed/</font> and is run manually against a fresh DB.",
        ]),
        p(
            "<b>Implication for debugging:</b> keep the two enum files open while reading any "
            "adapter. Every Cypher string interpolates label/relationship strings from them.",
        ),
        PageBreak(),
    ]

    # 1. router
    story += [
        p("1. HTTP entry &mdash; the FastAPI router", H1),
        p("Wiring", H2),
        p(
            "<font face='Courier'>src/eugene_ws.py:31-78</font> &mdash; "
            "<font face='Courier'>add_routers()</font> imports "
            "<font face='Courier'>patent_search_router</font> and includes it in the FastAPI app.",
        ),
        p("Router file", H2),
        p("<font face='Courier'>src/foundation/router/patent_search_router.py</font>", PATH),
        p("Module-load dependency injection (lines 34-35):"),
        code(
            "patent_query_adapter = neo4j_patent_query_adapter()\n"
            "search_result_mapper = patent_search_result_mapper()"
        ),
        p(
            "Factories are defined in <font face='Courier'>src/foundation/conf/conf.py:199-206</font> "
            "(adapter + Neo4j driver) and <font face='Courier'>src/foundation/conf/conf.py:267</font> "
            "(mapper). This is Eugene's manual DI pattern &mdash; no framework, no decorators.",
        ),
        p("Endpoint handler (GET /patents/drugs, lines 38-78)", H2),
        *bullets([
            "Pydantic validation via <font face='Courier'>Annotated[..., Query(...), AfterValidator(validate_value)]</font>. Validators in <font face='Courier'>src/foundation/router/validate_util.py</font>.",
            "ID normalization: <font face='Courier'>normalize_drug_id</font> in <font face='Courier'>src/foundation/model/case_helper.py</font>.",
            "Adapter call returns a pandas DataFrame; mapper turns it into a Pydantic <font face='Courier'>PatentSearchResult</font>.",
        ]),
        p("<b>Set your first breakpoint at line 72</b> (<font face='Courier'>drug_id = normalize_drug_id(drug_id)</font>)."),
        PageBreak(),
    ]

    # 2. adapter
    story += [
        p("2. Query adapter &mdash; the Cypher", H1),
        p("<font face='Courier'>src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py</font>", PATH),
        *bullets([
            "<font face='Courier'>find_related_patents_by_drug</font> (line 28) opens a session/transaction and delegates to <font face='Courier'>_find_related_patents_by_drug</font> (line 107).",
            "<font face='Courier'>tx.run(cypher, params).to_df()</font> &rarr; pandas DataFrame.",
            "Cypher is built in <font face='Courier'>_generate_patent_search_by_drug</font> (line 126).",
            "<font face='Courier'>ensure_connection()</font> from <font face='Courier'>src/graph/util/util.py</font> is a per-request driver-health guard.",
            "Pagination math in <font face='Courier'>src/foundation/infra/db/util/pagination.py</font>.",
        ]),
        p("Generated Cypher (after label/relationship interpolation)", H2),
        code(
            "MATCH (n:`drug`)-[r:`disclosed_in`]-(n2:`Patent_Application`)\n"
            "WHERE n.node_id = $drug_id\n"
            "RETURN n.node_id   AS drug_id,\n"
            "       n.node_name AS drug_name,\n"
            "       n2.patent_id AS patent_id\n"
            "ORDER BY patent_id DESC\n"
            "SKIP <offset> LIMIT <limit>"
        ),
        p("Response mapping", H2),
        p(
            "<font face='Courier'>src/foundation/mapper/patent_search_result_mapper.py:18-30</font> "
            "iterates the DataFrame and emits <font face='Courier'>PatentSearchResultRow</font> "
            "instances inside a <font face='Courier'>PatentSearchResult</font> "
            "(<font face='Courier'>src/foundation/model/patent/patent_search_result.py</font>).",
        ),
        p(
            "That completes the read path. The interesting question is how a "
            "<font face='Courier'>:Patent_Application</font> node connected by "
            "<font face='Courier'>:disclosed_in</font> to a <font face='Courier'>:drug</font> "
            "node ever appears in the graph. That is the ETL.",
        ),
        PageBreak(),
    ]

    # 3. ETL top
    story += [
        p("3. ETL &mdash; top-level orchestration", H1),
        p("Two CLI entrypoints at the repo root", H2),
        *bullets([
            "<font face='Courier'>src/download_patents.py</font> &mdash; fetches USPTO applications + pgpub documents to disk as JSON.",
            "The process path (turns disk JSON into Neo4j nodes/relationships + LLM-extracted knowledge) is invoked from the patent ingest CLIs.",
        ]),
        p("Both paths flow through <font face='Courier'>PatentOrchestrator</font>", H2),
        p("<font face='Courier'>src/patent/provider/patent_orchestrator.py</font>", PATH),
        *bullets([
            "<font face='Courier'>download()</font> (line 27) &rarr; <font face='Courier'>ApplicationOrchestator.fetch_theraputic_areas</font> &rarr; <font face='Courier'>JsonWriter.write</font>, then <font face='Courier'>PgpubOrchestrator.fetch</font> &rarr; <font face='Courier'>PgpubJsonWriter.write</font>.",
            "<font face='Courier'>process()</font> (line 53) &rarr; <font face='Courier'>fetch_and_store_theraputic_areas</font> (writes Application nodes) &rarr; <font face='Courier'>PgpubOrchestrator.process(..., with_analysis_and_linking=True)</font> (writes pgpub nodes + runs the LLM).",
            "DI wiring: <font face='Courier'>src/patent/conf/orchestator.py</font>.",
        ]),
        Spacer(1, 8),
        p("4. ETL &mdash; populating Patent_Application nodes", H1),
        p(
            "<font face='Courier'>ApplicationOrchestator</font> "
            "(<font face='Courier'>src/patent/application/</font>) hits the USPTO API "
            "(<font face='Courier'>provider/application_provider.py</font>) to list recent "
            "therapeutic-area applications. Its Neo4j writer adapter MERGEs "
            "<font face='Courier'>:Patent_Application</font> nodes keyed on "
            "<font face='Courier'>application_number_text</font>. See "
            "<font face='Courier'>src/patent/application/infra/db/</font>.",
        ),
        PageBreak(),
    ]

    # 5. pgpub
    story += [
        p("5. ETL &mdash; populating Pgpub + linking to the Application", H1),
        p("<font face='Courier'>src/patent/pgpub/provider/pgpub_orchestrator.py:55-77</font>  &mdash;  <font face='Courier'>process()</font>", PATH),
        p("For each Application:"),
        *bullets([
            "<font face='Courier'>pgpub_metadata_provider.list_assoc_documents(...)</font> &rarr; <font face='Courier'>pgpub_provider.fetch_pgpub(...)</font> retrieves USPTO pre-grant publications.",
            "<font face='Courier'>_add_embeddings(pgpub)</font> runs the document through <font face='Courier'>src/patent/pgpub/infra/embedding/pgpub_metadata_embedding_provider.py</font> and stuffs a vector onto <font face='Courier'>pgpub.embeddings</font>.",
            "<font face='Courier'>_ingest(pgpub)</font> &rarr; <font face='Courier'>Neo4jPgpubAdapter.upsert(pgpub)</font> at <font face='Courier'>src/patent/pgpub/infra/db/adapter/neo4j_pgpub_adapter.py:32</font>.",
        ]),
        p("Upsert Cypher (neo4j_pgpub_adapter.py:50-96)", H2),
        code(
            "MERGE (pgpub:`<USPTO_PGPUB_NODE_TYPE>` {\n"
            "    application_number_text: $application_number_text\n"
            "})\n"
            "ON MATCH  SET pgpub.refresh_date = datetime(),\n"
            "              pgpub.abstract = $abstract, ...,\n"
            "              pgpub.embeddings = $embeddings\n"
            "ON CREATE SET ... pgpub.is_uspto = true\n"
            "WITH pgpub\n"
            "MATCH (application:`<USPTO_APPLICATION_NODE_TYPE>`\n"
            "       { application_number_text: $application_number_text })\n"
            "MERGE (application)-[:`<USPTO_PGPUB_PATENT_REL_TYPE>` { is_uspto: true }]-(pgpub)"
        ),
        p(
            "Label constants live in <font face='Courier'>src/patent/pgpub/infra/db/const.py</font> "
            "and <font face='Courier'>src/patent/application/infra/db/const.py</font>.",
        ),
        p(
            "<b>This MERGE pattern is the de-facto schema constraint in this codebase:</b> "
            "the same <font face='Courier'>application_number_text</font> always resolves to "
            "the same node, so re-running the ETL is idempotent.",
        ),
        PageBreak(),
    ]

    # 6. LLM step
    story += [
        p("6. ETL &mdash; the LLM extraction step (where :disclosed_in is born)", H1),
        p(
            "When <font face='Courier'>with_analysis_and_linking=True</font>, "
            "<font face='Courier'>PgPubKnowledgeGraphAnalyzer.analyze(...)</font> runs after "
            "ingest. The read-side query in &sect;2 depends on this step, because "
            "<font face='Courier'>(:drug)-[:disclosed_in]-(:Patent_Application)</font> only "
            "exists after the LLM extracts entities from the patent text and the linking "
            "step hooks them into canonical drug/gene/disease nodes.",
        ),
        p("Call chain", H2),
        *bullets([
            "<font face='Courier'>src/patent/pgpub/analyze/pgpub_knowledge_graph_analyzer.py:22</font> loops pgpubs &rarr; <font face='Courier'>summary_orchestrator.summarize(pgpub)</font>.",
            "<font face='Courier'>src/patent/pgpub/analyze/pgpub_graph_summary_orchestrator.py:64</font> runs three steps:",
        ]),
        p("Step 1 &mdash; extract", H2),
        p(
            "<font face='Courier'>extract_and_write()</font> (line 88) &rarr; "
            "<font face='Courier'>_extract()</font> (line 177): builds two pages "
            "(<font face='Courier'>pgpub.abstract</font> and the concatenated "
            "<font face='Courier'>claims</font>) and runs them through "
            "<font face='Courier'>DocumentAnalyzer.analyze_document_pages</font>.",
        ),
        p("Step 2 &mdash; link", H2),
        p(
            "<font face='Courier'>upsert_relationships()</font> (line 109) links extracted "
            "entities to the pgpub via "
            "<font face='Courier'>Neo4jPgpubLinkingAdapter.link_pgpub_node</font> &mdash; "
            "this is what creates the <font face='Courier'>:disclosed_in</font>-style edges.",
        ),
        p("Step 3 &mdash; community summaries", H2),
        p(
            "<font face='Courier'>summarize_communities()</font> (line 129) builds a NetworkX "
            "graph of extracted entities, runs Leiden-style community detection "
            "(<font face='Courier'>graph/community/</font>), asks the LLM for a per-community "
            "report, and stores summaries as <font face='Courier'>:Summary</font>/"
            "<font face='Courier'>:Finding</font> nodes via "
            "<font face='Courier'>neo4j_pgpub_summary_adapter.py</font>.",
        ),
        p("DocumentAnalyzer", H2),
        p(
            "<font face='Courier'>src/document/analyze/document_analyzer.py:47-85</font> "
            "pairs each <font face='Courier'>input_param</font> (which carries the prompt) "
            "with each page, fans them out across a "
            "<font face='Courier'>ThreadPoolExecutor</font> (default 4 workers), streams the "
            "LLM response chunk-by-chunk, and returns "
            "<font face='Courier'>PromptResponse</font>.",
        ),
        p("Prompt template (generate.py:476-486):"),
        code(
            "Question: {question}\n"
            "Contents to analyze: {document}"
        ),
        PageBreak(),
    ]

    # 7. LLM prompts
    story += [
        p("7. The LLM prompts used during patent ingestion", H1),
        p(
            "Wiring: <font face='Courier'>src/patent/pgpub/conf/graphrag_conf.py:145-149</font>. "
            "The extraction <font face='Courier'>DocumentAnalyzer</font> is constructed with "
            "<font face='Courier'>input_params=[generate_knowlege_graph_extraction_input_params(\"\")]</font>, "
            "which embeds the GraphRAG-style triples prompt below.",
        ),
        p("7.1 Knowledge graph extraction prompt", H2),
        p("<font face='Courier'>src/infra/llm/prompt/generate.py:205-268</font>", PATH),
        code(
            "-Goal-\n"
            "Given a text document, identify all entities and their entity types\n"
            "from the text and all relationships among the identified entities.\n\n"
            "-Steps-\n"
            "1. Identify all entities. For each:\n"
            "   - entity_name (capitalized)\n"
            "   - entity_type\n"
            "   - entity_description\n"
            "   Format: (\"entity\"/<name>/<type>/<description>)\n\n"
            "   Only include these entity types:\n"
            "     drug, disease, gene_protein, pathway, anatomy,\n"
            "     biological_process, cellular_component, effect_phenotype,\n"
            "     exposure, molecular_function, chemical_synonym\n\n"
            "2. Identify all (source, target) pairs that are clearly related.\n"
            "   - source_entity, target_entity, relation, relationship_description\n"
            "   Format: (\"relationship\"/<src>/<tgt>/<relation>/<description>)\n\n"
            "   Only include these relation types:\n"
            "     drug_drug, drug_protein, drug_effect, disease_disease,\n"
            "     disease_protein, pathway_protein, pathway_pathway,\n"
            "     protein_protein, bioprocess_protein, indication\n\n"
            "3. Output as JSON with `entities` and `relationships` arrays."
        ),
        p("7.2 Entity summary prompt (used by community step)", H2),
        p("<font face='Courier'>src/infra/llm/prompt/generate.py:271</font>", PATH),
        code(
            "You are a helpful assistant responsible for generating a comprehensive\n"
            "summary of the data provided below. Given one or two entities, and a\n"
            "list of descriptions, all related to the same entity or group of\n"
            "entities, please concatenate all of these into a single, comprehensive\n"
            "description... Make sure it is written in third person, and include\n"
            "the entity names so we have the full context.\n\n"
            "Entities: {entity_name}\n"
            "Description List: {description_list}"
        ),
        p("7.3 Community report prompt", H2),
        p("<font face='Courier'>src/infra/llm/prompt/generate.py:310</font>", PATH),
        p(
            "Produces a structured report (TITLE, SUMMARY, IMPACT SEVERITY RATING, "
            "RATING EXPLANATION, DETAILED FINDINGS) returned as JSON. The output is "
            "parsed by "
            "<font face='Courier'>document/load/stored_summaries_loader.py</font> and "
            "stored as <font face='Courier'>:Summary</font> + "
            "<font face='Courier'>:Finding</font> nodes attached to the Patent_Application.",
        ),
        p("Triples parsing &amp; canonical linking", H2),
        *bullets([
            "<font face='Courier'>src/graph/mapper/triples_parser.py</font> parses the <font face='Courier'>(\"entity\"/...)</font> and <font face='Courier'>(\"relationship\"/...)</font> lines into <font face='Courier'>Entity</font>/<font face='Courier'>Relationship</font> objects.",
            "<font face='Courier'>_link_or_drop_entities</font> at <font face='Courier'>pgpub_graph_summary_orchestrator.py:240</font> calls <font face='Courier'>Neo4jPgpubLinkingAdapter.find_node_index_by_node_name(entity_type, value)</font>.",
            "<b>This is the canonical-lookup gate:</b> any LLM-extracted entity that does not already exist as a canonical node (drugs/genes/diseases must be seeded first via <font face='Courier'>bin/seed/</font>) is dropped. Surviving entities are linked to the pgpub.",
        ]),
        p("LLM model factory", H2),
        p(
            "<font face='Courier'>src/infra/llm/llm_factory.py</font> &mdash; returns a "
            "LangChain <font face='Courier'>BaseChatModel</font> (provider/model selected by "
            "env vars). Streaming is on by default; the analyzer assembles chunks itself.",
        ),
        PageBreak(),
    ]

    # debug walk
    story += [
        p("8. Suggested debugging walk", H1),
        *bullets([
            "Start FastAPI locally: <font face='Courier'>uvicorn src.eugene_ws:app</font>. Then <font face='Courier'>curl '/patents/drugs?drug_id=DB00993&amp;page=1&amp;page_size=10'</font>. Breakpoint at <font face='Courier'>patent_search_router.py:72</font>. Step into the adapter, watch the Cypher string get built, inspect the DataFrame.",
            "Once the read path is clear, run <font face='Courier'>python src/download_patents.py --max-applications 1 --output resources/data</font> and step through <font face='Courier'>patent_orchestrator.py:27</font>.",
            "Run the process() path (find the CLI that calls it &mdash; e.g. <font face='Courier'>convert_patents.py</font> at the repo root) with a breakpoint at <font face='Courier'>pgpub_orchestrator.py:55</font>. Watch <font face='Courier'>_ingest</font> write a pgpub node, then enter <font face='Courier'>PgPubKnowledgeGraphAnalyzer.analyze</font> to see the LLM extraction.",
            "Inside <font face='Courier'>DocumentAnalyzer._analyze_document_task</font> (<font face='Courier'>document_analyzer.py:67</font>), inspect <font face='Courier'>input_params[\"question\"]</font> &mdash; that is the exact prompt string from <font face='Courier'>generate.py:205-268</font> after template interpolation.",
            "After analyze, query Neo4j: <font face='Courier'>MATCH (p:Patent_Application)-[:disclosed_in]-(d:drug) RETURN d.node_name, p.patent_id LIMIT 10</font> &mdash; this is the row set the router returns.",
        ]),
        Spacer(1, 10),
        p("9. Reference index (file paths)", H1),
        code(
            "Schema\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "  bin/seed/*.cypher\n"
            "  containers/eugene_neo4j_ce/{Dockerfile,conf/}\n\n"
            "Router & wiring\n"
            "  src/eugene_ws.py\n"
            "  src/foundation/router/patent_search_router.py\n"
            "  src/foundation/router/validate_util.py\n"
            "  src/foundation/conf/conf.py\n\n"
            "Read path (Cypher + mapping)\n"
            "  src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py\n"
            "  src/foundation/infra/db/util/pagination.py\n"
            "  src/foundation/mapper/patent_search_result_mapper.py\n"
            "  src/foundation/model/patent/patent_search_result.py\n\n"
            "ETL orchestrators\n"
            "  src/download_patents.py\n"
            "  src/patent/provider/patent_orchestrator.py\n"
            "  src/patent/conf/orchestator.py\n"
            "  src/patent/application/provider/application_orchestrator.py\n"
            "  src/patent/pgpub/provider/pgpub_orchestrator.py\n\n"
            "Pgpub upsert & linking\n"
            "  src/patent/pgpub/infra/db/adapter/neo4j_pgpub_adapter.py\n"
            "  src/patent/pgpub/infra/db/adapter/neo4j_pgpub_linking_adapter.py\n"
            "  src/patent/pgpub/infra/db/adapter/neo4j_pgpub_summary_adapter.py\n"
            "  src/patent/pgpub/infra/db/const.py\n"
            "  src/patent/application/infra/db/const.py\n\n"
            "LLM analysis\n"
            "  src/patent/pgpub/analyze/pgpub_knowledge_graph_analyzer.py\n"
            "  src/patent/pgpub/analyze/pgpub_graph_summary_orchestrator.py\n"
            "  src/patent/pgpub/conf/graphrag_conf.py\n"
            "  src/document/analyze/document_analyzer.py\n"
            "  src/infra/llm/prompt/generate.py\n"
            "  src/infra/llm/llm_factory.py\n"
            "  src/graph/mapper/triples_parser.py\n"
            "  src/graph/community/\n"
        ),
    ]

    return story


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        title="Eugene Patent Search - End-to-End Flow",
        author="Eugene Engineering",
    )
    doc.build(build())
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
