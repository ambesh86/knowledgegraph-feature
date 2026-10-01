#!/usr/bin/env python3
"""
Generate Enterprise-Grade Project Validation Document for euGENE Knowledge Graph.
Outputs: DOCX and PDF in docs/ directory.
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
DOCX_OUT = os.path.join(BASE, "docs", "Eugene_Enterprise_Project_Validation.docx")
PDF_OUT = os.path.join(BASE, "docs", "Eugene_Enterprise_Project_Validation.pdf")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _shading(cell, color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    s = OxmlElement("w:shd")
    s.set(qn("w:fill"), color)
    s.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(s)


def tbl(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        for p in c.paragraphs:
            for r in p.runs:
                r.bold = True; r.font.size = Pt(8)
        _shading(c, "1F4E79")
        for p in c.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255,255,255)
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            c = t.rows[ri+1].cells[ci]
            c.text = str(v)
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph("")


def body(doc, text):
    p = doc.add_paragraph(text)
    for r in p.runs: r.font.size = Pt(10)


def bullet(doc, text, level=0, bold_pfx=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(1.27 + level*1.27)
    if bold_pfx:
        r = p.add_run(bold_pfx); r.bold = True; r.font.size = Pt(10)
        r2 = p.add_run(text); r2.font.size = Pt(10)
    else:
        r = p.add_run(text); r.font.size = Pt(10)


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    r = p.add_run(text)
    r.font.name = "Courier New"; r.font.size = Pt(7.5)
    r.font.color.rgb = RGBColor(30,30,30)


def h1(doc, text): doc.add_heading(text, level=1)
def h2(doc, text): doc.add_heading(text, level=2)
def h3(doc, text): doc.add_heading(text, level=3)


# ── Document Builder ─────────────────────────────────────────────────────────

def build():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(2); s.bottom_margin = Cm(2)
        s.left_margin = Cm(2.2); s.right_margin = Cm(2.2)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"; style.font.size = Pt(10)
    style.paragraph_format.space_after = Pt(3)

    # ═══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════════
    for _ in range(5): doc.add_paragraph("")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("euGENE"); r.bold = True; r.font.size = Pt(40)
    r.font.color.rgb = RGBColor(31,78,121)

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Biomedical Knowledge Graph & Agentic AI Platform")
    r.font.size = Pt(16); r.font.color.rgb = RGBColor(89,89,89)

    doc.add_paragraph("")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("_" * 70); r.font.color.rgb = RGBColor(31,78,121)

    doc.add_paragraph("")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ENTERPRISE PROJECT VALIDATION DOCUMENT"); r.bold = True; r.font.size = Pt(22)

    doc.add_paragraph("")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Version 1.0  |  March 2026\nPrepared for CSL Behring  |  Confidential")
    r.font.size = Pt(11); r.font.color.rgb = RGBColor(89,89,89)

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "Table of Contents")
    toc = [
        "1.  Project Overview & Business Purpose",
        "2.  Detailed Architecture Diagram",
        "3.  Technology Stack & Dependencies",
        "4.  Database Connectivity & Architecture",
        "5.  Component / Service Inventory",
        "6.  API Endpoint Catalog",
        "7.  MCP Tooling & Agent Skills Design",
        "8.  Authentication & Security Architecture",
        "9.  Prompt Engineering & LLM Configuration",
        "10. Workflow Orchestration",
        "11. Deployment Model & CI/CD",
        "12. Environment Configuration Matrix",
        "13. Monitoring, Observability & Health Checks",
        "14. Testing Strategy & Quality Assurance",
        "15. Data Ingestion & Knowledge Strategy",
        "16. Project Structure & Folder Hierarchy",
        "17. Development Guide & Setup Instructions",
        "18. Risks, Mitigations & Open Questions",
        "Appendix A: Complete Cypher Query Catalog",
        "Appendix B: Environment Variable Reference",
        "Appendix C: Release Notes",
    ]
    for t in toc:
        p = doc.add_paragraph(t)
        p.paragraph_format.space_before = Pt(1); p.paragraph_format.space_after = Pt(1)
        for r in p.runs: r.font.size = Pt(11)
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 1. PROJECT OVERVIEW & BUSINESS PURPOSE
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "1. Project Overview & Business Purpose")

    h2(doc, "1.1 What the System Does")
    body(doc,
        "euGENE is a biomedical knowledge graph and agentic AI platform developed for "
        "CSL Behring. It enables competitive intelligence across the pharmaceutical "
        "landscape by integrating data from DrugBank, ClinicalTrials.gov, USPTO, PubMed, "
        "and internal CSL sources into a Neo4j graph database. Users can explore drug "
        "pipelines, disease-gene relationships, patent landscapes, and organizational "
        "partnerships through both a structured REST API and a conversational AI chat "
        "interface powered by LLM agents (Anthropic Claude and OpenAI GPT).")

    h2(doc, "1.2 Target Audience & User Personas")
    tbl(doc,
        ["Persona", "Use Case", "Interface"],
        [
            ["R&D Scientists", "Explore drug-disease-gene relationships, find competitive drugs", "Chat UI, API"],
            ["Patent Analysts", "Search patent landscapes, find patent-drug linkages", "API, Chat UI"],
            ["Business Development", "Assess organizational assets, competitive threat analysis", "Chat UI"],
            ["Data Engineers", "Ingest new datasets, manage graph schema, run analytics", "CLI, API"],
            ["DevOps / SRE", "Deploy, monitor, scale the platform", "Terraform, CI/CD, CloudWatch"],
        ],
        widths=[3.5, 6, 3])

    h2(doc, "1.3 Key Business Capabilities")
    bullet(doc, "Drug-Disease Intelligence: Explore indications, contraindications, off-label uses, drug aliases")
    bullet(doc, "Gene-Protein Analysis: Map drug-protein targets, disease-protein associations, pathway relationships")
    bullet(doc, "Patent Landscape: Search patents by drug, clinical trial, or gene/protein with pagination")
    bullet(doc, "Organizational Assets: Discover company drug pipelines, clinical trial sponsorships, partnerships")
    bullet(doc, "PubMed Integration: Link published research to drugs, diseases, and genes")
    bullet(doc, "Agentic AI Querying: Natural language questions answered via ReAct agent with 12 graph tools")
    bullet(doc, "Graph Analytics: Node similarity (cosine), community detection (Leiden), GraphSAGE embeddings")

    h2(doc, "1.4 Quantitative Summary")
    tbl(doc,
        ["Metric", "Value"],
        [
            ["Graph Nodes", "129,375"],
            ["Graph Relationships", "4,050,249"],
            ["Graph Properties", "4,567,749"],
            ["Node Types (Labels)", "36 distinct types"],
            ["Relationship Types", "27 distinct types"],
            ["Core API Endpoints", "38"],
            ["MCP Agent Tools", "12"],
            ["Microservices", "5 (Neo4j, Core API, MCP, Agent WS, Agent UI)"],
            ["LLM Providers Supported", "2 (Anthropic Claude, OpenAI GPT)"],
            ["AWS Environments", "2 (difflabs us-east-1, AIA eu-central-1)"],
            ["Authentication Layers", "3 (Entra ID, Eugene JWT, Agent Allowlist)"],
        ],
        widths=[6, 10])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 2. ARCHITECTURE DIAGRAM
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "2. Detailed Architecture Diagram")

    h2(doc, "2.1 System Architecture (Five-Tier)")
    code(doc,
        "+==================================================================================+\n"
        "||                         PRESENTATION LAYER (Tier 5)                             ||\n"
        "+==================================================================================+\n"
        "||                                                                                 ||\n"
        "||  +----------------------------------+  +------------------------------------+   ||\n"
        "||  | eugene-agent-ui (Streamlit)      |  | Neo4j Browser                      |   ||\n"
        "||  | Port: 18501 (local) / 8501       |  | Port: 17474 (local) / 7474         |   ||\n"
        "||  |                                  |  |                                    |   ||\n"
        "||  | - Chat message interface         |  | - Graph visualization              |   ||\n"
        "||  | - Suggestion pills               |  | - Cypher query console             |   ||\n"
        "||  | - Tool selection sidebar         |  | - Schema browser                   |   ||\n"
        "||  | - OAuth token input              |  |                                    |   ||\n"
        "||  | - Streaming response display     |  |                                    |   ||\n"
        "||  +----------------------------------+  +------------------------------------+   ||\n"
        "||                    |                                                            ||\n"
        "+==================================================================================+\n"
        "                      | HTTP POST /agent/api/query/stream\n"
        "                      | Authorization: Bearer <EUGENE_JWT>\n"
        "                      v\n"
        "+==================================================================================+\n"
        "||                      AGENT ORCHESTRATION LAYER (Tier 4)                        ||\n"
        "+==================================================================================+\n"
        "||                                                                                 ||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||  | eugene-agent-ws (FastAPI + Strands Framework)                                |||\n"
        "||  | Port: 18001 (local) / 8000                                                  |||\n"
        "||  |                                                                             |||\n"
        "||  | +---------------------------+  +---------------------------+                |||\n"
        "||  | | LLM Factory               |  | Agent Engine             |                |||\n"
        "||  | | - Anthropic Claude Sonnet  |  | - ReAct Pattern          |                |||\n"
        "||  | | - OpenAI GPT-4.1-mini      |  | - 10-msg sliding window  |                |||\n"
        "||  | | - Auto-detection           |  | - FileSessionManager     |                |||\n"
        "||  | +---------------------------+  +---------------------------+                |||\n"
        "||  |                                                                             |||\n"
        "||  | Local Tools: calculator, current_time, python_repl, http_request            |||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||                    |                                                            ||\n"
        "+==================================================================================+\n"
        "                      | MCP HTTP Streaming + JWT\n"
        "                      v\n"
        "+==================================================================================+\n"
        "||                        MCP TOOL SERVER LAYER (Tier 3)                           ||\n"
        "+==================================================================================+\n"
        "||                                                                                 ||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||  | eugene-mcp (FastMCP + JWT Verifier)                                         |||\n"
        "||  | Port: 18443 (local) / 8000                                                  |||\n"
        "||  |                                                                             |||\n"
        "||  | +--------------------+ +--------------------+ +--------------------+        |||\n"
        "||  | | Identity Tools (1) | | Fetch Tools    (2) | | Node Tools     (2) |        |||\n"
        "||  | | - fetch_identity   | | - fetch_by_label   | | - lookup_node      |        |||\n"
        "||  | |                    | | - fetch_similar     | | - fetch_details    |        |||\n"
        "||  | +--------------------+ +--------------------+ +--------------------+        |||\n"
        "||  | +--------------------+ +--------------------+ +--------------------+        |||\n"
        "||  | | Drug Tools     (1) | | Fact Tools     (1) | | Graph Tools    (3) |        |||\n"
        "||  | | - fetch_aliases    | | - fetch_facts      | | - relationships    |        |||\n"
        "||  | |                    | |                    | | - paths, reachable  |        |||\n"
        "||  | +--------------------+ +--------------------+ +--------------------+        |||\n"
        "||  | +--------------------+                                                      |||\n"
        "||  | | Org Tools      (2) |                                                      |||\n"
        "||  | | - find_org_names   |                                                      |||\n"
        "||  | | - find_org_assets  |                                                      |||\n"
        "||  | +--------------------+                                                      |||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||                    |                                                            ||\n"
        "+==================================================================================+\n"
        "                      | HTTP REST + JWT\n"
        "                      v\n"
        "+==================================================================================+\n"
        "||                          CORE API LAYER (Tier 2)                                ||\n"
        "+==================================================================================+\n"
        "||                                                                                 ||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||  | eugene_ws (FastAPI + Uvicorn)                                                |||\n"
        "||  | Port: 18000 (local) / 8000                                                  |||\n"
        "||  |                                                                             |||\n"
        "||  | Routers (20):                                                               |||\n"
        "||  | auth | health | stats | labels | count | node_lookup | node_details         |||\n"
        "||  | n_hop | search_path | facet | similarity | drug_aliases                     |||\n"
        "||  | patent_search | patent_count | pubmed_search | pubmed_count                 |||\n"
        "||  | facts | organization_search | root | release_notes                          |||\n"
        "||  |                                                                             |||\n"
        "||  | Architecture: DDD + Hexagonal (model/provider/mapper/adapter/conf)           |||\n"
        "||  +-----------------------------------------------------------------------------+||\n"
        "||                    |                                                            ||\n"
        "+==================================================================================+\n"
        "                      | Bolt Protocol (neo4j:// or bolt+ssc://)\n"
        "                      v\n"
        "+==================================================================================+\n"
        "||                         DATA PERSISTENCE LAYER (Tier 1)                        ||\n"
        "+==================================================================================+\n"
        "||                                                                                 ||\n"
        "||  +--------------------------------------+  +--------------------------------+   ||\n"
        "||  | Neo4j 5.26.9 Community Edition       |  | Milvus (Vector DB)             |   ||\n"
        "||  | Port: 17687 (Bolt) / 17474 (HTTP)    |  | milvus-lite (embedded)         |   ||\n"
        "||  |                                      |  |                                |   ||\n"
        "||  | Plugins:                             |  | Model: minishlab/potion-base-8M|   ||\n"
        "||  |   APOC 5.25.0 Extended               |  | Purpose: Semantic search       |   ||\n"
        "||  |   Graph Data Science (GDS) 2.13.2+   |  |   embeddings for drugs,        |   ||\n"
        "||  |                                      |  |   diseases, documents           |   ||\n"
        "||  | Data:                                |  |                                |   ||\n"
        "||  |   129,375 nodes                      |  |                                |   ||\n"
        "||  |   4,050,249 relationships            |  |                                |   ||\n"
        "||  |   4,567,749 properties               |  |                                |   ||\n"
        "||  +--------------------------------------+  +--------------------------------+   ||\n"
        "||                                                                                 ||\n"
        "+==================================================================================+\n"
    )

    h2(doc, "2.2 Deployment Environments")
    code(doc,
        "DEPLOYMENT TARGETS:\n"
        "+---------------------+  +---------------------+  +---------------------+\n"
        "| LOCAL DEVELOPMENT   |  | DIFFLABS (Dev)      |  | AIA (Staging/Prod)  |\n"
        "|                     |  |                     |  |                     |\n"
        "| Docker Compose      |  | AWS us-east-1       |  | AWS eu-central-1    |\n"
        "| 5 containers        |  | ECS Fargate         |  | ECS Fargate         |\n"
        "| Ports: 17xxx/18xxx  |  | ALB + Target Groups |  | ALB + Target Groups |\n"
        "| Neo4j: local volume |  | EC2 r7i.xlarge      |  | EC2 r7i.xlarge      |\n"
        "| Auth: bypass mode   |  | Acct: 087084717211  |  | Acct: 010928221940  |\n"
        "+---------------------+  +---------------------+  +---------------------+\n"
        "\n"
        "DATA FLOW:\n"
        "User ---> Streamlit UI ---> Agent WS ---> MCP Server ---> Core API ---> Neo4j\n"
        "  |         (8501)          (8001)         (8443)          (8000)       (7687)\n"
        "  |                                                                      |\n"
        "  +--- JWT Token forwarded through entire chain (HS256) ----------------+\n"
    )

    h2(doc, "2.3 Authentication Flow")
    code(doc,
        "PRODUCTION AUTH FLOW:\n"
        "+--------+     +----------+     +---------------+     +-----------+\n"
        "| User   | --> | /login   | --> | Microsoft     | --> | Entra ID  |\n"
        "|        |     | endpoint |     | Entra ID      |     | ID Token  |\n"
        "+--------+     +----------+     | (OAuth 2.0)   |     | (RS256)   |\n"
        "                                +---------------+     +-----------+\n"
        "                                                            |\n"
        "                                       JWKS validation      |\n"
        "                                       (8h cached keys)     v\n"
        "                                                      +-----------+\n"
        "                                                      | Eugene    |\n"
        "                                                      | JWT       |\n"
        "                                                      | (HS256)   |\n"
        "                                                      | 24h TTL   |\n"
        "                                                      +-----------+\n"
        "                                                            |\n"
        "         Token forwarded: UI -> Agent WS -> MCP -> API     |\n"
        "         Each service validates independently               v\n"
        "\n"
        "LOCAL DEV AUTH FLOW:\n"
        "+--------+     +----------+     +-----------+\n"
        "| User   | --> | /login   | --> | Dev Token |\n"
        "|        |     | (local)  |     | Immediate |\n"
        "+--------+     +----------+     | HS256     |\n"
        "                                +-----------+\n"
        "  User: eugene.test@cslhering.com\n"
        "  Roles: [user.public.read]\n"
    )

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 3. TECHNOLOGY STACK
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "3. Technology Stack & Dependencies")

    h2(doc, "3.1 Core Technology Matrix")
    tbl(doc,
        ["Layer", "Technology", "Version", "Purpose"],
        [
            ["Runtime", "Python", "3.12-3.13", "Application runtime"],
            ["API Framework", "FastAPI", "Latest (via pip)", "REST API with auto OpenAPI docs"],
            ["ASGI Server", "Uvicorn", "Latest", "Production HTTP server"],
            ["Graph Database", "Neo4j Community", "5.26.9", "Knowledge graph storage"],
            ["Neo4j Driver", "neo4j (Python)", "5.25.0", "Database connectivity"],
            ["Graph Plugins", "APOC Extended", "5.25.0", "Utility procedures (path, meta, merge)"],
            ["Graph Plugins", "Graph Data Science", "2.13.2+", "ML algorithms (similarity, embeddings)"],
            ["Vector DB", "Milvus Lite", "2.4.10", "Semantic search embeddings"],
            ["MCP Framework", "FastMCP", "3.0.0b1", "Model Context Protocol server"],
            ["Agent Framework", "Strands Agents", "1.21.0", "LLM agent orchestration"],
            ["UI Framework", "Streamlit", "1.52.2", "Chat web interface"],
            ["LLM (Anthropic)", "Claude Sonnet 4", "claude-sonnet-4-20250514", "Primary LLM provider"],
            ["LLM (OpenAI)", "GPT-4.1-mini", "gpt-4.1-mini", "Secondary LLM provider"],
            ["Embeddings", "potion-base-8M", "minishlab/potion-base-8M", "Semantic vector embeddings"],
            ["Auth (Enterprise)", "MSAL", "Latest", "Microsoft Entra ID OAuth 2.0"],
            ["Auth (JWT)", "PyJWT / python-jose", "Latest", "HS256 token signing/validation"],
            ["IaC", "Terraform", ">= 1.0.0", "AWS infrastructure provisioning"],
            ["CI/CD", "GitLab CI", "Cloud hosted", "Build, scan, deploy pipelines"],
            ["Containers", "Docker / Docker Compose", "Latest", "Service containerization"],
            ["Cloud", "AWS (ECS, EC2, ECR, S3, ALB)", "Latest", "Production hosting"],
            ["Data Processing", "Pandas", "2.2.3", "DataFrame operations"],
            ["ML/NLP", "Transformers", "4.46.2", "NLP model loading"],
            ["ML/NLP", "Sentence-Transformers", "3.3.0", "Embedding models"],
            ["ML/NLP", "PyTorch (CPU)", "Latest", "ML framework (CPU-only)"],
        ],
        widths=[2.5, 3.5, 3.5, 6.5])

    h2(doc, "3.2 Key Python Dependencies (requirements.txt)")
    tbl(doc,
        ["Category", "Packages"],
        [
            ["Web Framework", "fastapi, uvicorn, starlette, pydantic==2.8.2, pydantic-settings==2.5.2"],
            ["Database", "neo4j==5.25.0, pymilvus==2.4.3, milvus-lite==2.4.10, kuzu==0.6.0"],
            ["LLM / LangChain", "langchain==0.3.1, langchain-aws==0.2.1, langchain-openai==0.2.1, openai==1.42.0"],
            ["ML / NLP", "transformers==4.46.2, sentence-transformers==3.3.0, model2vec==0.3.2, torch (CPU)"],
            ["Data Science", "pandas==2.2.3, numpy==1.26.4, scikit-learn, scipy, networkx, graspologic"],
            ["Auth", "msal, PyJWT, python-jose, cryptography"],
            ["AWS", "boto3==1.34.162, botocore==1.34.162"],
            ["HTTP", "httpx==0.27.0, requests==2.32.3"],
            ["Utilities", "python-dotenv==1.0.1, orjson==3.10.7, regex==2024.7.24, click, Rich"],
            ["Dev Tools", "black, pytest, pytest-cov, pytest-xdist, ruff, mypy"],
        ],
        widths=[3, 13])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 4. DATABASE CONNECTIVITY & ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "4. Database Connectivity & Architecture")

    h2(doc, "4.1 Connection Configuration")
    tbl(doc,
        ["Environment", "URI", "TLS", "Auth"],
        [
            ["Local (Docker)", "bolt://neo4j:7687 (internal)\nbolt://localhost:17687 (host)", "Disabled", "neo4j / eugene_local_2024"],
            ["difflabs (Dev)", "bolt+ssc://10.88.203.244:7687", "Self-signed (EC P-384)", "neo4j / <secret>"],
            ["AIA (Prod)", "neo4j+ssc://<ec2-ip>:7687", "Self-signed (EC P-384)", "neo4j / <AWS Secrets>"],
        ],
        widths=[3, 6, 3, 4])

    h2(doc, "4.2 Neo4j Server Configuration (Production)")
    tbl(doc,
        ["Setting", "Value", "Purpose"],
        [
            ["server.memory.heap.initial_size", "16384m", "JVM heap (16 GB)"],
            ["server.memory.heap.max_size", "16384m", "JVM max heap (16 GB)"],
            ["server.memory.pagecache.size", "512M", "Page cache for disk reads"],
            ["server.bolt.tls_level", "REQUIRED", "Enforce TLS on Bolt connections"],
            ["server.default_listen_address", "0.0.0.0", "Accept connections from any host"],
            ["dbms.security.procedures.unrestricted", "apoc.*, gds.*", "Allow all APOC and GDS procedures"],
            ["dbms.cypher.lenient_create_relationship", "true", "Allow flexible relationship creation"],
            ["db.tx_log.rotation.retention_policy", "2 days 2G", "Transaction log retention"],
            ["JVM Additional", "--add-modules=jdk.incubator.vector", "Enable Java vector API"],
        ],
        widths=[5, 4, 7])

    h2(doc, "4.3 Node Label Inventory")
    tbl(doc,
        ["ID", "Label", "Count", "Source", "Key Properties"],
        [
            ["8", "drug", "4,600", "DrugBank", "node_id, node_name, drug_bank_id, description"],
            ["7", "disease", "17,100", "Disease Ontology", "node_id, node_name, MONDO_ID, MONDO_NAME"],
            ["12", "gene_protein", "27,700", "Protein DBs", "node_id, node_name, annotation"],
            ["4", "ClinicalTrial", "49,300", "ClinicalTrials.gov", "node_id, node_name, nct_id"],
            ["32", "Organization", "26,100", "Company/Sponsor", "org_id, organization_canonical_name, organization_type"],
            ["1", "anatomy", "Various", "Anatomical Ontology", "node_id, node_name"],
            ["2", "biological_process", "Various", "Gene Ontology", "node_id, node_name"],
            ["15", "pathway", "Various", "Pathway DBs", "node_id, node_name"],
            ["9", "effect_phenotype", "Various", "Phenotype data", "node_id, node_name"],
            ["10", "exposure", "Various", "Environmental data", "node_id, node_name"],
            ["14", "molecular_function", "Various", "Gene Ontology", "node_id, node_name"],
            ["16", "patent", "Pending", "USPTO", "node_id, patent_id"],
            ["31", "Patent_Application", "Pending", "USPTO", "patent_id, node_name"],
            ["30", "Approved_Patent", "Pending", "USPTO", "patent_id, node_name"],
            ["400", "pubmed_document", "Pending", "PubMed", "pmid, title, doi"],
            ["300", "csl_tpp", "Partial", "CSL Internal", "node_id, therapeutic_area"],
            ["21", "drug_product", "Various", "DrugBank", "node_id, node_name"],
            ["22", "drug_synonym", "Various", "DrugBank", "node_id, node_name"],
            ["100", "summary (GraphRAG)", "Various", "Generated", "node_id, content"],
            ["200", "uspto_application", "Pending", "USPTO", "node_id, app_number"],
        ],
        widths=[0.8, 3, 1.5, 2.8, 7])

    h2(doc, "4.4 Relationship Type Inventory")
    tbl(doc,
        ["ID", "Relationship", "Source -> Target", "Description"],
        [
            ["15", "indication", "Drug -> Disease", "Drug is indicated for disease"],
            ["6", "contraindication", "Drug -> Disease", "Drug is contraindicated"],
            ["1", "off-label use", "Drug -> Disease", "Drug used off-label"],
            ["13", "drug_protein", "Drug -> Gene/Protein", "Drug targets protein"],
            ["10", "disease_protein", "Disease -> Gene/Protein", "Disease associated with protein"],
            ["12", "drug_effect", "Drug -> Effect/Phenotype", "Drug has pharmacological effect"],
            ["11", "drug_drug", "Drug -> Drug", "Drug-drug interactions"],
            ["7", "disease_disease", "Disease -> Disease", "Disease comorbidities"],
            ["19", "protein_protein", "Protein -> Protein", "Protein interactions"],
            ["18", "pathway_protein", "Pathway -> Protein", "Protein in pathway"],
            ["3", "anatomy_protein_present", "Anatomy -> Protein", "Protein present in tissue"],
            ["2", "anatomy_protein_absent", "Anatomy -> Protein", "Protein absent in tissue"],
            ["9", "disease_phenotype_positive", "Disease -> Phenotype", "Disease manifests phenotype"],
            ["8", "disease_phenotype_negative", "Disease -> Phenotype", "Disease lacks phenotype"],
            ["14", "exposure_disease", "Exposure -> Disease", "Environmental exposure link"],
            ["20", "has_drug_alias", "Drug -> Drug Synonym", "Drug name synonym"],
            ["21", "disclosed_in", "Drug -> Patent", "Drug disclosed in patent"],
            ["22", "supports_patent_application", "Trial -> Patent", "Trial supports patent"],
            ["23", "patent_app_target", "Gene -> Patent", "Gene targeted in patent"],
            ["24", "featured_in", "Drug -> Research", "Drug featured in publication"],
            ["25", "analyzed_in", "Gene -> Research", "Gene analyzed in publication"],
            ["26", "evaluated_in", "Trial -> Research", "Trial evaluated in pub"],
            ["200", "has_publication", "Entity -> PubMed", "Entity linked to PMID"],
        ],
        widths=[0.8, 4, 3.5, 7.5])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 5. COMPONENT / SERVICE INVENTORY
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "5. Component / Service Inventory")

    h2(doc, "5.1 Service: neo4j (Data Tier)")
    tbl(doc, ["Property", "Value"],
        [
            ["Image", "neo4j:5.26.9-community-bullseye"],
            ["Container Name", "eugene-neo4j"],
            ["Ports", "17474:7474 (HTTP Browser), 17687:7687 (Bolt Driver)"],
            ["Plugins", "APOC 5.25.0 Extended, GDS 2.13.2+"],
            ["Volumes", "eugene_neo4j_data:/data, eugene_neo4j_logs:/logs"],
            ["Health Check", "wget --spider http://localhost:7474 (10s interval, 30s startup)"],
            ["Memory", "512M pagecache, 512m-1024m heap (local) / 16GB heap (prod)"],
        ], widths=[3.5, 12.5])

    h2(doc, "5.2 Service: eugene_ws (Core API Tier)")
    tbl(doc, ["Property", "Value"],
        [
            ["Framework", "FastAPI + Uvicorn"],
            ["Container Name", "eugene-ws"],
            ["Port", "18000:8000"],
            ["Source", "src/eugene_ws.py"],
            ["Routers", "20 (auth, health, stats, labels, count, node_lookup, node_details, n_hop, search_path, facet, similarity, drug_aliases, patent_search, patent_count, pubmed_search, pubmed_count, facts, organization_search, root, release_notes)"],
            ["Architecture", "DDD + Hexagonal (model/provider/mapper/adapter/conf per domain)"],
            ["Dependencies", "neo4j service (healthy)"],
            ["Health Check", "urllib http://localhost:8000/health (10s interval, 15s startup)"],
            ["Special", "CPU-only PyTorch, HuggingFace model cache"],
        ], widths=[3, 13])

    h2(doc, "5.3 Service: eugene_mcp (MCP Tool Tier)")
    tbl(doc, ["Property", "Value"],
        [
            ["Framework", "FastMCP 3.0.0b1 + JWT Verifier"],
            ["Container Name", "eugene-mcp"],
            ["Port", "18443:8000"],
            ["Source", "agents/eugene-mcp/src/eugene_mcp.py"],
            ["Tools", "12 tools in 7 classes (Identity, Fetch, Node, Drug, Fact, Graph, Organization)"],
            ["Auth", "HS256 JWT verification middleware on every tool call"],
            ["Transport", "Stateless HTTP streaming"],
            ["Dependencies", "eugene_ws service (healthy)"],
            ["HTTP Client", "httpx, 30s timeout, verify=False (internal network)"],
        ], widths=[3, 13])

    h2(doc, "5.4 Service: eugene_agent_ws (Agent Tier)")
    tbl(doc, ["Property", "Value"],
        [
            ["Framework", "FastAPI + Strands Agents 1.21.0"],
            ["Container Name", "eugene-agent-ws"],
            ["Port", "18001:8000"],
            ["Source", "agents/eugene-agent-ws/src/eugene_chat_ws.py"],
            ["root_path", "/agent/api"],
            ["Endpoints", "POST /query (sync), POST /query/stream (SSE)"],
            ["LLM Support", "Anthropic Claude (claude-sonnet-4-20250514), OpenAI GPT (gpt-4.1-mini)"],
            ["Agent Pattern", "ReAct (Reason, Act, Observe)"],
            ["Conversation", "SlidingWindowConversationManager(window_size=10, per_turn=2)"],
            ["Session", "FileSessionManager (local), future: S3SessionManager"],
            ["Auth", "JWT validation + user allowlist (EUGENE_AGENT_ALLOWLIST)"],
            ["Local Tools", "calculator, current_time, python_repl, http_request (optional)"],
        ], widths=[3, 13])

    h2(doc, "5.5 Service: eugene_agent_ui (Frontend Tier)")
    tbl(doc, ["Property", "Value"],
        [
            ["Framework", "Streamlit 1.52.2"],
            ["Container Name", "eugene-agent-ui"],
            ["Port", "18501:8501"],
            ["Source", "agents/eugene-agent-ui/src/eugene_agent_ui.py"],
            ["Layout", "Wide, sidebar expanded"],
            ["Features", "Chat history, streaming responses, suggestion pills, tool selection, OAuth token input"],
            ["Dependencies", "eugene_agent_ws service"],
            ["API Endpoint", "EUGENE_AGENT_API_URL or http://localhost:8000/agent/api/query"],
        ], widths=[3, 13])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 6. API ENDPOINT CATALOG
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "6. API Endpoint Catalog")

    h2(doc, "6.1 Core API Endpoints (eugene_ws) - 38 Total")
    tbl(doc,
        ["Method", "Path", "Auth", "Description"],
        [
            ["GET", "/login", "No", "Initiate OAuth / issue local dev token"],
            ["GET", "/auth/callback", "No", "OAuth redirect callback from Entra ID"],
            ["GET", "/auth/whoami", "Yes", "Return authenticated user claims"],
            ["GET", "/", "Yes", "Welcome message with user info"],
            ["GET", "/health", "No", "Health check (returns {status: OK})"],
            ["GET", "/releases", "No", "Release notes history (v1 - v2.2)"],
            ["GET", "/stats", "Yes", "Database statistics (node/rel counts)"],
            ["GET", "/count/{label}", "Yes", "Count nodes by label type"],
            ["GET", "/labels/{label}", "Yes", "List nodes by label (paginated, max 50)"],
            ["GET", "/node/find/{node_value}", "Yes", "Find node ID by name (fuzzy optional)"],
            ["POST", "/node/details", "Yes", "Get details for list of node IDs (max 50)"],
            ["GET", "/graph/relationship/start/{start_id}", "Yes", "N-hop subgraph from node (n_hop: 1-2)"],
            ["GET", "/graph/path/start/{start_id}/end/{end_id}", "Yes", "Shortest path between nodes (n_hop: 1-4)"],
            ["GET", "/graph/reachability/start/{start_id}/end/{end_id}", "Yes", "Check reachability (n_hop: 1-4)"],
            ["GET", "/graph/facts/start/{start_id}", "Yes", "English-language facts (paginated)"],
            ["POST", "/facet/{label}", "Yes", "Faceted search by label and values"],
            ["POST", "/similarity/{label}", "Yes", "Cosine similarity via GDS (drug/disease)"],
            ["GET", "/drugs/aliases/{drug_name}", "Yes", "Drug aliases by name (fuzzy optional)"],
            ["GET", "/drugs/aliases/id/{drug_id}", "Yes", "Drug aliases by DrugBank ID"],
            ["GET", "/patents/drugs", "Yes", "Patents by drug_id (paginated, max 100)"],
            ["GET", "/patents/clinicaltrials", "Yes", "Patents by nct_id (paginated)"],
            ["GET", "/patents/geneproteins", "Yes", "Patents by gene_protein name (paginated)"],
            ["GET", "/count/patents/drugs", "Yes", "Count patents by drug_id"],
            ["GET", "/count/patents/clinicaltrials", "Yes", "Count patents by nct_id"],
            ["GET", "/count/patents/geneproteins", "Yes", "Count patents by gene_protein"],
            ["GET", "/pmids/drugs", "Yes", "PubMed articles by drug_id (paginated)"],
            ["GET", "/pmids/clinicaltrials", "Yes", "PubMed articles by nct_id (paginated)"],
            ["GET", "/pmids/geneproteins", "Yes", "PubMed articles by gene_protein (paginated)"],
            ["GET", "/count/pmids/drugs", "Yes", "Count PubMed articles by drug_id"],
            ["GET", "/count/pmids/clinicaltrials", "Yes", "Count PubMed by nct_id"],
            ["GET", "/count/pmids/geneproteins", "Yes", "Count PubMed by gene_protein"],
            ["GET", "/organizations/{name}", "Yes", "Search organizations (wildcard *, ?, max 500)"],
            ["GET", "/organizations/assets/{org_id}", "Yes", "Organization assets (drugs, trials, max 500)"],
            ["GET", "/list/organization/aliases/{name}", "Yes", "DEPRECATED: Org alias search"],
        ],
        widths=[1.5, 5.5, 1, 8])

    h2(doc, "6.2 Agent API Endpoints (eugene_agent_ws)")
    tbl(doc,
        ["Method", "Path", "Auth", "Description"],
        [
            ["GET", "/agent/api/health", "No", "Agent health check"],
            ["GET", "/agent/api/", "No", "Agent welcome"],
            ["GET", "/agent/api/auth/whoami", "Yes", "Agent user identity"],
            ["POST", "/agent/api/query", "Yes", "Synchronous agent query"],
            ["POST", "/agent/api/query/stream", "Yes", "Streaming agent query (SSE)"],
        ],
        widths=[1.5, 5, 1, 8.5])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 7. MCP TOOLING & AGENT SKILLS
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "7. MCP Tooling & Agent Skills Design")

    h2(doc, "7.1 MCP Tool Inventory (12 Tools)")
    tbl(doc,
        ["#", "Tool", "Class", "API Endpoint Called", "Purpose"],
        [
            ["1", "fetch_identity()", "EugeneIdentityTools", "GET /auth/whoami", "Validate user identity"],
            ["2", "fetch_by_label(label, page, page_size)", "EugeneFetchTools", "GET /labels/{label}", "Browse drugs/diseases"],
            ["3", "fetch_similar(label, values)", "EugeneFetchTools", "POST /similarity/{label}", "Find similar entities"],
            ["4", "lookup_node_by_value(value, fuzzy)", "EugeneNodeTools", "GET /node/find/{value}", "Resolve name to ID"],
            ["5", "fetch_node_details(ids)", "EugeneNodeTools", "POST /node/details", "Get node attributes"],
            ["6", "fetch_drug_aliases(drug_name)", "EugeneDrugTools", "GET /drugs/aliases/{name}", "Drug synonym lookup"],
            ["7", "fetch_facts(node_id)", "EugeneFactTools", "GET /graph/facts/start/{id}", "Paginated fact extraction (50 pages max)"],
            ["8", "fetch_node_relationships(node_id, n_hop)", "EugeneGraphTools", "GET /graph/relationship/start/{id}", "N-hop traversal"],
            ["9", "fetch_paths(start, end, n_hop)", "EugeneGraphTools", "GET /graph/path/start/{s}/end/{e}", "Path discovery"],
            ["10", "has_reachable_path(start, end, n_hop)", "EugeneGraphTools", "GET /graph/reachability/start/{s}/end/{e}", "Reachability check"],
            ["11", "find_organization_names(pattern)", "EugeneOrganizationTools", "GET /organizations/{pattern}", "Org wildcard search (10 pages)"],
            ["12", "find_organization_assets(org_id)", "EugeneOrganizationTools", "GET /organizations/assets/{id}", "Org asset discovery (10 pages)"],
        ],
        widths=[0.6, 4, 3, 4, 4.4])

    h2(doc, "7.2 Future Tools (Planned, Currently Disabled)")
    tbl(doc,
        ["Tool Category", "Purpose", "Status"],
        [
            ["PUBMED", "Direct PubMed article search via API", "Code stub exists (ToolRequestEnum.PUBMED)"],
            ["CLINICAL_TRIALS", "ClinicalTrials.gov API integration", "Code stub exists"],
            ["CHEMBL", "ChEMBL chemical database queries", "Code stub exists"],
            ["BIORXIV", "BioRxiv preprint search", "Code stub exists"],
        ],
        widths=[3, 7, 6])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 8. SECURITY & ACCESS CONTROL
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "8. Authentication & Security Architecture")

    h2(doc, "8.1 Three-Layer Authentication")
    tbl(doc,
        ["Layer", "Mechanism", "Algorithm", "Provider", "Details"],
        [
            ["1. Enterprise SSO", "Microsoft Entra ID", "RS256 (asymmetric)", "Microsoft", "OIDC flow, JWKS validation with 8h cache, corporate identity"],
            ["2. Platform Token", "Eugene JWT", "HS256 (symmetric)", "Eugene Backend", "24h TTL, claims: tid/sub/upn/roles, shared secret signing"],
            ["3. Agent Allowlist", "UPN Allowlist", "N/A", "Agent WS", "Pipe-separated list of authorized user emails"],
        ],
        widths=[2.5, 3, 2.5, 2.5, 5.5])

    h2(doc, "8.2 JWT Token Structure")
    code(doc,
        "Eugene JWT Claims:\n"
        "{\n"
        '  "tid": "f8645748-68c6-4eec-bd61-c71341a6ed7d",    // Tenant ID\n'
        '  "sub": "<user-oid>",                                // Subject (user OID)\n'
        '  "upn": "user@cslbehring.com",                      // User Principal Name\n'
        '  "roles": ["user.public.read"],                      // Assigned roles\n'
        '  "iat": 1711500000,                                  // Issued at\n'
        '  "exp": 1711586400,                                  // Expires (24h later)\n'
        '  "iss": "https://eugene.ai.cslg1.cslg.net/<tid>",   // Issuer\n'
        '  "aud": "api://eugene/<client_id>"                   // Audience\n'
        "}\n"
    )

    h2(doc, "8.3 Role-Based Access Control")
    tbl(doc,
        ["Role", "Scope", "Assigned To", "Status"],
        [
            ["user.public.read", "Read public biomedical data", "All authenticated users (default)", "Active"],
            ["user.confidential.read", "Read proprietary CSL data", "Named CSL users only", "Defined, not yet enforced at query level"],
        ],
        widths=[3.5, 4.5, 4.5, 3.5])

    h2(doc, "8.4 Security Posture Assessment")
    tbl(doc,
        ["Control", "Severity", "Status", "Detail"],
        [
            ["Cypher Injection", "HIGH", "OPEN", "one-hop adapter uses string formatting instead of parameterized queries"],
            ["API Rate Limiting", "MEDIUM", "OPEN", "No rate limiting middleware on any endpoint"],
            ["SAST/DAST Scanning", "MEDIUM", "OPEN", "Checkov defined but SAST/DAST commented out in CI pipeline"],
            ["TLS Certificates", "LOW", "ACTIVE", "Self-signed certs on Neo4j and ALB; manual renewal"],
            ["SSL Verification", "MEDIUM", "BY DESIGN", "MCP and Agent HTTP clients use verify=False (internal network)"],
            ["Static Role Mapping", "LOW", "OPEN", "Roles hard-coded in roles.py; should migrate to DB or IdP"],
            ["Input Validation", "LOW", "ACTIVE", "Pydantic models + regex sanitization on org search"],
            ["Secrets Management", "LOW", "ACTIVE", "AWS Secrets Manager for production; .env for local dev"],
        ],
        widths=[3, 2, 2, 9])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 9. PROMPT DESIGN
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "9. Prompt Engineering & LLM Configuration")

    h2(doc, "9.1 Agent System Prompt")
    code(doc,
        'SYSTEM_PROMPT = """\n'
        'You are an agent tasked with helping investigate biomedical\n'
        'companies to assess competitive threat and collaboration\n'
        'opportunities. In our case assets here mean any drug, disease,\n'
        'patents, clinical trials, intellectual property, or financial\n'
        'deals the company may have involvement. As an agent follow the\n'
        'Reason, Act, Observe (ReAct) pattern. You are an agent that\n'
        'may call tools to retrieve data.\n'
        '"""\n'
    )

    h2(doc, "9.2 LLM Provider Configuration")
    tbl(doc,
        ["Provider", "Default Model", "Alternatives", "Max Tokens", "Temperature", "Top-P"],
        [
            ["Anthropic", "claude-sonnet-4-20250514", "claude-haiku-4-5-20251001, claude-opus-4-20250514", "16,384", "0.7", "N/A"],
            ["OpenAI", "gpt-4.1-mini", "gpt-4.1, gpt-4o, gpt-4o-mini, gpt-3.5-turbo", "4,096", "0.7", "1.0"],
        ],
        widths=[2.2, 3.5, 4.5, 1.8, 1.8, 1.2])

    body(doc,
        "Provider auto-detection priority: 1) LLM_PROVIDER env var, 2) ANTHROPIC_API_KEY present -> Anthropic, "
        "3) OPENAI_API_KEY present -> OpenAI. OpenAI client uses max_retries=3, timeout=60s."
    )

    h2(doc, "9.3 Conversation Management")
    bullet(doc, "Sliding window: 10 messages retained per conversation")
    bullet(doc, "Per-turn truncation: Max 2 result items per tool response")
    bullet(doc, "Session persistence: FileSessionManager (local disk)")
    bullet(doc, "Conversation ID: UUID-based tracking across turns")
    bullet(doc, "Prompt validation: Max 2048 chars, blocks special chars (% _ $ ; : ^ * @)")

    h2(doc, "9.4 Suggestion Pills (UI Pre-built Queries)")
    tbl(doc,
        ["#", "Suggestion Text"],
        [
            ["1", "List drug aliases for Adderall"],
            ["2", "Generate a table of drugs, diseases and clinical trial researched by Biogen Inc"],
            ["3", "What assets does Eugene know about companies with names like biogen"],
            ["4", "Does Mycophenolate mofetil have any relationships to PTRH2? If so explain"],
            ["5", "What recent pubmed studies mention ABL1?"],
            ["6", "What organizations are related to pmid 41402159?"],
            ["7", "What facts does eugene know about Sickle cell anemia?"],
        ],
        widths=[0.8, 15.2])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 10. WORKFLOW ORCHESTRATION
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "10. Workflow Orchestration")

    h2(doc, "10.1 Query Execution Flow (Streaming)")
    code(doc,
        "1. User submits prompt via Streamlit UI\n"
        "2. UI sends POST /agent/api/query/stream\n"
        "   Headers: Authorization: Bearer <EUGENE_JWT>\n"
        "   Body: {prompt, conversation_id, include_tools}\n"
        "3. Agent WS validates JWT + checks user in allowlist\n"
        "4. Agent WS initializes EugeneDataAgent:\n"
        "   a. LlmFactory creates model (Anthropic or OpenAI)\n"
        "   b. MCPClient connects to MCP server with JWT\n"
        "   c. MCPClient.list_tools() discovers 12 available tools\n"
        "   d. Local tools added (calculator, current_time, python_repl)\n"
        "   e. Strands Agent created with system prompt + all tools\n"
        "5. Agent executes ReAct loop:\n"
        "   a. REASON: LLM analyzes query, plans approach\n"
        "   b. ACT: LLM calls selected MCP tool(s)\n"
        "   c. MCP tool authenticates with Core API (JWT forwarded)\n"
        "   d. Core API executes parameterized Cypher query\n"
        "   e. OBSERVE: LLM reviews results, decides next action\n"
        "   f. Repeat until answer is complete\n"
        "6. Streaming events emitted:\n"
        '   {"type": "session", "session_id": "<uuid>"}\n'
        '   {"type": "content", "content": "token..."}\n'
        '   {"type": "done", "content": ""}\n'
        "7. UI displays tokens in real-time with cursor indicator\n"
        "8. Metrics logged: total_tokens, execution_time, tools_used\n"
    )

    h2(doc, "10.2 Docker Compose Startup Orchestration")
    code(doc,
        "Dependency Chain (automatic via depends_on + healthcheck):\n"
        "\n"
        "neo4j (healthcheck: wget localhost:7474, 10s interval, 30s startup)\n"
        "  |-> eugene_ws (depends: neo4j HEALTHY)\n"
        "       |       (healthcheck: urllib localhost:8000/health, 10s, 15s startup)\n"
        "       |-> eugene_mcp (depends: eugene_ws HEALTHY)\n"
        "            |-> eugene_agent_ws (depends: eugene_mcp)\n"
        "                 |-> eugene_agent_ui (depends: eugene_agent_ws)\n"
    )

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 11. DEPLOYMENT MODEL & CI/CD
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "11. Deployment Model & CI/CD")

    h2(doc, "11.1 CI/CD Pipeline (GitLab)")
    tbl(doc,
        ["Stage", "Job(s)", "Trigger", "Actions"],
        [
            ["echo", "debug", "All branches", "Log commit info"],
            ["scan", "checkov-scan", "MR to qa/main", "Checkov IaC scan (fail on HIGH/CRITICAL)"],
            ["docker", "build-push", "qa, main, feature/*", "Build Docker images, push to ECR (010928221940)"],
            ["terraform-ec2", "validate, plan", "qa, main", "Terraform init/validate/plan EC2 infra"],
            ["apply-ec2", "apply", "qa, main (manual)", "Terraform apply EC2 (manual approval gate)"],
            ["terraform-services", "validate, plan", "qa, main", "Terraform init/validate/plan ECS services"],
            ["apply-services", "apply", "qa, main (manual)", "Terraform apply ECS (manual approval gate)"],
        ],
        widths=[3, 2.5, 3, 7.5])

    h2(doc, "11.2 Branch Strategy")
    code(doc,
        "feature/* -> Docker build only (no deploy)\n"
        "qa        -> Full pipeline: build + scan + terraform plan/apply (staging)\n"
        "main      -> Full pipeline: build + scan + terraform plan/apply (production)\n"
        "\n"
        "AWS OIDC Authentication:\n"
        "  GitLab OIDC Token -> AWS STS assume-role-with-web-identity\n"
        "  Role: arn:aws:iam::010928221940:role/csl-gitlab-ci-cd-scop-all-branches\n"
        "  Session duration: 3600 seconds\n"
    )

    h2(doc, "11.3 Docker Images")
    tbl(doc,
        ["Image", "Dockerfile (Local)", "Dockerfile (Prod)", "Base", "CMD"],
        [
            ["eugene_ws", "docker/eugene_ws/", "containers/eugene_ws/", "python:3.13-slim", "uvicorn eugene_ws:app --host 0.0.0.0 --port 8000"],
            ["eugene_mcp", "docker/eugene_mcp/", "difflabs/containers/eugene_mcp/", "python:3.13-slim", "python src/eugene_mcp.py --host 0.0.0.0 --port 8000"],
            ["eugene_agent_ws", "docker/eugene_agent_ws/", "difflabs/containers/eugene_agent_ws/", "python:3.13-slim", "uvicorn eugene_chat_ws:app --host 0.0.0.0 --port 8000"],
            ["eugene_agent_ui", "docker/eugene_agent_ui/", "difflabs/containers/eugene_agent_ui/", "python:3.13-slim", "streamlit run src/eugene_agent_ui.py --server.port=8501"],
            ["eugene_neo4j_ce", "N/A (uses image)", "containers/eugene_neo4j_ce/", "neo4j:5.26.9-community", "Sleep loop (manual start)"],
        ],
        widths=[2.5, 3, 3.5, 2.5, 5])

    h2(doc, "11.4 Terraform Modules")
    tbl(doc,
        ["Module", "Source", "Resources Provisioned"],
        [
            ["eugene-ec2", "infrastructure/modules/eugene-ec2/", "EC2 instance (r7i.xlarge), EBS volumes, Security Groups, IAM Instance Profile"],
            ["eugene-services", "infrastructure/modules/eugene-services/", "ECS Cluster, Task Definitions, ALB Target Groups, CloudWatch Logs"],
            ["eugene-containers (difflabs)", "difflabs/iac/eugene-containers/", "ECR repositories for all service images"],
            ["eugene-services (difflabs)", "difflabs/iac/eugene-services/", "ECS services, load balancer targets"],
        ],
        widths=[3.5, 4.5, 8])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 12. ENVIRONMENT CONFIGURATION MATRIX
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "12. Environment Configuration Matrix")

    tbl(doc,
        ["Parameter", "Local Dev", "difflabs (Dev)", "AIA (Staging/Prod)"],
        [
            ["ENVIRONMENT", "local", "production", "production"],
            ["Neo4j URI", "bolt://localhost:17687", "bolt+ssc://10.88.203.244:7687", "neo4j+ssc://<ec2>:7687"],
            ["Neo4j Auth", "neo4j/eugene_local_2024", "AWS Secrets Manager", "AWS Secrets Manager"],
            ["Core API URL", "http://localhost:18000", "https://internal-eugene-search-alb-*.us-east-1.elb.amazonaws.com", "https://eugene-staging.ai.cslg1.cslg.net"],
            ["MCP Server URL", "http://localhost:18443", "https://<alb>:8443", "https://<alb>:8443"],
            ["Agent API URL", "http://localhost:18001", "https://<alb>/agent/api", "https://<alb>/agent/api"],
            ["Chat UI URL", "http://localhost:18501", "https://<alb>:8501", "https://<alb>:8501"],
            ["Auth Mode", "Bypass (local token)", "Entra ID OAuth", "Entra ID OAuth"],
            ["LLM Provider", "Configurable", "Configurable", "Configurable"],
            ["TLS", "Disabled", "Self-signed", "Self-signed"],
            ["Terraform Backend", "N/A", "S3 (us-east-1)", "S3 (eu-central-1)"],
            ["AWS Account", "N/A", "087084717211", "010928221940"],
        ],
        widths=[3.5, 3.5, 4.5, 4.5])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 13. MONITORING & OBSERVABILITY
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "13. Monitoring, Observability & Health Checks")

    h2(doc, "13.1 Health Check Endpoints")
    tbl(doc,
        ["Service", "Endpoint", "Response", "Docker Interval"],
        [
            ["neo4j", "http://localhost:7474", "HTML page (wget spider)", "10s (10 retries, 30s startup)"],
            ["eugene_ws", "http://localhost:8000/health", '{"status": "OK"}', "10s (5 retries, 15s startup)"],
            ["eugene_mcp", "http://localhost:8000/health", '{"status": "OK", "service": "eugene mcp service"}', "On demand"],
            ["eugene_agent_ws", "http://localhost:8000/health", '{"status": "OK", "service": "eugene agentic webservice"}', "On demand"],
        ],
        widths=[3, 4.5, 5.5, 3])

    h2(doc, "13.2 API Canaries (Automated Monitoring)")
    tbl(doc,
        ["Canary", "Endpoint", "Validation"],
        [
            ["HealthEndpointCanary", "GET /health", "HTTP 200 OK response"],
            ["StatsEndpointCanary", "GET /stats", "Valid node/relationship counts returned"],
            ["LabelCountsEndpointCanary", "GET /count/{label}", "Non-zero counts for known labels"],
            ["NodeFindEndpointCanary", "GET /node/find/{value}", "Node ID returned for known entity"],
            ["NodeDetailsEndpointCanary", "POST /node/details", "Node attributes returned for known IDs"],
        ],
        widths=[4, 4, 8])

    body(doc, "Canary targets: difflabs ALB (internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com), "
         "AIA Staging (eugene-staging.ai.cslg1.cslg.net), AIA Prod (eugene.ai.cslg1.cslg.net).")

    h2(doc, "13.3 Agent Execution Metrics")
    bullet(doc, "total_tokens: Total LLM tokens consumed per query")
    bullet(doc, "execution_time: Total agent execution time (seconds, 4 decimal precision)")
    bullet(doc, "tools_used: List of unique tool names invoked during query")
    bullet(doc, "cycle_durations: Time per ReAct loop iteration")
    bullet(doc, "@log_time decorator applied to agent init, execute, and stream functions")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 14. TESTING STRATEGY
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "14. Testing Strategy & Quality Assurance")

    h2(doc, "14.1 Test Framework Configuration")
    tbl(doc,
        ["Setting", "Value"],
        [
            ["Framework", "pytest >= 7.0"],
            ["Parallelism", "pytest-xdist (-n 2 workers)"],
            ["Coverage", "pytest-cov (src/ directory, LCOV + terminal)"],
            ["Markers", "serial (no parallelism), integration (integration tests)"],
            ["Environment", "Loads .env via pytest-dotenv"],
            ["Formatter", "Black (line-length 88)"],
            ["Linter", "Ruff, mypy"],
            ["Coverage Omit", "*/*_test.py, */conftest.py"],
        ],
        widths=[3.5, 12.5])

    h2(doc, "14.2 Pre-Commit Hooks")
    bullet(doc, "Terraform validation (difflabs/iac/ modules)")
    bullet(doc, "Black code formatter on src/")
    bullet(doc, "pytest full suite execution")
    bullet(doc, "Exit code 0 (pass) or 1 (fail, blocks commit)")

    h2(doc, "14.3 Recommended Testing Expansion")
    tbl(doc,
        ["Test Type", "Scope", "Priority"],
        [
            ["E2E Integration", "UI -> Agent WS -> MCP -> Core API -> Neo4j", "HIGH"],
            ["JWT Edge Cases", "Expired, invalid signature, missing claims, wrong audience", "HIGH"],
            ["Load Testing", "Concurrent streaming requests, large result pagination", "MEDIUM"],
            ["LLM Failover", "Anthropic unavailable -> OpenAI fallback", "MEDIUM"],
            ["MCP Unavailability", "Agent behavior when MCP server is down", "MEDIUM"],
            ["Security", "Cypher injection attempts, unauthorized access", "HIGH"],
        ],
        widths=[3, 7, 3])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 15. DATA INGESTION & KNOWLEDGE STRATEGY
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "15. Data Ingestion & Knowledge Strategy")

    h2(doc, "15.1 Data Sources & Status")
    tbl(doc,
        ["Source", "Data Type", "Ingestion Method", "Status", "Record Count"],
        [
            ["DrugBank", "Drugs, aliases, interactions", "CSV bulk import (neo4j-admin)", "LOADED", "4,600 drugs"],
            ["Disease Ontology", "Diseases, MONDO mappings", "CSV bulk import", "LOADED", "17,100 diseases"],
            ["Protein Databases", "Genes, proteins, pathways", "CSV bulk import", "LOADED", "27,700 genes"],
            ["ClinicalTrials.gov", "Trials, sponsors, conditions", "CSV + Cypher", "SCHEMA ONLY", "49,300 nodes (empty)"],
            ["USPTO", "Patents, applications, claims", "API download + Cypher", "NOT INGESTED", "0"],
            ["PubMed/PMC", "Articles, affiliations", "API download + APOC", "NOT INGESTED", "0"],
            ["CSL Internal", "TPP, org data", "Checkpoint files", "PARTIAL", "Various"],
        ],
        widths=[2.5, 3, 3, 2.5, 5])

    h2(doc, "15.2 Three-Phase Ingestion Pipeline")
    code(doc,
        "PHASE 1: BULK IMPORT (Foundational)\n"
        "  sudo systemctl stop neo4j.service\n"
        "  neo4j-admin database import full \\\n"
        "    --nodes=nodes.csv \\\n"
        "    --relationships=edges_dedup.csv \\\n"
        "    --overwrite-destination --verbose\n"
        "  # Result: 129,375 nodes, 4,050,249 relationships in 7.6 seconds\n"
        "  # Peak memory: 1.034 GB\n"
        "  # Source: s3://knowledge-graph-external-data/\n"
        "  sudo systemctl start neo4j.service\n"
        "\n"
        "PHASE 2: FEATURE ENRICHMENT\n"
        "  python src/batch_load_disease_features.py  # 44,133 features, ~53 min\n"
        "  python src/batch_load_drug_features.py     # 7,957 features, ~9.5 min\n"
        "  # Uses APOC batch transactions (1000 rows/batch)\n"
        "\n"
        "PHASE 3: SUPPLEMENTARY DATA\n"
        "  # Clinical trials: eugene/saved_queries/ingest_csv/clinical_trials.cypher\n"
        "  # Patents: bin/docker/ingest-bio-data.py (USPTO API download)\n"
        "  # PubMed: src/pubmed/ module (download + APOC loading)\n"
    )

    h2(doc, "15.3 Local Sample Data Ingestion")
    code(doc,
        "python bin/docker/ingest-sample-data.py\n"
        "  # Connects: bolt://localhost:17687\n"
        "  # Loads: 6 data sources (pharma data, gene editing, entities, relationships, orgs)\n"
        "  # Uses: MD5-based ID generation, MERGE operations\n"
    )

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 16. PROJECT STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "16. Project Structure & Folder Hierarchy")

    code(doc,
        "knowledgeGraph/\n"
        "+-- src/                          # Core API source code\n"
        "|   +-- eugene_ws.py              # FastAPI application entry point\n"
        "|   +-- router/                   # API routing layer\n"
        "|   |   +-- auth/                 # Authentication (Entra ID, JWT, RBAC)\n"
        "|   |   +-- health_router.py      # Health check endpoint\n"
        "|   |   +-- root_router.py        # Root welcome endpoint\n"
        "|   |   +-- release_notes_router.py\n"
        "|   +-- foundation/               # Core graph domain\n"
        "|   |   +-- model/                # Node/Relationship enums, response models\n"
        "|   |   +-- provider/             # Business logic (n-hop, path, facts)\n"
        "|   |   +-- mapper/               # Data transformers (graph, facts, patents)\n"
        "|   |   +-- router/               # API endpoints (labels, count, node, graph, etc.)\n"
        "|   |   +-- infra/db/adapter/     # Neo4j Cypher query adapters\n"
        "|   |   +-- conf/                 # Dependency injection factory\n"
        "|   +-- organization/             # Organization domain\n"
        "|   +-- patent/                   # Patent domain (pgpub, application)\n"
        "|   +-- pubmed/                   # PubMed domain\n"
        "|   +-- clinicaltrail/            # Clinical trial domain\n"
        "|   +-- tpp/                      # Target Product Profile domain\n"
        "|   +-- graph/                    # Graph analytics & community detection\n"
        "|   +-- document/                 # Document analysis & parsing\n"
        "|   +-- centree/                  # Drug development projects\n"
        "|   +-- stats/                    # Database statistics\n"
        "|   +-- infra/                    # Infrastructure (LLM, embeddings, DB connection)\n"
        "|   +-- util/                     # Utilities (regex, timer, case helper)\n"
        "+-- agents/                       # Agent microservices\n"
        "|   +-- eugene-mcp/               # MCP Tool Server (FastMCP)\n"
        "|   |   +-- src/tools/            # 7 tool classes (12 tools)\n"
        "|   |   +-- src/auth/             # JWT verifier\n"
        "|   |   +-- src/conf/             # Configuration\n"
        "|   +-- eugene-agent-ws/          # Agent Backend (Strands)\n"
        "|   |   +-- src/query/agent/      # EugeneDataAgent (ReAct)\n"
        "|   |   +-- src/query/infra/llm/  # LLM Factory (Claude, GPT)\n"
        "|   |   +-- src/query/router/     # Agent API endpoints\n"
        "|   |   +-- src/query/model/      # Request/Response models\n"
        "|   +-- eugene-agent-ui/          # Chat UI (Streamlit)\n"
        "|       +-- src/                  # UI application\n"
        "+-- docker/                       # Local Dockerfiles\n"
        "+-- containers/                   # Production Dockerfiles (AIA)\n"
        "+-- difflabs/                     # Dev environment (containers + Terraform)\n"
        "+-- infrastructure/               # Production Terraform (AIA)\n"
        "|   +-- modules/eugene-ec2/       # EC2 module\n"
        "|   +-- modules/eugene-services/  # ECS services module\n"
        "|   +-- environments/             # qa-ec2, qa-services configs\n"
        "+-- eugene/                       # Neo4j setup, notebooks, saved queries\n"
        "+-- docs/                         # Documentation\n"
        "+-- bin/                          # Operational scripts\n"
        "|   +-- docker/                   # local-up, local-down, ingest scripts\n"
        "|   +-- docker/ecr/              # ECR login, build, tag, push\n"
        "+-- api-canaries/                 # API health monitoring\n"
        "+-- tests/                        # Test data directory\n"
        "+-- docker-compose.yml            # Local 5-service orchestration\n"
        "+-- docker.env.template           # Environment variable template\n"
        "+-- requirements.txt              # Python dependencies\n"
        "+-- .gitlab-ci.yml                # CI/CD pipeline\n"
        "+-- pyproject.toml                # Project metadata\n"
        "+-- .pytest.ini                   # Test configuration\n"
    )

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 17. DEVELOPMENT GUIDE
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "17. Development Guide & Setup Instructions")

    h2(doc, "17.1 Prerequisites")
    bullet(doc, "Python 3.12+ (3.13 recommended)")
    bullet(doc, "Docker Desktop (latest)")
    bullet(doc, "Git")
    bullet(doc, "Terraform >= 1.0.0 (for infrastructure work)")
    bullet(doc, "AWS CLI v2 (for ECR push / S3 access)")

    h2(doc, "17.2 Local Development Setup")
    code(doc,
        "# 1. Clone repository\n"
        "git clone <repo-url>\n"
        "cd knowledgeGraph\n"
        "\n"
        "# 2. Configure environment\n"
        "cp docker.env.template docker.env\n"
        "# Edit docker.env: set API keys, Neo4j password\n"
        "\n"
        "# 3. Start all services\n"
        "docker compose up --build\n"
        "# Or use helper script:\n"
        "bin/docker/local-up.sh --build\n"
        "\n"
        "# 4. Ingest sample data (optional)\n"
        "python bin/docker/ingest-sample-data.py\n"
        "\n"
        "# 5. Access services:\n"
        "#   Neo4j Browser:    http://localhost:17474\n"
        "#   Core API Swagger: http://localhost:18000/docs\n"
        "#   Core API Login:   http://localhost:18000/login\n"
        "#   Agent API Docs:   http://localhost:18001/docs\n"
        "#   Chat UI:          http://localhost:18501\n"
        "\n"
        "# 6. Stop services\n"
        "bin/docker/local-down.sh          # Keep data\n"
        "bin/docker/local-down.sh --reset  # Delete Neo4j volumes\n"
    )

    h2(doc, "17.3 Running Core API Locally (without Docker)")
    code(doc,
        "python -m venv venv_eugene_ws\n"
        "source venv_eugene_ws/bin/activate\n"
        "pip install -r requirements.txt\n"
        "cp .env.template .env\n"
        "# Edit .env with local Neo4j credentials\n"
        "uvicorn eugene_ws:app --app-dir src --host 127.0.0.1 --port 8000 --reload\n"
    )

    h2(doc, "17.4 Running Tests")
    code(doc,
        "pytest                    # All tests with coverage\n"
        "pytest -n 4               # 4 parallel workers\n"
        "pytest -m integration     # Integration tests only\n"
        "pytest -m serial          # Serial (DB-dependent) tests\n"
        "pytest src/organization/  # Single domain tests\n"
    )

    h2(doc, "17.5 Deploying to difflabs")
    code(doc,
        "# Login to ECR\n"
        "bin/docker/ecr/login.sh\n"
        "\n"
        "# Build, tag, push images\n"
        "bin/docker/ecr/build.sh\n"
        "bin/docker/ecr/tag.sh\n"
        "bin/docker/ecr/push.sh\n"
        "\n"
        "# Deploy infrastructure\n"
        "cd difflabs/iac/eugene-services\n"
        "./bin/init-difflabs.sh\n"
        "./bin/plan-difflabs.sh\n"
        "./bin/apply-difflabs.sh\n"
    )

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # 18. RISKS, MITIGATIONS & OPEN QUESTIONS
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "18. Risks, Mitigations & Open Questions")

    h2(doc, "18.1 Risk Register")
    tbl(doc,
        ["#", "Risk", "Severity", "Likelihood", "Mitigation", "Status"],
        [
            ["1", "Cypher injection in one-hop adapter", "HIGH", "MEDIUM", "Parameterize all Cypher queries using $variables", "OPEN"],
            ["2", "No API rate limiting", "MEDIUM", "MEDIUM", "Add FastAPI middleware (slowapi)", "OPEN"],
            ["3", "SAST/DAST scanning disabled", "MEDIUM", "HIGH", "Re-enable in CI pipeline", "OPEN"],
            ["4", "Self-signed TLS certificates", "LOW", "HIGH", "Migrate to AWS ACM", "OPEN"],
            ["5", "Incomplete data (patents, PubMed)", "MEDIUM", "HIGH", "Execute pending ingestion pipelines", "IN PROGRESS"],
            ["6", "AIA deployment broken", "HIGH", "HIGH", "Fix ECS IAM permission issue", "OPEN"],
            ["7", "Single MCP instance", "MEDIUM", "LOW", "Implement S3SessionManager", "PLANNED"],
            ["8", "Static role mapping", "LOW", "LOW", "Migrate to DB-backed roles", "OPEN"],
            ["9", "Neo4j CE limitations", "MEDIUM", "LOW", "Evaluate Enterprise Edition for RBAC", "DEFERRED"],
            ["10", "LLM provider outage", "MEDIUM", "LOW", "Dual provider auto-fallback", "PARTIAL"],
            ["11", "API key in docker.env", "HIGH", "LOW", ".gitignore excludes; use Secrets Manager", "MITIGATED"],
            ["12", "Python version variance", "LOW", "LOW", "Standardize on Python 3.13", "OPEN"],
        ],
        widths=[0.6, 3.5, 1.5, 1.5, 5, 2])

    h2(doc, "18.2 Open Questions")
    tbl(doc,
        ["#", "Question", "Context", "Priority"],
        [
            ["1", "When will patent and PubMed data ingestion be completed?", "Code exists but data not loaded", "HIGH"],
            ["2", "What is the plan to fix AIA ECS IAM permissions?", "Production deployment blocked", "HIGH"],
            ["3", "Should qa branch be merged into main?", "Branches are desynced", "HIGH"],
            ["4", "Should role-based filtering be at API or DB level?", "Neo4j CE lacks native RBAC", "MEDIUM"],
            ["5", "Should MCP scale horizontally (S3SessionManager)?", "Currently single instance", "MEDIUM"],
            ["6", "Should SAST/DAST be mandatory for all MRs?", "Currently disabled in pipeline", "MEDIUM"],
            ["7", "What is the TLS certificate renewal strategy?", "Self-signed certs expire", "MEDIUM"],
            ["8", "What additional MCP tools needed for MVP?", "PubMed, ChEMBL stubs exist", "MEDIUM"],
            ["9", "What is the target SLA for API response times?", "No documented requirements", "MEDIUM"],
            ["10", "Should clinical trial data be re-ingested or removed?", "49.3K shell nodes exist", "LOW"],
        ],
        widths=[0.6, 5, 5, 2])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # APPENDIX A: CYPHER QUERY CATALOG
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "Appendix A: Complete Cypher Query Catalog")

    queries = [
        ("Count All Nodes by Label", "MATCH (n:`{label}`)\nRETURN count(n) as count"),
        ("Find Node by Value", "MATCH (n)\nWHERE n.node_name =~ '(?i).*{value}.*'\n  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\nRETURN labels(n), n.node_id, n.node_name"),
        ("Node Details by IDs", "MATCH (n)\nWHERE (n.is_hidden IS NULL OR NOT n.is_hidden)\n  AND n.node_id IN $node_ids\nRETURN labels(n) as labels, n.node_id as id,\n  n.node_name as value, n.node_source as source,\n  n.description as description"),
        ("N-Hop Graph Traversal", "MATCH (start {node_id: $start_id})-[r]-{0,{n_hop}}(end)\nUNWIND(r) AS rel\nRETURN DISTINCT startNode(rel).node_name,\n  endNode(rel).node_name, type(rel)\nORDER BY startName SKIP $offset LIMIT $limit"),
        ("Drug Aliases by Name", "MATCH (n) WHERE n.node_name = $drug_name\n  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\nCALL apoc.path.subgraphNodes([n],\n  {relationshipFilter: 'has_drug_alias'}) YIELD node\nRETURN DISTINCT node.node_name, node.node_id,\n  node.drug_bank_id, 'drug' in labels(node) as is_canonical"),
        ("Patents by Drug", "MATCH (n:`DRUG`)-[r:`disclosed_in`]-(n2:`Patent_Application`)\nWHERE n.node_id = $drug_id\nRETURN n.node_id, n.node_name, n2.patent_id\nORDER BY patent_id DESC SKIP $offset LIMIT $limit"),
        ("PubMed by Gene", "MATCH (n:`GENE_PROTEIN`)-[r:`analyzed_in`]-(n2:`Research`)\nWHERE n.node_name = $gene\nRETURN n2.pmid, n2.title\nORDER BY n2.pmid DESC SKIP $offset LIMIT $limit"),
        ("Organization Search", "MATCH (o:`Organization`)\nWHERE o.organization_canonical_name =~ $pattern\nRETURN o.org_id, o.organization_canonical_name,\n  o.organization_type\nSKIP $skip LIMIT $limit"),
        ("Organization Assets", "MATCH (start:`Organization`)-[rel1]-(ct:`ClinicalTrial`)\n  -[rel2]-(end:`DISEASE`|`DRUG`)\nWHERE start.org_id = $org_id\nRETURN start.organization_canonical_name,\n  ct.nct_id, labels(end), end.node_name\nORDER BY trial DESC SKIP $skip LIMIT $limit"),
        ("GDS Node Similarity", "MATCH (d1:`DRUG`|`DISEASE`)\nWHERE d1.node_name =~ '(?i).*{value}.*'\nCALL gds.nodeSimilarity.filtered.stream(\n  '{projection}', {\n    degreeCutoff: 1, similarityCutoff: .45,\n    similarityMetric: 'COSINE',\n    sourceNodeFilter: [d1]\n  }) YIELD node1, node2, similarity\nRETURN similarity, gds.util.asNode(node1).node_name,\n  gds.util.asNode(node2).node_name\nORDER BY similarity DESC"),
    ]
    for title, q in queries:
        h3(doc, title)
        code(doc, q)

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # APPENDIX B: ENVIRONMENT VARIABLES
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "Appendix B: Environment Variable Reference")

    tbl(doc,
        ["Variable", "Service(s)", "Required", "Description"],
        [
            ["ENVIRONMENT", "eugene_ws, agent_ws", "Yes", "local or production"],
            ["NEO4J_URI", "eugene_ws", "Yes", "Neo4j connection URI"],
            ["NEO4J_USERNAME", "eugene_ws, neo4j", "Yes", "Database username"],
            ["NEO4J_PASSWORD", "eugene_ws, neo4j", "Yes", "Database password"],
            ["EUGENE_TENANT_ID", "All backend", "Yes", "JWT issuer tenant ID"],
            ["EUGENE_CLIENT_ID", "All backend", "Yes", "JWT audience client ID"],
            ["EUGENE_CLIENT_SECRET", "All backend", "Yes", "JWT HS256 signing key"],
            ["ENTRA_TENANT_ID", "eugene_ws", "Prod only", "Azure AD tenant"],
            ["ENTRA_CLIENT_ID", "eugene_ws", "Prod only", "OAuth app registration ID"],
            ["ENTRA_CLIENT_SECRET", "eugene_ws", "Prod only", "OAuth client secret"],
            ["ENTRA_AUTHORITY", "eugene_ws", "Prod only", "Entra ID authority URL"],
            ["ENTRA_SCOPE", "eugene_ws", "Prod only", "OAuth scopes"],
            ["REDIRECT_URI", "eugene_ws", "Prod only", "OAuth callback URL"],
            ["REDIRECT_PATH", "eugene_ws", "Prod only", "OAuth callback path"],
            ["EUGENE_API_BASE", "eugene_mcp", "Yes", "Core API base URL"],
            ["EUGENE_ISSUER", "eugene_mcp", "Yes", "JWT issuer URL"],
            ["EUGENE_AUDIENCE", "eugene_mcp", "Yes", "JWT audience claim"],
            ["EUGENE_MCP_SERVER_URL", "eugene_agent_ws", "Yes", "MCP server URL"],
            ["EUGENE_AGENT_ALLOWLIST", "eugene_agent_ws", "Yes", "Pipe-separated user UPNs"],
            ["EUGENE_AGENT_API_URL", "eugene_agent_ui", "No", "Agent API base URL"],
            ["LLM_PROVIDER", "eugene_agent_ws", "No", "anthropic or openai"],
            ["ANTHROPIC_API_KEY", "eugene_agent_ws", "Cond.", "Anthropic API key"],
            ["ANTHROPIC_MODEL_ID", "eugene_agent_ws", "No", "Anthropic model (default: claude-sonnet-4-20250514)"],
            ["OPENAI_API_KEY", "eugene_agent_ws", "Cond.", "OpenAI API key"],
            ["OPENAI_MODEL_ID", "eugene_agent_ws", "No", "OpenAI model (default: gpt-4.1-mini)"],
            ["HF_HUB_CACHE", "eugene_ws", "No", "HuggingFace model cache directory"],
            ["S3_STAGING_BUCKET", "Production containers", "Prod only", "S3 bucket for .env and models"],
        ],
        widths=[3.5, 3, 1.5, 8])

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    # APPENDIX C: RELEASE NOTES
    # ═══════════════════════════════════════════════════════════════════════
    h1(doc, "Appendix C: Release Notes")

    tbl(doc,
        ["Version", "Key Features"],
        [
            ["v1.0", "Initial release: Neo4j graph database, foundational drug-disease-gene data"],
            ["v1.1", "Added patent search, PubMed search, drug alias endpoints"],
            ["v1.2", "Organization search and assets, graph facts endpoint"],
            ["v2.0", "MCP server with 12 tools, agent backend with Strands framework"],
            ["v2.1", "Streamlit chat UI, dual LLM support (Anthropic + OpenAI)"],
            ["v2.2", "Docker Compose local dev stack, CI/CD pipeline, Terraform IaC"],
        ],
        widths=[2, 14])

    # Footer
    doc.add_paragraph("")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("--- End of Document ---")
    r.font.size = Pt(10); r.font.color.rgb = RGBColor(128,128,128)

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Generated from complete codebase analysis  |  euGENE Knowledge Graph  |  March 2026")
    r.font.size = Pt(9); r.font.color.rgb = RGBColor(128,128,128)

    return doc


# ── PDF Conversion ───────────────────────────────────────────────────────────

def to_pdf(docx_path, pdf_path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.platypus import Table as RLT, TableStyle as RLTS
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from docx import Document as DR

    d = DR(docx_path)
    pdf = SimpleDocTemplate(pdf_path, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.2*cm, rightMargin=2.2*cm)

    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle('CT', fontName='Helvetica-Bold', fontSize=28, alignment=1, spaceAfter=8, textColor=colors.HexColor('#1F4E79')))
    ss.add(ParagraphStyle('CS', fontName='Helvetica', fontSize=13, alignment=1, spaceAfter=5, textColor=colors.HexColor('#595959')))
    ss.add(ParagraphStyle('H1C', fontName='Helvetica-Bold', fontSize=15, spaceBefore=16, spaceAfter=7, textColor=colors.HexColor('#1F4E79')))
    ss.add(ParagraphStyle('H2C', fontName='Helvetica-Bold', fontSize=12, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#2E75B6')))
    ss.add(ParagraphStyle('H3C', fontName='Helvetica-Bold', fontSize=10, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor('#2E75B6')))
    ss.add(ParagraphStyle('BC', fontName='Helvetica', fontSize=8.5, spaceBefore=2, spaceAfter=2, leading=12))
    ss.add(ParagraphStyle('BLC', fontName='Helvetica', fontSize=8.5, spaceBefore=1, spaceAfter=1, leftIndent=18, bulletIndent=8, leading=11))
    ss.add(ParagraphStyle('CC', fontName='Courier', fontSize=6.5, spaceBefore=3, spaceAfter=3, leftIndent=12, leading=9, textColor=colors.HexColor('#1E1E1E')))

    story = []
    def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    for para in d.paragraphs:
        txt = para.text.strip()
        if not txt:
            story.append(Spacer(1,4)); continue
        sn = para.style.name if para.style else ""
        if "Heading 1" in sn: story.append(Paragraph(esc(txt), ss['H1C']))
        elif "Heading 2" in sn: story.append(Paragraph(esc(txt), ss['H2C']))
        elif "Heading 3" in sn: story.append(Paragraph(esc(txt), ss['H3C']))
        elif any(r.font.size and r.font.size >= Pt(28) for r in para.runs if r.font.size):
            story.append(Spacer(1,100)); story.append(Paragraph(esc(txt), ss['CT']))
        elif any(r.font.size and Pt(13) <= r.font.size <= Pt(22) for r in para.runs if r.font.size):
            story.append(Paragraph(esc(txt), ss['CS']))
        elif "List" in sn or "Bullet" in sn:
            story.append(Paragraph(f"&bull; {esc(txt)}", ss['BLC']))
        elif any(r.font.name and "Courier" in r.font.name for r in para.runs if r.font.name):
            for ln in txt.split("\n"):
                story.append(Paragraph(esc(ln), ss['CC']))
        else:
            story.append(Paragraph(esc(txt), ss['BC']))

    for table in d.tables:
        data = []
        for row in table.rows:
            rd = []
            for cell in row.cells:
                ct = cell.text.strip()
                rd.append(Paragraph(esc(ct), ParagraphStyle('TC', fontName='Helvetica', fontSize=6.5, leading=8)))
            data.append(rd)
        if data:
            nc = len(data[0])
            cw = (A4[0] - 4.4*cm) / nc
            t = RLT(data, colWidths=[cw]*nc, repeatRows=1)
            t.setStyle(RLTS([
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#1F4E79')),
                ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),6.5),
                ('GRID',(0,0),(-1,-1),0.4,colors.grey),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F2F2F2')]),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('TOPPADDING',(0,0),(-1,-1),2),
                ('BOTTOMPADDING',(0,0),(-1,-1),2),
            ]))
            story.append(Spacer(1,4)); story.append(t); story.append(Spacer(1,4))

    pdf.build(story)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DOCX_OUT), exist_ok=True)

    print("Building enterprise DOCX document...")
    doc = build()
    doc.save(DOCX_OUT)
    print(f"  DOCX saved: {DOCX_OUT}")

    print("Converting to PDF...")
    to_pdf(DOCX_OUT, PDF_OUT)
    print(f"  PDF saved: {PDF_OUT}")

    # Print stats
    from docx import Document as DR2
    d2 = DR2(DOCX_OUT)
    paras = len(d2.paragraphs)
    tables = len(d2.tables)
    print(f"\nDocument Stats: {paras} paragraphs, {tables} tables")
    print("Done!")
