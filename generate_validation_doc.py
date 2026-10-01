#!/usr/bin/env python3
"""Generate Eugene Project Validation Document in DOCX and PDF formats."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCX_PATH = os.path.join(OUTPUT_DIR, "docs", "Eugene_Project_Validation_Document.docx")
PDF_PATH = os.path.join(OUTPUT_DIR, "docs", "Eugene_Project_Validation_Document.pdf")


def set_cell_shading(cell, color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    shading.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading)


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
        set_cell_shading(cell, "1F4E79")
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.color.rgb = RGBColor(255, 255, 255)
    # Data rows
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph("")


def add_bullet(doc, text, level=0, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(1.27 + level * 1.27)
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        run.font.size = Pt(10)
        run = p.add_run(text)
        run.font.size = Pt(10)
    else:
        run = p.add_run(text)
        run.font.size = Pt(10)


def add_body(doc, text):
    p = doc.add_paragraph(text)
    for run in p.runs:
        run.font.size = Pt(10)


def add_code_block(doc, code):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.0)
    run = p.add_run(code)
    run.font.name = "Courier New"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(30, 30, 30)


def build_document():
    doc = Document()

    # -- Page setup --
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # -- Styles --
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)
    style.paragraph_format.space_after = Pt(4)

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    for _ in range(6):
        doc.add_paragraph("")
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("euGENE")
    run.bold = True
    run.font.size = Pt(36)
    run.font.color.rgb = RGBColor(31, 78, 121)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Biomedical Knowledge Graph & Agentic AI Platform")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(89, 89, 89)

    doc.add_paragraph("")
    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = line.add_run("_" * 60)
    run.font.color.rgb = RGBColor(31, 78, 121)

    doc.add_paragraph("")
    doc_title = doc.add_paragraph()
    doc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = doc_title.add_run("PROJECT VALIDATION DOCUMENT")
    run.bold = True
    run.font.size = Pt(20)

    doc.add_paragraph("")
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run("Version 1.0  |  March 2026\nPrepared for CSL Behring\nConfidential")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(89, 89, 89)

    doc.add_page_break()

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    doc.add_heading("Table of Contents", level=1)
    toc_items = [
        "1. Executive Summary",
        "2. Background & Context",
        "3. Solution Overview",
        "4. Functional Requirements",
        "5. Non-Functional Requirements",
        "6. Architecture",
        "7. Tooling & Skills Design",
        "8. Knowledge & Data Strategy",
        "9. Security & Access Control",
        "10. Prompt Design",
        "11. Workflow Orchestration",
        "12. Deployment Model",
        "13. Monitoring & Observability",
        "14. Testing Strategy",
        "15. Risks & Mitigations",
        "16. Open Questions",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            run.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # 1. EXECUTIVE SUMMARY
    # =========================================================================
    doc.add_heading("1. Executive Summary", level=1)

    add_body(doc,
        "euGENE is a biomedical knowledge graph and agentic AI platform developed for "
        "CSL Behring to enable competitive intelligence across drugs, diseases, genes, "
        "proteins, patents, clinical trials, and organizations. The system integrates "
        "data from USPTO, PubMed, ClinicalTrials.gov, DrugBank, and internal CSL sources "
        "into a Neo4j graph database containing 129,375 nodes and 4,050,249 relationships."
    )
    add_body(doc,
        "The platform provides both a structured REST API for programmatic access and a "
        "conversational AI interface powered by LLM agents (Claude and GPT models) that "
        "can query the knowledge graph using natural language. The system follows a "
        "five-tier microservices architecture: Neo4j database, Core API (FastAPI), "
        "MCP Tool Server (FastMCP), Agent Backend (Strands framework), and Chat UI (Streamlit)."
    )
    add_body(doc,
        "Authentication is handled through Microsoft Entra ID (enterprise SSO) with a "
        "dual-layer JWT token system. The platform is deployed on AWS using Terraform "
        "infrastructure-as-code, with environments in both us-east-1 (difflabs/dev) and "
        "eu-central-1 (AIA/production). CI/CD is managed through GitLab pipelines."
    )

    add_table(doc,
        ["Metric", "Value"],
        [
            ["Total Graph Nodes", "129,375"],
            ["Total Relationships", "4,050,249"],
            ["Core API Endpoints", "38"],
            ["MCP Agent Tools", "12"],
            ["Microservices", "5 (Neo4j, API, MCP, Agent, UI)"],
            ["LLM Providers", "2 (Anthropic Claude, OpenAI GPT)"],
            ["AWS Environments", "2 (difflabs us-east-1, AIA eu-central-1)"],
            ["Authentication", "Microsoft Entra ID + Eugene JWT (HS256)"],
        ],
        col_widths=[6, 10],
    )

    # =========================================================================
    # 2. BACKGROUND & CONTEXT
    # =========================================================================
    doc.add_heading("2. Background & Context", level=1)

    doc.add_heading("2.1 Business Need", level=2)
    add_body(doc,
        "CSL Behring requires competitive intelligence capabilities to assess drug pipelines, "
        "disease research, patent landscapes, and organizational partnerships across the "
        "pharmaceutical industry. Existing tools lack the ability to traverse complex "
        "relationships between biomedical entities and provide actionable insights through "
        "natural language queries."
    )

    doc.add_heading("2.2 Project Scope", level=2)
    add_bullet(doc, "Build a knowledge graph from public biomedical data sources (DrugBank, ClinicalTrials.gov, USPTO, PubMed)")
    add_bullet(doc, "Expose graph data via REST API with authentication and role-based access")
    add_bullet(doc, "Provide an AI-powered conversational interface for natural language querying")
    add_bullet(doc, "Deploy on AWS with infrastructure-as-code and CI/CD automation")
    add_bullet(doc, "Support competitive analysis: drug pipelines, organizational assets, patent landscapes")

    doc.add_heading("2.3 Stakeholders", level=2)
    add_table(doc,
        ["Role", "Responsibility"],
        [
            ["CSL Behring R&D", "Primary consumers of competitive intelligence"],
            ["AI Accelerator Team (AIA)", "Platform hosting and infrastructure"],
            ["Diffusion Labs (difflabs)", "Development and DevOps environment"],
            ["Engineering Team", "Platform development and maintenance"],
        ],
        col_widths=[5, 11],
    )

    doc.add_heading("2.4 Technology Decisions", level=2)
    add_table(doc,
        ["Decision", "Choice", "Rationale"],
        [
            ["Graph Database", "Neo4j 5.26 Community", "Industry standard for knowledge graphs, Cypher query language, APOC/GDS plugins"],
            ["API Framework", "FastAPI (Python)", "Async support, auto-generated OpenAPI docs, Pydantic validation"],
            ["Agent Framework", "Strands (AWS)", "MCP integration, streaming support, conversation management"],
            ["LLM Protocol", "Model Context Protocol (MCP)", "Standard tool interface for LLMs, vendor-agnostic"],
            ["UI Framework", "Streamlit", "Rapid prototyping, built-in chat components, SSE streaming"],
            ["IaC", "Terraform", "Multi-environment deployment, state management, GitLab integration"],
            ["Auth", "Microsoft Entra ID", "Enterprise SSO requirement from CSL"],
        ],
        col_widths=[3.5, 4, 8.5],
    )

    # =========================================================================
    # 3. SOLUTION OVERVIEW
    # =========================================================================
    doc.add_heading("3. Solution Overview", level=1)

    doc.add_heading("3.1 System Architecture (Five-Tier)", level=2)
    add_code_block(doc,
        "+-------------------------------------------+\n"
        "|  TIER 5: Chat UI (Streamlit)              |\n"
        "|  Port 18501 | eugene-agent-ui             |\n"
        "+-------------------------------------------+\n"
        "                    |\n"
        "          HTTP POST /query/stream + JWT\n"
        "                    v\n"
        "+-------------------------------------------+\n"
        "|  TIER 4: Agent Backend (FastAPI+Strands)  |\n"
        "|  Port 18001 | eugene-agent-ws             |\n"
        "|  LLM: Claude / GPT                        |\n"
        "+-------------------------------------------+\n"
        "                    |\n"
        "          MCP HTTP Streaming + JWT\n"
        "                    v\n"
        "+-------------------------------------------+\n"
        "|  TIER 3: MCP Tool Server (FastMCP)        |\n"
        "|  Port 18443 | eugene-mcp                  |\n"
        "|  12 Knowledge Graph Tools                 |\n"
        "+-------------------------------------------+\n"
        "                    |\n"
        "          HTTP REST + JWT\n"
        "                    v\n"
        "+-------------------------------------------+\n"
        "|  TIER 2: Core API (FastAPI)               |\n"
        "|  Port 18000 | eugene-ws                   |\n"
        "|  38 REST Endpoints                        |\n"
        "+-------------------------------------------+\n"
        "                    |\n"
        "          Bolt Protocol (TLS)\n"
        "                    v\n"
        "+-------------------------------------------+\n"
        "|  TIER 1: Neo4j Graph Database             |\n"
        "|  Port 17687 | neo4j:5.26.9               |\n"
        "|  129K nodes, 4M relationships             |\n"
        "+-------------------------------------------+\n"
    )

    doc.add_heading("3.2 Service Inventory", level=2)
    add_table(doc,
        ["Service", "Technology", "Port (Local)", "Source Directory", "Purpose"],
        [
            ["neo4j", "Neo4j 5.26.9 CE", "17474/17687", "docker-compose.yml", "Graph database with APOC + GDS"],
            ["eugene_ws", "FastAPI + Uvicorn", "18000", "src/", "Core REST API (38 endpoints)"],
            ["eugene_mcp", "FastMCP", "18443", "agents/eugene-mcp/", "MCP tool server (12 tools)"],
            ["eugene_agent_ws", "FastAPI + Strands", "18001", "agents/eugene-agent-ws/", "LLM agent backend"],
            ["eugene_agent_ui", "Streamlit", "18501", "agents/eugene-agent-ui/", "Chat web interface"],
        ],
        col_widths=[2.8, 3, 2.5, 4, 4],
    )

    doc.add_heading("3.3 Code Architecture Pattern", level=2)
    add_body(doc,
        "The codebase follows Domain-Driven Design (DDD) with Hexagonal Architecture. "
        "Each domain module (foundation, organization, patent, pubmed, tpp, graph) has "
        "a consistent internal structure:"
    )
    add_code_block(doc,
        "<domain>/\n"
        "  +-- model/      # Pydantic data models & enums\n"
        "  +-- provider/    # Business logic & orchestration\n"
        "  +-- mapper/      # Data transformation (DataFrame -> Model -> Response)\n"
        "  +-- router/      # FastAPI endpoint definitions\n"
        "  +-- conf/        # Dependency injection (factory functions)\n"
        "  +-- infra/       # Database adapters (Neo4j)\n"
        "  +-- writer/      # Persistence & checkpointing\n"
        "  +-- load/        # Load from disk/checkpoints\n"
    )
    add_body(doc,
        "Dependency injection is manual via conf.py factory functions. There is no DI "
        "framework; each domain's conf.py instantiates adapters, providers, mappers, "
        "and routers with explicit wiring."
    )

    # =========================================================================
    # 4. FUNCTIONAL REQUIREMENTS
    # =========================================================================
    doc.add_heading("4. Functional Requirements", level=1)

    doc.add_heading("4.1 Core API Capabilities", level=2)
    add_table(doc,
        ["Category", "Endpoints", "Description"],
        [
            ["Authentication", "GET /login, GET /auth/whoami, GET /auth-callback", "Entra ID OAuth + Eugene JWT issuance"],
            ["Health & Info", "GET /health, GET /, GET /releases", "System health, welcome, release notes"],
            ["Database Stats", "GET /stats", "Node/relationship counts, data distribution"],
            ["Node Lookup", "GET /node/find/{value}, POST /node/details", "Find node IDs, get detailed node info"],
            ["Graph Navigation", "GET /graph/relationship/start/{id}, GET /graph/path/start/{id}/end/{id}", "N-hop subgraph, shortest path, reachability"],
            ["Graph Facts", "GET /graph/facts/start/{id}", "English-language facts from relationships"],
            ["Labels & Counts", "GET /labels/{label}, GET /count/{label}", "List/count nodes by type"],
            ["Drug Aliases", "GET /drugs/aliases/{name}, GET /drugs/aliases/id/{id}", "Drug synonyms and brand names"],
            ["Patent Search", "GET /patents/drugs, /clinicaltrials, /geneproteins + counts", "Patent lookup by drug/trial/gene"],
            ["PubMed Search", "GET /pmids/drugs, /clinicaltrials, /geneproteins + counts", "Article lookup by drug/trial/gene"],
            ["Facet & Similarity", "POST /facet/{label}, POST /similarity/{label}", "Faceted search, vector similarity"],
            ["Organizations", "GET /organizations/{name}, GET /organizations/assets/{id}", "Org search, asset discovery"],
        ],
        col_widths=[3, 5.5, 7.5],
    )

    doc.add_heading("4.2 Agent Capabilities (MCP Tools)", level=2)
    add_table(doc,
        ["Tool", "Method", "Purpose"],
        [
            ["fetch_identity", "EugeneIdentityTools", "Retrieve current user identity from JWT"],
            ["fetch_by_label", "EugeneFetchTools", "List drugs or diseases with pagination"],
            ["fetch_similar", "EugeneFetchTools", "Find similar nodes by relationship patterns"],
            ["lookup_node_by_value", "EugeneNodeTools", "Resolve entity name to node ID (fuzzy match)"],
            ["fetch_node_details", "EugeneNodeTools", "Get detailed node attributes by ID"],
            ["fetch_drug_aliases", "EugeneDrugTools", "Get all drug synonyms and brand names"],
            ["fetch_facts", "EugeneFactTools", "Paginated facts retrieval (up to 50 pages)"],
            ["fetch_node_relationships", "EugeneGraphTools", "N-hop relationship traversal"],
            ["fetch_paths", "EugeneGraphTools", "Find path between two nodes"],
            ["has_reachable_path", "EugeneGraphTools", "Check reachability between nodes"],
            ["find_organization_names", "EugeneOrganizationTools", "Wildcard search for organizations"],
            ["find_organization_assets", "EugeneOrganizationTools", "Get org assets (drugs, patents, trials)"],
        ],
        col_widths=[4, 4, 8],
    )

    doc.add_heading("4.3 Chat Interface Features", level=2)
    add_bullet(doc, "Real-time streaming responses via Server-Sent Events (SSE)")
    add_bullet(doc, "Conversation history with session persistence")
    add_bullet(doc, "Tool selection checkboxes (eugene, pubmed, http)")
    add_bullet(doc, "OAuth token input for authenticated access")
    add_bullet(doc, "Suggestion pills for common queries (e.g., drug aliases, org assets)")
    add_bullet(doc, "New conversation management with UUID tracking")

    # =========================================================================
    # 5. NON-FUNCTIONAL REQUIREMENTS
    # =========================================================================
    doc.add_heading("5. Non-Functional Requirements", level=1)

    add_table(doc,
        ["Requirement", "Target", "Implementation"],
        [
            ["Availability", "99.5% uptime", "ECS with health checks, auto-restart on failure"],
            ["Scalability", "Horizontal scaling", "Stateless HTTP services, Docker containerization"],
            ["Response Time", "< 5s for graph queries", "Neo4j APOC optimized queries, pagination"],
            ["Security", "Enterprise-grade auth", "Entra ID SSO + JWT + role-based access"],
            ["Data Freshness", "Batch updates", "Data ingestion scripts, S3-based loading"],
            ["Observability", "CloudWatch monitoring", "Health endpoints, API canaries, logging"],
            ["Portability", "Multi-environment", "Docker Compose (local), ECS (cloud), Terraform IaC"],
            ["Maintainability", "DDD architecture", "Hexagonal pattern, domain isolation, test coverage"],
        ],
        col_widths=[3.5, 4, 8.5],
    )

    # =========================================================================
    # 6. ARCHITECTURE
    # =========================================================================
    doc.add_heading("6. Architecture", level=1)

    doc.add_heading("6.1 Data Flow", level=2)
    add_body(doc, "The system implements a layered data flow from user query to database and back:")
    add_code_block(doc,
        "User Query (natural language)\n"
        "  -> Streamlit UI (eugene_agent_ui)\n"
        "    -> POST /agent/api/query/stream with JWT\n"
        "      -> Agent Backend (eugene_agent_ws)\n"
        "        -> Strands Agent with ReAct pattern\n"
        "          -> MCP Tool Calls (eugene_mcp)\n"
        "            -> HTTP REST calls to Core API (eugene_ws)\n"
        "              -> Neo4j Cypher queries\n"
        "              <- Graph results (nodes, relationships)\n"
        "            <- Structured JSON responses\n"
        "          <- Tool results aggregated\n"
        "        <- LLM generates natural language answer\n"
        "      <- SSE stream chunks\n"
        "    <- Real-time display with cursor\n"
        "  <- Final answer displayed in chat\n"
    )

    doc.add_heading("6.2 Authentication Flow", level=2)
    add_code_block(doc,
        "PRODUCTION FLOW:\n"
        "  User -> GET /login\n"
        "       -> Redirect to Microsoft Entra ID\n"
        "       -> User authenticates with corporate SSO\n"
        "       -> Entra returns ID token (RS256, OIDC)\n"
        "       -> Backend validates via JWKS endpoint (8h cache)\n"
        "       -> Backend issues Eugene JWT (HS256, 24h TTL)\n"
        "       -> Token includes: tid, sub, upn, roles\n"
        "\n"
        "LOCAL DEV FLOW:\n"
        "  User -> GET /login (ENVIRONMENT=local)\n"
        "       -> Immediate Eugene JWT issued\n"
        "       -> User: eugene.test@cslhering.com\n"
        "       -> Roles: [user.public.read]\n"
        "\n"
        "TOKEN FORWARDING:\n"
        "  UI -> Agent WS (validates JWT + checks allowlist)\n"
        "     -> MCP Server (JWTVerifier middleware)\n"
        "     -> Core API (get_current_user dependency)\n"
    )

    doc.add_heading("6.3 Neo4j Graph Schema", level=2)
    add_table(doc,
        ["Node Label", "Count", "Source", "Key Properties"],
        [
            ["drug", "4,600", "DrugBank", "node_id, node_name, description, drugbank_id"],
            ["disease", "17,100", "Disease Ontology", "node_id, node_name, MONDO_ID, MONDO_NAME"],
            ["gene_protein", "27,700", "Protein DBs", "node_id, node_name, annotation"],
            ["clinical_trial", "49,300", "ClinicalTrials.gov", "node_id, node_name, nct_id"],
            ["organization", "26,100", "Company/Sponsor", "node_id, node_name, disambiguated"],
            ["pathway", "Various", "Pathway DBs", "node_id, node_name"],
            ["anatomy", "Various", "Anatomical Ontology", "node_id, node_name"],
            ["patent", "Pending", "USPTO", "node_id, node_name, patent_number"],
            ["pubmed_document", "Pending", "PubMed/PMC", "pmid, title, doi"],
        ],
        col_widths=[3, 2, 3, 8],
    )

    doc.add_heading("6.4 Relationship Types", level=2)
    add_table(doc,
        ["Category", "Relationships"],
        [
            ["Therapeutic", "indication, contraindication, off_label_use, drug_effect"],
            ["Biological", "drug_protein, disease_protein, pathway_protein, protein_protein"],
            ["Phenotypic", "disease_phenotype_positive, disease_phenotype_negative"],
            ["Anatomical", "anatomy_protein_present, anatomy_protein_absent"],
            ["Disease", "disease_disease (comorbidities)"],
            ["Drug", "drug_drug, has_drug_alias"],
            ["Publication", "disclosed_in, featured_in, analyzed_in, has_publication"],
            ["Organizational", "sponsor, patent_holder, partnership"],
        ],
        col_widths=[3.5, 12.5],
    )

    # =========================================================================
    # 7. TOOLING & SKILLS DESIGN
    # =========================================================================
    doc.add_heading("7. Tooling & Skills Design", level=1)

    doc.add_heading("7.1 MCP Server Architecture", level=2)
    add_body(doc,
        "The MCP (Model Context Protocol) server exposes knowledge graph capabilities "
        "as callable tools for LLM agents. Built with FastMCP framework, it provides "
        "12 tools organized into 5 tool classes:"
    )
    add_table(doc,
        ["Tool Class", "Tools", "Purpose"],
        [
            ["EugeneIdentityTools", "fetch_identity", "User authentication validation"],
            ["EugeneFetchTools", "fetch_by_label, fetch_similar", "Browse and find similar entities"],
            ["EugeneNodeTools", "lookup_node_by_value, fetch_node_details", "Entity resolution and details"],
            ["EugeneDrugTools", "fetch_drug_aliases", "Drug name/synonym lookup"],
            ["EugeneFactTools", "fetch_facts", "Natural language fact extraction"],
            ["EugeneGraphTools", "fetch_node_relationships, fetch_paths, has_reachable_path", "Graph traversal and pathfinding"],
            ["EugeneOrganizationTools", "find_organization_names, find_organization_assets", "Company research and asset discovery"],
        ],
        col_widths=[4, 5.5, 6.5],
    )

    doc.add_heading("7.2 Tool Implementation Pattern", level=2)
    add_body(doc, "Each MCP tool follows a consistent pattern:")
    add_bullet(doc, "Extracts JWT token from MCP request context")
    add_bullet(doc, "Makes async HTTP call to Core API with token forwarding")
    add_bullet(doc, "Handles pagination automatically (up to 10-50 pages)")
    add_bullet(doc, "Returns structured JSON or formatted text")
    add_bullet(doc, "Timeout: 30 seconds per HTTP request")
    add_bullet(doc, "Error handling: Returns None on failure with logging")

    doc.add_heading("7.3 Local Agent Tools", level=2)
    add_body(doc, "The agent backend also provides local (non-MCP) tools:")
    add_bullet(doc, "calculator - Mathematical computations")
    add_bullet(doc, "current_time - Current timestamp retrieval")
    add_bullet(doc, "python_repl - Python code execution sandbox")
    add_bullet(doc, "http_request - General HTTP requests (optional, on-demand)")

    doc.add_heading("7.4 Future Tools (Planned)", level=2)
    add_bullet(doc, "PUBMED - Direct PubMed article search and retrieval")
    add_bullet(doc, "CLINICAL_TRIALS - ClinicalTrials.gov API integration")
    add_bullet(doc, "CHEMBL - ChEMBL chemical database queries")
    add_bullet(doc, "BIORXIV - BioRxiv preprint search")

    # =========================================================================
    # 8. KNOWLEDGE & DATA STRATEGY
    # =========================================================================
    doc.add_heading("8. Knowledge & Data Strategy", level=1)

    doc.add_heading("8.1 Data Sources", level=2)
    add_table(doc,
        ["Source", "Data Type", "Ingestion Method", "Status"],
        [
            ["DrugBank", "Drugs, drug-disease, drug-protein relationships", "CSV bulk import (neo4j-admin)", "Loaded (4.6K drugs)"],
            ["Disease Ontology", "Diseases, MONDO mappings", "CSV bulk import", "Loaded (17.1K diseases)"],
            ["Protein Databases", "Genes, proteins, pathways", "CSV bulk import", "Loaded (27.7K genes)"],
            ["ClinicalTrials.gov", "Clinical trials, sponsors", "CSV + Cypher scripts", "Schema only (49.3K nodes)"],
            ["USPTO", "Patents, applications, claims", "API download + Cypher", "Not yet ingested"],
            ["PubMed/PMC", "Articles, affiliations, DOIs", "API download + Cypher", "Not yet ingested"],
            ["CSL Internal", "TPP, organizational data", "Manual + checkpoint files", "Partial"],
        ],
        col_widths=[3, 5, 4, 4],
    )

    doc.add_heading("8.2 Data Ingestion Pipeline", level=2)
    add_body(doc, "Data loading follows a three-phase approach:")
    add_bullet(doc, "Phase 1: Foundational bulk import using neo4j-admin (nodes.csv + edges_dedup.csv) - 129K nodes, 4M relationships in 7.6 seconds")
    add_bullet(doc, "Phase 2: Feature enrichment via APOC batch loading - Disease features (44K, ~53 min), Drug features (8K, ~9.5 min)")
    add_bullet(doc, "Phase 3: Supplementary data via Cypher scripts and API downloads (clinical trials, patents, PubMed)")

    doc.add_heading("8.3 Embedding Strategy", level=2)
    add_bullet(doc, "Model: minishlab/potion-base-8M (lightweight, fast inference)")
    add_bullet(doc, "Purpose: Semantic search across drugs, diseases, and documents")
    add_bullet(doc, "Storage: Neo4j node properties + Milvus vector database (lite mode)")
    add_bullet(doc, "Pre-caching: Models pre-downloaded from S3 in production containers")

    doc.add_heading("8.4 Graph Analytics", level=2)
    add_bullet(doc, "Neo4j Graph Data Science (GDS) plugin for in-memory graph projections")
    add_bullet(doc, "Node Similarity: Cosine distance between node embeddings")
    add_bullet(doc, "Community Detection: Leiden algorithm for identifying clusters")
    add_bullet(doc, "GraphSAGE: Node embedding pipeline (project -> train -> predict)")
    add_bullet(doc, "Link Prediction: GDS beta pipeline for relationship prediction")

    # =========================================================================
    # 9. SECURITY & ACCESS CONTROL
    # =========================================================================
    doc.add_heading("9. Security & Access Control", level=1)

    doc.add_heading("9.1 Authentication Architecture", level=2)
    add_table(doc,
        ["Layer", "Mechanism", "Algorithm", "Details"],
        [
            ["Enterprise SSO", "Microsoft Entra ID", "RS256 (OIDC)", "Corporate identity, JWKS validation, 8h cache"],
            ["API Tokens", "Eugene JWT", "HS256 (symmetric)", "24h TTL, claims: tid, sub, upn, roles"],
            ["MCP Server", "FastMCP JWTVerifier", "HS256", "Middleware-based, validates every tool call"],
            ["Agent Backend", "Allowlist + JWT", "HS256", "User UPN checked against pipe-separated allowlist"],
            ["Local Dev", "Bypass mode", "HS256", "ENVIRONMENT=local skips Entra ID, issues test token"],
        ],
        col_widths=[3, 3.5, 3, 6.5],
    )

    doc.add_heading("9.2 Role-Based Access Control", level=2)
    add_table(doc,
        ["Role", "Scope", "Status"],
        [
            ["user.public.read", "Read access to public biomedical data", "Implemented (default for all users)"],
            ["user.confidential.read", "Read access to proprietary CSL data", "Defined, not yet enforced at query level"],
        ],
        col_widths=[4, 6, 6],
    )
    add_body(doc,
        "Role mapping is currently static in code (roles.py). Named users from CSL are "
        "assigned both public and confidential roles. All other authenticated users receive "
        "the default public read role."
    )

    doc.add_heading("9.3 Token Flow Through Services", level=2)
    add_code_block(doc,
        "Client -> Authorization: Bearer <EUGENE_JWT>\n"
        "  -> Agent WS: validate JWT + check allowlist\n"
        "    -> MCP Server: JWTVerifier middleware validates\n"
        "      -> Core API: get_current_user() dependency validates\n"
        "        -> Neo4j: Cypher query execution\n"
        "\n"
        "Each service independently validates the JWT.\n"
        "Token is forwarded (not re-issued) through the chain.\n"
    )

    doc.add_heading("9.4 Security Configuration", level=2)
    add_table(doc,
        ["Variable", "Purpose", "Service"],
        [
            ["ENTRA_CLIENT_ID", "OAuth application ID", "eugene_ws"],
            ["ENTRA_CLIENT_SECRET", "OAuth client secret", "eugene_ws"],
            ["ENTRA_TENANT_ID", "Azure AD tenant", "eugene_ws"],
            ["EUGENE_CLIENT_ID", "JWT audience claim", "All services"],
            ["EUGENE_CLIENT_SECRET", "JWT signing key (HS256)", "All services"],
            ["EUGENE_TENANT_ID", "JWT issuer tenant", "All services"],
            ["EUGENE_AGENT_ALLOWLIST", "Pipe-separated user UPNs", "eugene_agent_ws"],
            ["NEO4J_USERNAME/PASSWORD", "Database credentials", "eugene_ws"],
        ],
        col_widths=[4.5, 5.5, 6],
    )

    doc.add_heading("9.5 Known Security Items", level=2)
    add_table(doc,
        ["Item", "Severity", "Status", "Description"],
        [
            ["Cypher Injection", "HIGH", "Open", "User input not parameterized in one-hop adapter query builder"],
            ["SSL verify=False", "MEDIUM", "By Design", "Internal network; MCP/Agent HTTP clients skip TLS verification"],
            ["Self-signed TLS certs", "LOW", "Active", "Neo4j and ALB use self-signed certificates"],
            ["No rate limiting", "MEDIUM", "Open", "API endpoints have no rate limiting middleware"],
            ["SAST/DAST disabled", "MEDIUM", "Open", "Security scanning commented out in CI pipeline"],
            ["Static role mapping", "LOW", "Open", "Roles hard-coded; should migrate to database"],
        ],
        col_widths=[3.5, 2.5, 2.5, 7.5],
    )

    # =========================================================================
    # 10. PROMPT DESIGN
    # =========================================================================
    doc.add_heading("10. Prompt Design", level=1)

    doc.add_heading("10.1 Agent System Prompt", level=2)
    add_body(doc, "The agent backend uses the following system prompt for LLM interactions:")
    add_code_block(doc,
        '"You are an agent tasked with helping investigate biomedical\n'
        'companies to assess competitive threat and collaboration\n'
        'opportunities. In our case assets here mean any drug, disease,\n'
        'patents, clinical trials, intellectual property, or financial\n'
        'deals the company may have involvement. As an agent follow the\n'
        'Reason, Act, Observe (ReAct) pattern. You are an agent that\n'
        'may call tools to retrieve data."'
    )

    doc.add_heading("10.2 ReAct Pattern", level=2)
    add_body(doc, "The agent follows the Reason-Act-Observe (ReAct) pattern:")
    add_bullet(doc, "Reason: LLM analyzes user query and determines what information is needed", bold_prefix="Reason: ")
    add_bullet(doc, "Act: LLM selects and calls appropriate MCP tools with correct parameters", bold_prefix="Act: ")
    add_bullet(doc, "Observe: LLM reviews tool results and determines if more tools are needed", bold_prefix="Observe: ")
    add_bullet(doc, "Repeat until sufficient information gathered, then generate final answer")

    doc.add_heading("10.3 Conversation Management", level=2)
    add_bullet(doc, "Sliding window: 10-message history retained per conversation")
    add_bullet(doc, "Result truncation: Max 2 items per tool response per turn")
    add_bullet(doc, "Session persistence: FileSessionManager stores conversation state")
    add_bullet(doc, "Conversation ID: UUID-based tracking across multiple turns")

    doc.add_heading("10.4 LLM Configuration", level=2)
    add_table(doc,
        ["Provider", "Model", "Max Tokens", "Temperature", "Top-P"],
        [
            ["Anthropic", "claude-sonnet-4-20250514", "16,384", "0.7", "N/A"],
            ["OpenAI", "gpt-4.1-mini (default)", "4,096", "0.7", "1.0"],
        ],
        col_widths=[3, 4.5, 3, 3, 2.5],
    )
    add_body(doc,
        "Provider auto-detection: If LLM_PROVIDER is not set, the system prefers Anthropic "
        "if ANTHROPIC_API_KEY is available, otherwise falls back to OpenAI."
    )

    # =========================================================================
    # 11. WORKFLOW ORCHESTRATION
    # =========================================================================
    doc.add_heading("11. Workflow Orchestration", level=1)

    doc.add_heading("11.1 Query Execution Flow (Streaming)", level=2)
    add_code_block(doc,
        "1. User submits prompt via Streamlit UI\n"
        "2. UI sends POST /agent/api/query/stream with JWT + prompt\n"
        "3. Agent WS validates JWT and checks user allowlist\n"
        "4. Agent WS initializes EugeneDataAgent:\n"
        "   a. Creates LLM model (OpenAI or Anthropic)\n"
        "   b. Connects to MCP server with JWT\n"
        "   c. Lists available MCP tools\n"
        "   d. Initializes local tools (calculator, current_time, etc.)\n"
        "   e. Creates Strands Agent with system prompt\n"
        "5. Agent executes user prompt with ReAct loop:\n"
        "   a. LLM reasons about query\n"
        "   b. LLM calls MCP tools as needed\n"
        "   c. MCP tools call Core API with JWT forwarding\n"
        "   d. Core API executes Neo4j Cypher queries\n"
        "   e. Results bubble back through chain\n"
        "   f. LLM generates next step or final answer\n"
        "6. Streaming events sent to UI:\n"
        '   - {"type": "session", "session_id": "..."}\n'
        '   - {"type": "content", "content": "chunk..."}\n'
        '   - {"type": "done"}\n'
        "7. UI displays tokens in real-time with cursor\n"
        "8. Metrics logged: tokens, execution time, tools used\n"
    )

    doc.add_heading("11.2 Startup Orchestration", level=2)
    add_body(doc, "Docker Compose manages service startup order via health check dependencies:")
    add_code_block(doc,
        "neo4j (healthcheck: wget localhost:7474, 30s startup)\n"
        "  -> eugene_ws (depends: neo4j healthy; healthcheck: urllib localhost:8000/health)\n"
        "    -> eugene_mcp (depends: eugene_ws healthy)\n"
        "      -> eugene_agent_ws (depends: eugene_mcp)\n"
        "        -> eugene_agent_ui (depends: eugene_agent_ws)\n"
    )

    doc.add_heading("11.3 Data Ingestion Workflow", level=2)
    add_code_block(doc,
        "Phase 1: Bulk Import\n"
        "  - Stop Neo4j service\n"
        "  - Run neo4j-admin database import full\n"
        "  - Input: nodes.csv + edges_dedup.csv from S3\n"
        "  - Result: 129K nodes, 4M relationships (7.6 seconds)\n"
        "  - Restart Neo4j service\n"
        "\n"
        "Phase 2: Feature Enrichment\n"
        "  - Run batch_load_disease_features.py (44K features, ~53 min)\n"
        "  - Run batch_load_drug_features.py (8K features, ~9.5 min)\n"
        "  - Uses APOC batch transactions (1000 rows/batch)\n"
        "\n"
        "Phase 3: Supplementary Data\n"
        "  - Clinical trials: Cypher scripts (schema exists, data cleared)\n"
        "  - Patents: USPTO API download (not yet executed)\n"
        "  - PubMed: API download + APOC loading (not yet executed)\n"
    )

    # =========================================================================
    # 12. DEPLOYMENT MODEL
    # =========================================================================
    doc.add_heading("12. Deployment Model", level=1)

    doc.add_heading("12.1 Environment Overview", level=2)
    add_table(doc,
        ["Environment", "AWS Account", "Region", "Infrastructure", "Deployment Method"],
        [
            ["Local Dev", "N/A", "N/A", "Docker Compose", "docker compose up --build"],
            ["difflabs (Dev)", "087084717211", "us-east-1", "ECS + EC2 + ALB", "Manual scripts (bin/docker/ecr/)"],
            ["AIA (Staging/Prod)", "010928221940", "eu-central-1", "ECS + EC2 + ALB", "GitLab CI/CD pipeline"],
        ],
        col_widths=[3, 3, 2.5, 3.5, 4],
    )

    doc.add_heading("12.2 Docker Images", level=2)
    add_table(doc,
        ["Image", "Base", "Size Factor", "Special Dependencies"],
        [
            ["eugene_ws", "python:3.13-slim", "Large (PyTorch CPU)", "torch, transformers, sentence-transformers"],
            ["eugene_mcp", "python:3.13-slim", "Small", "fastmcp, httpx, mcp"],
            ["eugene_agent_ws", "python:3.13-slim", "Medium", "strands-agents, anthropic, openai"],
            ["eugene_agent_ui", "python:3.13-slim", "Small", "streamlit, httpx"],
            ["eugene_neo4j_ce", "neo4j:5.26.9-community", "Medium", "APOC, GDS, AWS CLI, SSM Agent"],
        ],
        col_widths=[3.5, 3.5, 3, 6],
    )

    doc.add_heading("12.3 CI/CD Pipeline (GitLab)", level=2)
    add_code_block(doc,
        "Stages:\n"
        "  1. echo         - Debug output (commit info)\n"
        "  2. scan         - Checkov security scanning (HIGH/CRITICAL fail)\n"
        "  3. docker       - Build & push images to ECR\n"
        "  4. terraform-ec2    - Plan EC2 infrastructure\n"
        "  5. apply-ec2        - Apply EC2 (manual approval)\n"
        "  6. terraform-services - Plan ECS services\n"
        "  7. apply-services    - Apply ECS (manual approval)\n"
        "\n"
        "Branch Strategy:\n"
        "  - feature/* -> Docker build only\n"
        "  - qa        -> Full deploy to staging\n"
        "  - main      -> Full deploy to production\n"
        "\n"
        "Authentication:\n"
        "  - GitLab OIDC -> AWS STS assume-role-with-web-identity\n"
        "  - Role: arn:aws:iam::010928221940:role/csl-gitlab-ci-cd-scop-all-branches\n"
    )

    doc.add_heading("12.4 Terraform Modules", level=2)
    add_table(doc,
        ["Module", "Resources", "Key Variables"],
        [
            ["eugene-ec2", "EC2 (r7i.xlarge), EBS, Security Groups, IAM Profile", "vpc_id, subnet, instance_type, availability_zone"],
            ["eugene-services", "ECS Cluster, Task Definitions, ALB Target Groups", "ecs_cluster_name, subnets, image_hashes, IAM roles"],
        ],
        col_widths=[3, 6, 7],
    )

    doc.add_heading("12.5 Production Entrypoint", level=2)
    add_body(doc, "Production containers use entrypoint.sh scripts that:")
    add_bullet(doc, "Download .env from S3 (s3://aia-scop-experiment-eugene-data/runtime/.env)")
    add_bullet(doc, "Export environment variables")
    add_bullet(doc, "Download pre-cached HuggingFace models from S3")
    add_bullet(doc, "Start the application server (uvicorn or streamlit)")

    # =========================================================================
    # 13. MONITORING & OBSERVABILITY
    # =========================================================================
    doc.add_heading("13. Monitoring & Observability", level=1)

    doc.add_heading("13.1 Health Checks", level=2)
    add_table(doc,
        ["Service", "Endpoint", "Method", "Interval"],
        [
            ["neo4j", "http://localhost:7474", "wget spider", "10s (30s startup)"],
            ["eugene_ws", "http://localhost:8000/health", "Python urllib", "10s (15s startup)"],
            ["eugene_mcp", "http://localhost:8000/health", "HTTP GET", "On demand"],
            ["eugene_agent_ws", "http://localhost:8000/health", "HTTP GET", "On demand"],
            ["eugene_agent_ui", "http://localhost:8501", "Streamlit built-in", "On demand"],
        ],
        col_widths=[3.5, 5, 3.5, 4],
    )

    doc.add_heading("13.2 API Canaries", level=2)
    add_body(doc,
        "The api-canaries service provides automated monitoring of Core API endpoints:"
    )
    add_table(doc,
        ["Canary", "Endpoint Tested", "Validation"],
        [
            ["HealthEndpointCanary", "GET /health", "Response 200 OK"],
            ["StatsEndpointCanary", "GET /stats", "Valid node/relationship counts"],
            ["NodeFindEndpointCanary", "GET /node/find/{value}", "Node ID returned"],
            ["NodeDetailsEndpointCanary", "POST /node/details", "Node attributes returned"],
            ["LabelCountsEndpointCanary", "GET /count/{label}", "Non-zero counts"],
        ],
        col_widths=[4.5, 5, 6.5],
    )

    doc.add_heading("13.3 Database Statistics", level=2)
    add_body(doc, "The /stats endpoint provides real-time database health metrics:")
    add_code_block(doc,
        '{\n'
        '  "node_count": "484.3k",\n'
        '  "relationship_count": "21.4m",\n'
        '  "drug_count": "4.6k",\n'
        '  "disease_count": "17.1k",\n'
        '  "gene_protein_count": "27.7k",\n'
        '  "clinical_trial_count": "49.3k",\n'
        '  "organization_count": "26.1k"\n'
        '}\n'
    )

    doc.add_heading("13.4 Agent Metrics", level=2)
    add_bullet(doc, "Total tokens used per LLM call")
    add_bullet(doc, "Execution time per agent invocation (seconds, 4 decimal precision)")
    add_bullet(doc, "Tools used per query (unique tool names)")
    add_bullet(doc, "Cycle durations (time per ReAct loop iteration)")
    add_bullet(doc, "Performance decorator (@log_time) on critical functions")

    doc.add_heading("13.5 Logging", level=2)
    add_bullet(doc, "Application-level logging at INFO level (configurable)")
    add_bullet(doc, "Neo4j container logs persisted to Docker volume (eugene_neo4j_logs)")
    add_bullet(doc, "CloudWatch integration for ECS-deployed services")
    add_bullet(doc, "Structured log format with function names and timing")

    # =========================================================================
    # 14. TESTING STRATEGY
    # =========================================================================
    doc.add_heading("14. Testing Strategy", level=1)

    doc.add_heading("14.1 Test Framework", level=2)
    add_table(doc,
        ["Component", "Configuration"],
        [
            ["Framework", "pytest 7.0+"],
            ["Parallelism", "pytest-xdist (-n 2, 2 workers)"],
            ["Coverage", "pytest-cov (src/ directory, LCOV + terminal output)"],
            ["Markers", "serial (no parallelization), integration (integration tests)"],
            ["Environment", "Loads .env file via pytest-dotenv"],
            ["Formatter", "Black (line-length 88)"],
            ["Linter", "Ruff, mypy"],
        ],
        col_widths=[4, 12],
    )

    doc.add_heading("14.2 Test Coverage Areas", level=2)
    add_table(doc,
        ["Domain", "Test Modules", "Type"],
        [
            ["Organization", "name_verifier_mapper_test, resolution_mapper_test, provider tests (4)", "Unit"],
            ["Utility", "regex_validation_test", "Unit"],
            ["Graph Infrastructure", "conftest.py fixtures", "Integration fixtures"],
            ["Foundation", "Various adapter/provider tests", "Unit + Integration"],
            ["Patent", "Patent adapter tests", "Unit"],
            ["Document", "Document analysis tests", "Unit"],
        ],
        col_widths=[3.5, 7.5, 5],
    )

    doc.add_heading("14.3 Test Execution", level=2)
    add_code_block(doc,
        "# Run all tests with coverage\n"
        "pytest\n"
        "\n"
        "# Run specific domain tests\n"
        "pytest src/organization/\n"
        "\n"
        "# Run with more parallelism\n"
        "pytest -n 4\n"
        "\n"
        "# Run integration tests only\n"
        "pytest -m integration\n"
        "\n"
        "# Run serial tests (database-dependent)\n"
        "pytest -m serial\n"
    )

    doc.add_heading("14.4 Pre-Commit Hooks", level=2)
    add_bullet(doc, "Terraform validation (difflabs/iac/ modules)")
    add_bullet(doc, "Black code formatter on src/")
    add_bullet(doc, "Full pytest suite execution")
    add_bullet(doc, "Exit code: 0 (all pass) or 1 (any failure blocks commit)")

    doc.add_heading("14.5 CI/CD Testing", level=2)
    add_bullet(doc, "Checkov security scanning on Terraform (fail on HIGH/CRITICAL)")
    add_bullet(doc, "Docker image build validation (all 5 services)")
    add_bullet(doc, "SAST/DAST scanning defined but currently disabled in pipeline")

    doc.add_heading("14.6 Recommended Additional Testing", level=2)
    add_bullet(doc, "End-to-end: UI -> Agent WS -> MCP -> Core API -> Neo4j flow")
    add_bullet(doc, "JWT validation edge cases (expired, invalid signature, missing claims)")
    add_bullet(doc, "MCP tool pagination with large result sets")
    add_bullet(doc, "Concurrent streaming requests under load")
    add_bullet(doc, "LLM provider failover (Anthropic -> OpenAI)")
    add_bullet(doc, "Network timeout and MCP server unavailability handling")

    # =========================================================================
    # 15. RISKS & MITIGATIONS
    # =========================================================================
    doc.add_heading("15. Risks & Mitigations", level=1)

    add_table(doc,
        ["Risk", "Severity", "Likelihood", "Mitigation", "Status"],
        [
            ["Cypher injection in one-hop adapter", "HIGH", "MEDIUM", "Parameterize all Cypher queries using $variables", "OPEN"],
            ["No API rate limiting", "MEDIUM", "MEDIUM", "Implement FastAPI middleware (slowapi or custom)", "OPEN"],
            ["Self-signed TLS certificates", "LOW", "HIGH", "Migrate to AWS ACM for automatic renewal", "OPEN"],
            ["Neo4j Community Edition limits", "MEDIUM", "LOW", "Upgrade to Enterprise for RBAC, clustering", "DEFERRED"],
            ["SAST/DAST scanning disabled", "MEDIUM", "HIGH", "Re-enable Checkov and add Snyk/Trivy scanning", "OPEN"],
            ["Static role mapping in code", "LOW", "LOW", "Migrate to database-backed role management", "OPEN"],
            ["Incomplete data (patents, PubMed)", "MEDIUM", "HIGH", "Execute pending ingestion pipelines", "IN PROGRESS"],
            ["Single MCP instance bottleneck", "MEDIUM", "LOW", "Implement S3SessionManager for horizontal scale", "PLANNED"],
            ["AIA deployment broken", "HIGH", "HIGH", "Fix ECS IAM permission issue", "OPEN"],
            ["API key exposure in docker.env", "HIGH", "LOW", "Ensure .gitignore excludes docker.env; use Secrets Manager", "MITIGATED"],
            ["Python version variance (3.12/3.13)", "LOW", "LOW", "Standardize on single Python version across all containers", "OPEN"],
            ["LLM provider outage", "MEDIUM", "LOW", "Dual provider support (auto-fallback Anthropic <-> OpenAI)", "PARTIAL"],
        ],
        col_widths=[4, 2, 2, 5, 2.5],
    )

    # =========================================================================
    # 16. OPEN QUESTIONS
    # =========================================================================
    doc.add_heading("16. Open Questions", level=1)

    add_table(doc,
        ["#", "Question", "Context", "Priority"],
        [
            ["1", "When will patent and PubMed data ingestion be completed?", "Code exists but data not loaded; impacts agent answer quality", "HIGH"],
            ["2", "Should role-based data filtering be enforced at API or database level?", "Neo4j CE lacks native RBAC; application-level filtering required", "MEDIUM"],
            ["3", "What is the plan for AIA deployment ECS IAM fix?", "Production deployment blocked by permission issue", "HIGH"],
            ["4", "Should the MCP server scale horizontally with S3SessionManager?", "Current FileSessionManager limits to single instance", "MEDIUM"],
            ["5", "Is the qa branch ready to merge into main?", "Branches are currently desynced; may cause deployment issues", "HIGH"],
            ["6", "Should SAST/DAST scanning be mandatory for all merge requests?", "Currently commented out in pipeline; security gap", "MEDIUM"],
            ["7", "What is the TLS certificate renewal strategy?", "Self-signed certs expire; manual process today", "MEDIUM"],
            ["8", "Should clinical trial data be re-ingested or removed from schema?", "49.3K node shells exist but data was cleared", "LOW"],
            ["9", "Is Neo4j Enterprise Edition justified for production RBAC needs?", "CE limitations affect security posture", "LOW"],
            ["10", "What additional MCP tools (PubMed, ChEMBL, etc.) are needed for MVP?", "Tool stubs exist in code but are disabled", "MEDIUM"],
            ["11", "What is the target SLA for API response times?", "No documented performance requirements", "MEDIUM"],
            ["12", "Should the Claude Desktop MCP integration be prioritized?", "Referenced in next_steps.md as agentic coworker example", "LOW"],
        ],
        col_widths=[0.8, 5, 6, 2.5],
    )

    doc.add_paragraph("")
    doc.add_paragraph("")

    # -- Footer --
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("--- End of Document ---")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(128, 128, 128)

    doc.add_paragraph("")
    generated = doc.add_paragraph()
    generated.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = generated.add_run(
        "Generated from codebase analysis of euGENE Knowledge Graph Project\n"
        "March 2026"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(128, 128, 128)

    return doc


def convert_docx_to_pdf(docx_path, pdf_path):
    """Convert DOCX to PDF using reportlab as fallback."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from docx import Document as DocxReader

    doc_reader = DocxReader(docx_path)
    pdf_doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2.5*cm, rightMargin=2.5*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CoverTitle', fontName='Helvetica-Bold', fontSize=30,
        alignment=1, spaceAfter=10, textColor=colors.HexColor('#1F4E79')
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle', fontName='Helvetica', fontSize=14,
        alignment=1, spaceAfter=6, textColor=colors.HexColor('#595959')
    ))
    styles.add(ParagraphStyle(
        name='Heading1Custom', fontName='Helvetica-Bold', fontSize=16,
        spaceBefore=18, spaceAfter=8, textColor=colors.HexColor('#1F4E79')
    ))
    styles.add(ParagraphStyle(
        name='Heading2Custom', fontName='Helvetica-Bold', fontSize=13,
        spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#2E75B6')
    ))
    styles.add(ParagraphStyle(
        name='BodyCustom', fontName='Helvetica', fontSize=9,
        spaceBefore=3, spaceAfter=3, leading=13
    ))
    styles.add(ParagraphStyle(
        name='BulletCustom', fontName='Helvetica', fontSize=9,
        spaceBefore=2, spaceAfter=2, leftIndent=20, bulletIndent=10, leading=12
    ))
    styles.add(ParagraphStyle(
        name='CodeCustom', fontName='Courier', fontSize=7,
        spaceBefore=4, spaceAfter=4, leftIndent=15, leading=10,
        textColor=colors.HexColor('#1E1E1E')
    ))

    story = []

    for para in doc_reader.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 6))
            continue

        style_name = para.style.name if para.style else ""

        if "Heading 1" in style_name:
            story.append(Paragraph(text, styles['Heading1Custom']))
        elif "Heading 2" in style_name:
            story.append(Paragraph(text, styles['Heading2Custom']))
        elif any(run.font.size and run.font.size >= Pt(30) for run in para.runs if run.font.size):
            story.append(Spacer(1, 120))
            story.append(Paragraph(text, styles['CoverTitle']))
        elif any(run.font.size and Pt(14) <= run.font.size <= Pt(20) for run in para.runs if run.font.size):
            story.append(Paragraph(text, styles['CoverSubtitle']))
        elif "List" in style_name or "Bullet" in style_name:
            clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"&bull; {clean}", styles['BulletCustom']))
        elif any(run.font.name and "Courier" in run.font.name for run in para.runs if run.font.name):
            for line in text.split("\n"):
                clean = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(clean, styles['CodeCustom']))
        else:
            clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(clean, styles['BodyCustom']))

    # Tables from DOCX
    for table in doc_reader.tables:
        data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_text = cell.text.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                row_data.append(Paragraph(cell_text, ParagraphStyle(
                    'TableCell', fontName='Helvetica', fontSize=7, leading=9
                )))
            data.append(row_data)

        if data:
            n_cols = len(data[0])
            col_width = (A4[0] - 5*cm) / n_cols
            t = RLTable(data, colWidths=[col_width] * n_cols, repeatRows=1)
            t.setStyle(RLTableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(Spacer(1, 6))
            story.append(t)
            story.append(Spacer(1, 6))

    pdf_doc.build(story)


if __name__ == "__main__":
    print("Building DOCX document...")
    doc = build_document()
    os.makedirs(os.path.dirname(DOCX_PATH), exist_ok=True)
    doc.save(DOCX_PATH)
    print(f"DOCX saved: {DOCX_PATH}")

    print("Converting to PDF...")
    convert_docx_to_pdf(DOCX_PATH, PDF_PATH)
    print(f"PDF saved: {PDF_PATH}")

    print("\nDone! Both documents generated successfully.")
