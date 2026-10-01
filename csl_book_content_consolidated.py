"""
Consolidated client-presentation content for the Eugene programme.

A single cohesive document covering:
   1. Overview of Eugene
   2. Scope and Capabilities
   3. Detailed Current-State Architecture
   4. Gaps Identified
   5. Technical Recommendations

Distilled from the Project Validation Document, Stage 1 Assessment & Audit
Report, Developer Guide, and CSL_Arch_nextGen.pdf.

Mermaid figures from DEVELOPER_GUIDE.md are pre-rendered to PNG via
generate_developer_guide.py and cached under .dev_guide_assets/.
"""
import os

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       ".dev_guide_assets")
def _mmd(n):
    return os.path.join(_ASSETS, f"diagram_{n:02d}.png")

# Mermaid figures from the Developer Guide (rendered by mmdc):
#   1 high-level architecture (LR)
#   2 facts-request sequence
#   3 data ingestion pipeline
#   4 API router groups by domain
#   5 agent / Strands ReAct loop
#   6 JWT auth login + validation
#   7 CI / CD pipeline (push -> scan -> docker -> tf plan)
MMD_ARCH        = _mmd(1)
MMD_REQ_SEQ     = _mmd(2)
MMD_INGEST      = _mmd(3)
MMD_API_ROUTERS = _mmd(4)
MMD_AGENT_REACT = _mmd(5)
MMD_AUTH        = _mmd(6)
MMD_CICD        = _mmd(7)

# Next-generation Research Agent architecture, rendered from
# docs/CSL_Arch.drawio.svg via headless Chromium.
NEXTGEN_RESEARCH_AGENT_SVG = os.path.join(_ASSETS,
                                          "csl_arch_nextgen_research.png")

DOC_TITLE    = "Eugene Platform — Consolidated Programme Briefing"
DOC_SUBTITLE = ("Overview, Scope, Current-State Architecture, "
                "Gaps and Technical Recommendations")
DOC_FILE_PDF  = "EUGENE_CONSOLIDATED_BRIEFING.pdf"
DOC_FILE_DOCX = "EUGENE_CONSOLIDATED_BRIEFING.docx"


CONSOLIDATED_BOOK = [

    # ════════════════════════════════════════════════════════════════════
    # FRONT MATTER
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Front Matter"),

    ("CHAPTER", "About This Document"),
    ("PARA",
     "This briefing is the single, consolidated reference for the Eugene "
     "biomedical knowledge graph and agentic AI programme at CSL Behring. It "
     "is intended for client and stakeholder presentations and replaces the "
     "need to navigate between the Project Validation Document, the Stage 1 "
     "Assessment & Audit Report, the Developer Guide, and the next-generation "
     "architecture proposal. The five sections that follow tell a complete "
     "technical story: what Eugene is, what it does today, how it is built, "
     "where the gaps are, and what we recommend doing about them."),
    ("PARA",
     "Every architectural claim in this document is grounded in source "
     "material in the docs/ folder. Where a measurement, a finding, or a "
     "remediation is cited, it traces to one of the four primary sources "
     "above. Diagrams are reproduced from the canonical Mermaid sources in "
     "the Developer Guide, augmented with the next-generation architecture "
     "preserved in CSL_Arch_nextGen.pdf."),

    ("CHAPTER", "Document Map"),
    ("BULLETS", [
        "Section 1 — Overview of Eugene: who it is for, what it does, and why "
        "it matters to CSL Behring.",
        "Section 2 — Scope and Capabilities: what the platform answers today, "
        "what data sources are integrated, and what use cases are in production.",
        "Section 3 — Detailed Current-State Architecture: the five running "
        "services, the data model, the request flow, the authentication "
        "design, and the AWS deployment topology.",
        "Section 4 — Gaps Identified: the twenty-one findings of the Stage 1 "
        "audit (CRITICAL, HIGH, MEDIUM) plus operational, data, and "
        "experience gaps observed in this assessment.",
        "Section 5 — Technical Recommendations: the next-generation target "
        "architecture, the four-phase remediation roadmap, the user-experience "
        "enhancement programme, and the non-functional commitments.",
    ]),

    ("CALLOUT",
     "Confidential. Prepared for CSL Behring stakeholders. Reproduction or "
     "distribution outside CSL Behring requires programme-lead approval."),


    # ════════════════════════════════════════════════════════════════════
    # 1 — OVERVIEW OF EUGENE
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Section 1 — Overview of Eugene"),

    ("CHAPTER", "1.  What Eugene Is"),
    ("PARA",
     "Eugene is an enterprise-grade, AI-powered biomedical knowledge graph "
     "platform purpose-built for CSL Behring's competitive intelligence and "
     "research analytics operations. It allows non-technical users — Business "
     "Development analysts, R&D scientists, and Medical Affairs professionals "
     "— to pose complex, multi-hop biomedical questions in plain English and "
     "to receive synthesised, evidence-backed answers in seconds. The "
     "underlying graph integrates authoritative public data (USPTO patents, "
     "PubMed literature, ClinicalTrials.gov records) with internal CSL data "
     "assets, delivering a single conversational surface across what was "
     "previously a fragmented set of databases and tools."),

    ("SECTION", "1.1  Mission Statement"),
    ("PARA",
     "Eugene exists to compress the time required to answer biomedical "
     "competitive-intelligence and research questions from days of manual "
     "database navigation to seconds of conversational interaction. The "
     "Project Validation Document positions Eugene as a platform whose "
     "explicit objective is that a non-technical user should pose a "
     "multi-hop biomedical question in plain English and receive a "
     "synthesised, evidence-backed answer in real time."),

    ("SECTION", "1.2  Stakeholder Map"),
    ("TABLE", [
        ["Role",                   "Stakeholder Group",                  "Responsibility"],
        ["Executive Sponsor",      "CSL Behring Leadership",             "Strategic direction; budget approval"],
        ["Product Owner",          "R&D / Competitive Intelligence",     "Requirements prioritisation; user acceptance"],
        ["Platform Engineering",   "AI / Data Engineering Team",          "Architecture, development, deployment"],
        ["End Users",              "Scientists, Analysts, Medical Affairs", "Query, interpret, and act on insights"],
        ["Security / Compliance",  "IT Security; Legal",                  "Authentication, data governance review"],
        ["Infrastructure",         "Cloud Platform Team",                 "AWS environment management"],
    ]),

    ("SECTION", "1.3  Business Value"),
    ("PARA",
     "Eugene delivers five business outcomes today:"),
    ("BULLETS", [
        "Accelerated competitive intelligence — analysts query drug pipelines "
        "and patent landscapes in seconds rather than hours of manual "
        "database navigation.",
        "Reduced research latency — the agent eliminates the need for "
        "manual Cypher authorship, removing a hard skill barrier between "
        "scientists and the graph.",
        "Centralisation of biomedical knowledge — USPTO, PubMed, "
        "ClinicalTrials.gov, DrugBank, and internal CSL data are reachable "
        "through a single conversational surface.",
        "Scalable cloud-native infrastructure — AWS ECS Fargate, ALB-fronted, "
        "Terraform-managed in two environments (development and production).",
        "Auditability — every agent reasoning chain decomposes into structured "
        "MCP tool calls that are individually loggable and explainable.",
    ]),


    # ════════════════════════════════════════════════════════════════════
    # 2 — SCOPE AND CAPABILITIES
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Section 2 — Scope and Capabilities"),

    ("CHAPTER", "2.  What Eugene Can Answer"),

    ("SECTION", "2.1  Representative Questions"),
    ("PARA",
     "The following questions, drawn from the validation document and "
     "demonstrated end-to-end on the platform today, illustrate the breadth "
     "of capability. Each is answerable by a non-technical user in under "
     "thirty seconds:"),
    ("BULLETS", [
        "Which organisations hold patents on drugs targeting the same "
        "indication as our lead compound, and what is their clinical trial "
        "status?",
        "Find all organisations in Germany with active Phase III trials in "
        "rare disease.",
        "Which drugs target EGFR and what trials are sponsored by which "
        "organisations?",
        "Trace the connection between AstraZeneca and the KRAS gene through "
        "patents and trials.",
        "What are the relationships of Hemophilia A in the graph?",
        "What are the drug aliases for Adderall?",
        "Generate a table of drugs, diseases and clinical trials researched "
        "by Biogen Inc.",
        "What recent PubMed studies mention ABL1?",
    ]),

    ("CHAPTER", "3.  Data Coverage"),

    ("SECTION", "3.1  Data Sources Integrated"),
    ("PARA",
     "The Mermaid pipeline below — reproduced from the developer guide — "
     "shows how each source is downloaded, transformed into Entity / "
     "Relationship records, expanded with type nodes, and merged into "
     "Neo4j:"),
    ("IMAGE",   MMD_INGEST),
    ("CAPTION", "Figure (Mermaid). Data ingestion pipeline (download → "
                "transform → load), from DEVELOPER_GUIDE.md §5."),
    ("TABLE", [
        ["Source",              "Status",  "Description"],
        ["USPTO Patents",       "Loaded",  "Patent records, filing dates, assignees"],
        ["PubMed",              "Loaded",  "Journal articles, abstracts, citations"],
        ["ClinicalTrials.gov",  "Loaded",  "Trial records, phases, sponsors"],
        ["Internal CSL data",   "Loaded",  "Proprietary biomedical and deal data"],
        ["DrugBank",            "Loaded",  "Drug mechanisms, indications, status"],
        ["Organisation DB",     "Loaded",  "Pharma / biotech company records"],
    ]),

    ("SECTION", "3.2  Graph Scale"),
    ("PARA",
     "The Eugene knowledge graph contains approximately 484,000 nodes "
     "organised across nine principal labels and approximately 21 million "
     "typed, directed edges. Memory is tuned per environment, with production "
     "running 16 GB pagecache and 4–8 GB heap on dedicated EC2."),

    ("TABLE", [
        ["Node Label",     "Approx. Count", "Key Properties"],
        ["Drug",            "4.6 k",   "node_id, name, mechanism_of_action, status, aliases"],
        ["Disease",         "17.1 k",  "node_id, name, icd_code, mesh_id, synonyms"],
        ["GeneProtein",     "27.7 k",  "node_id, name, hgnc_id, entrez_id, symbol"],
        ["ClinicalTrial",   "49.3 k",  "node_id, nct_id, title, phase, status, sponsor"],
        ["Patent",          "50 k +",  "patent_id, title, filing_date, grant_date, assignee"],
        ["Organization",    "26.1 k",  "node_id, name, hq_country, org_type, aliases"],
        ["Publication",     "100 k +", "node_id, pmid, title, journal, publication_date"],
        ["Annotation",      "—",       "source, text_span, confidence"],
        ["Therapeutic Area", "~ 500",   "node_id, name"],
    ]),

    ("SECTION", "3.3  Capability Inventory"),
    ("BULLETS", [
        "Twenty REST endpoints covering identity, foundation queries, "
        "drug/disease/patent/PubMed/organisation domains, similarity, and "
        "stats.",
        "Twelve MCP tools mediating the agent's access to the API: "
        "fetch_identity, fetch_by_label, fetch_similar, lookup_node_by_value, "
        "fetch_node_details, fetch_drug_aliases, fetch_facts, "
        "fetch_node_relationships, fetch_paths, has_reachable_path, "
        "find_organization_names, find_organization_assets.",
        "Two-hop graph traversal with hard-cap (MAX_SUPPORTED_HOPS=2) to "
        "prevent fan-out.",
        "Token-by-token streaming via Server-Sent Events for ChatGPT-class "
        "user experience.",
        "Dual-LLM provider auto-detect (OpenAI GPT-4.1 and Anthropic Claude "
        "Sonnet) with one-environment-variable swap.",
        "Microsoft Entra ID single sign-on plus Eugene-issued HS256 JWT for "
        "service-to-service propagation.",
    ]),


    # ════════════════════════════════════════════════════════════════════
    # 3 — CURRENT-STATE ARCHITECTURE
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Section 3 — Detailed Current-State Architecture"),

    ("CHAPTER", "4.  High-Level Architecture"),

    ("SECTION", "4.1  Five-Service Topology"),
    ("PARA",
     "Eugene is composed of five running services arranged in a five-tier "
     "microservice architecture, following Domain-Driven Design with "
     "hexagonal (ports-and-adapters) layering inside the Core API. The "
     "diagram below reproduces the canonical architecture from the Developer "
     "Guide."),

    ("DIAGRAM", "ARCH"),

    ("PARA",
     "The same architecture is also captured in the developer guide as a "
     "Mermaid flowchart, reproduced below verbatim from "
     "<font name='Courier'>docs/DEVELOPER_GUIDE.md</font>:"),
    ("IMAGE",   MMD_ARCH),
    ("CAPTION", "Figure (Mermaid). High-level architecture flowchart, "
                "from DEVELOPER_GUIDE.md §2."),

    ("SECTION", "4.2  Tier Responsibilities"),
    ("TABLE", [
        ["Tier",                "Service",            "Responsibility"],
        ["Presentation",        "eugene-agent-ui",    "User interaction; live token rendering"],
        ["Agent",               "eugene-agent-ws",    "Reasoning loop; tool selection; LLM inference"],
        ["Tool / Orchestration", "eugene-mcp",        "Schema-validated tool surface; JWT enforcement"],
        ["Data API",            "eugene_ws",          "Canonical graph API; 20 REST endpoints"],
        ["Persistence",         "Neo4j 5.26 CE + Milvus", "Graph + vector storage"],
    ]),

    ("SECTION", "4.3  Technology Stack"),
    ("DIAGRAM", "TECHSTACK"),
    ("PARA",
     "The Core API itself is organised by biomedical domain into the "
     "following router groups, faithful to the Mermaid graph in the "
     "developer guide:"),
    ("IMAGE",   MMD_API_ROUTERS),
    ("CAPTION", "Figure (Mermaid). Core API router groups, "
                "from DEVELOPER_GUIDE.md §6."),
    ("PARA",
     "The stack is intentionally Python-centric end-to-end (3.12 / 3.13), "
     "with FastAPI for HTTP services, Strands for the agent loop, FastMCP "
     "for the tool surface, Neo4j 5.26 Community Edition with APOC and GDS "
     "for the graph, and Milvus for vector similarity. Containerisation is "
     "Docker; orchestration is AWS ECS Fargate; infrastructure is "
     "Terraform-managed."),

    ("CHAPTER", "5.  End-to-End Request Flow"),

    ("SECTION", "5.1  Sequence Walk-through"),
    ("PARA",
     "When a user submits a question, control flows through every tier of "
     "the platform. The diagram below traces the canonical seventeen-step "
     "path for the example query \"What are the relationships of "
     "Hemophilia A?\":"),

    ("DIAGRAM", "SEQ"),

    ("PARA",
     "The developer guide records the same flow as a UML sequence diagram, "
     "showing the layered DDD pipeline inside the Core API "
     "(Router → Orchestrator → Provider → Adapter → Neo4j → mappers):"),
    ("IMAGE",   MMD_REQ_SEQ),
    ("CAPTION", "Figure (Mermaid). Request sequence for "
                "<i>GET /graph/facts/start/{id}</i>, from DEVELOPER_GUIDE.md §4."),

    ("SECTION", "5.2  ReAct Loop Inside the Agent"),
    ("DIAGRAM", "REACT"),
    ("PARA",
     "Inside the Agent Backend, the Strands framework drives a ReAct loop: "
     "the LLM reasons (Think), invokes an MCP tool (Act), receives a "
     "structured result (Observe), and repeats until it has sufficient "
     "evidence or its tool budget is exhausted, at which point it "
     "synthesises a streaming answer."),
    ("PARA",
     "The developer guide expands the same loop into a per-tool flowchart "
     "showing how the agent reasons, calls an MCP tool, returns to reason, "
     "and ultimately streams the final answer back to the UI:"),
    ("IMAGE",   MMD_AGENT_REACT),
    ("CAPTION", "Figure (Mermaid). Agent layer with Strands ReAct loop, "
                "from DEVELOPER_GUIDE.md §7."),

    ("CHAPTER", "6.  Data Model"),

    ("SECTION", "6.1  Graph Schema"),
    ("DIAGRAM", "DATAMODEL"),
    ("PARA",
     "The graph carries nine principal node labels — Drug, Disease, "
     "GeneProtein, ClinicalTrial, Patent, Organization, Publication, "
     "Annotation, and Therapeutic Area. Principal relationship types are "
     "TARGETS, INDICATES, ASSOCIATED_WITH, OWNS_PATENT_ON, CONDUCTED_BY, "
     "STUDIES, PUBLISHED_IN, SYNONYM_OF, and PARENT_OF. All Cypher queries "
     "use parameterised binding; no string interpolation appears anywhere "
     "in the source."),

    ("CHAPTER", "7.  Authentication & Authorisation"),

    ("SECTION", "7.1  Two-Layer Identity Model"),
    ("DIAGRAM", "AUTHFLOW"),
    ("PARA",
     "The developer guide describes the same identity flow as a sequence "
     "diagram, showing both the local-mode token issue path and the "
     "per-request validation path:"),
    ("IMAGE",   MMD_AUTH),
    ("CAPTION", "Figure (Mermaid). JWT login and per-request validation, "
                "from DEVELOPER_GUIDE.md §11."),
    ("PARA",
     "Eugene operates a two-layer identity model. Layer 1 is enterprise SSO "
     "via Microsoft Entra ID using OAuth 2.0 Authorization Code flow. Layer 2 "
     "is an Eugene-issued HS256 JWT that propagates between services. After "
     "Entra ID returns an ID token, the Core API issues an Eugene JWT (24-hour "
     "TTL) with claims iss = https://eugene.ai.cslg1.cslg.net/{tenant_id}, "
     "aud = api://eugene/{client_id}, sub = user UPN, and roles. The same JWT "
     "travels with every request from browser to agent, MCP, and Core API; "
     "every tier validates signature, audience, issuer, and expiry."),

    ("SECTION", "7.2  RBAC Status"),
    ("PARA",
     "Row-level RBAC is not implemented today. The roles claim is present in "
     "the JWT but is not enforced inside Cypher. Until Q3 2026, the platform "
     "exposes only public data; introduction of patient-derived or "
     "commercially sensitive data is gated on RBAC implementation."),

    ("CHAPTER", "8.  AWS Deployment Topology"),

    ("DIAGRAM", "DEPLOY"),

    ("SECTION", "8.1  Environment Matrix"),
    ("TABLE", [
        ["Attribute", "Local",               "Difflabs (Dev)",       "AIA (Production)"],
        ["Platform",  "Docker Compose",      "AWS ECS Fargate",       "AWS ECS Fargate"],
        ["Region",    "—",                   "us-east-1",             "eu-central-1"],
        ["Account",   "—",                   "087084717211",          "010928221940"],
        ["Auth",      "Local JWT bypass",    "Entra ID",              "Entra ID"],
        ["Neo4j",     "Container",           "ECS task",              "EC2 (manual)"],
        ["Secrets",   "docker.env",          "Secrets Manager",       "Secrets Manager"],
        ["TLS",       "Disabled",            "ALB-terminated",        "ALB-terminated"],
        ["IaC root",  "—",                   "difflabs/iac/",         "infrastructure/"],
    ]),

    ("SECTION", "8.2  CI / CD"),
    ("PARA",
     "Code pushed to the repository triggers pre-commit hooks (Black, Ruff, "
     "isort), then GitHub Actions runs unit tests, integration tests against "
     "a Neo4j testcontainer, builds the Docker image, pushes to ECR, and "
     "runs Terraform plan. Production deployments require a manual approval "
     "gate before Terraform apply triggers a rolling ECS update. The "
     "developer guide records the same pipeline as a Mermaid flowchart:"),
    ("IMAGE",   MMD_CICD),
    ("CAPTION", "Figure (Mermaid). CI / CD pipeline, "
                "from DEVELOPER_GUIDE.md §13."),


    # ════════════════════════════════════════════════════════════════════
    # 4 — GAPS IDENTIFIED
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Section 4 — Gaps Identified"),

    ("CHAPTER", "9.  Audit Outcome"),

    ("PARA",
     "The Stage 1 assessment identified twenty-one findings across security, "
     "agent framework, database, and observability domains. Two are "
     "CRITICAL, ten are HIGH, and nine are MEDIUM severity. Six positive "
     "findings recognise the platform's architectural strengths and are "
     "preserved through the recommended remediation programme. Estimated "
     "remediation effort to close every CRITICAL and HIGH item is "
     "approximately eight weeks of focused engineering work, parallelisable "
     "across two to three engineers."),

    ("CHAPTER", "10.  Critical Findings"),
    ("PARA",
     "The two CRITICAL findings dominate the first week of the recommended "
     "Phase 1 hardening. Both are fixable in a day or less; both should land "
     "before any further functional work is committed."),

    ("FINDINGS_TABLE", "CRITICAL"),

    ("CHAPTER", "11.  High-Severity Findings"),
    ("PARA",
     "Ten HIGH-severity findings span the agent, security, database, and "
     "observability domains. Eight are quick wins (half a day to one day "
     "each); two require multi-day effort (rate limiting, structured "
     "logging). Together they remove the platform's most acute production "
     "risks."),

    ("FINDINGS_TABLE", "HIGH"),

    ("CHAPTER", "12.  Medium-Severity Findings"),
    ("PARA",
     "Nine MEDIUM-severity findings cover token revocation, PII / PHI "
     "filtering, connection-pool sizing, deep-pagination caps, file-session "
     "robustness, graph statistics, and graph-data freshness. They do not "
     "block limited rollout, but they are required for a "
     "100-concurrent-user posture and for the regulatory expectations that "
     "follow any introduction of patient-derived or commercially sensitive "
     "data."),

    ("FINDINGS_TABLE", "MEDIUM"),

    ("CHAPTER", "13.  Operational, Data, and Experience Gaps"),

    ("SECTION", "13.1  Data Loading Gaps"),
    ("CALLOUT",
     "USPTO patents count is currently zero in production (data deleted, "
     "never reloaded). PubMed count is currently zero (partial ingestion "
     "abandoned). Therapeutic-area subgroup counts are currently zero. "
     "These gaps are documented in the maintenance runbook and addressed "
     "in the data-readiness backlog."),

    ("SECTION", "13.2  Operational Gaps"),
    ("BULLETS", [
        "JWT signing-secret rotation is manual; no scheduled rotation.",
        "Neo4j SSL certificate rotation is manual; expires near year-end.",
        "Production Neo4j is provisioned manually on EC2; not yet "
        "Terraform-managed.",
        "No automated S3 snapshot policy for Neo4j data.",
        "No LLM cost instrumentation; per-query token consumption is not "
        "tracked.",
        "API canaries cover only five of twenty Core API endpoints.",
    ]),

    ("SECTION", "13.3  Experience Gaps in the Streamlit UI"),
    ("BULLETS", [
        "No conversation export (JSON, Markdown, PDF).",
        "No citation panel or evidence drilldown.",
        "No graph visualisation; the agent's reasoning trail is opaque.",
        "No tool-call timeline or agent-decision lineage.",
        "Limited accessibility primitives; no keyboard shortcuts.",
        "Poor mobile responsiveness.",
        "No light / dark theme; no system-prompt templates.",
    ]),

    ("CHAPTER", "14.  Architectural Strengths to Preserve"),
    ("PARA",
     "The audit also surfaced six structural strengths. They are listed "
     "here so that the re-platforming work explicitly retains and amplifies "
     "them rather than refactoring them away."),
    ("POSITIVES_TABLE", None),


    # ════════════════════════════════════════════════════════════════════
    # 5 — TECHNICAL RECOMMENDATIONS
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Section 5 — Technical Recommendations"),

    ("CHAPTER", "15.  Next-Generation Target Architecture"),

    ("SECTION", "15.1  Headline Picture"),
    ("PARA",
     "The next-generation architecture (CSL_Arch_nextGen.pdf) re-imagines "
     "Eugene as one specialist agent within a CSL-owned orchestration layer "
     "running on AWS Bedrock AgentCore. The diagram below summarises the "
     "target state."),

    ("DIAGRAM", "NEXTGEN"),

    ("SECTION", "15.2  Research Agent — End-to-End Reference Architecture"),
    ("PARA",
     "The diagram below — sourced from "
     "<font name='Courier'>docs/CSL_Arch.drawio.svg</font> — renders the "
     "complete CSL-owned Research Agent reference architecture in a single "
     "view. It maps every layer of the next-generation platform from the "
     "BD / Researcher persona through the CSL-owned orchestration and "
     "specialist agents, into AWS Bedrock AgentCore (Runtime, Memory, "
     "Observability) and the AgentCore Gateway, across the authoritative "
     "knowledge tier (Eugene Knowledge Graph plus dual storage with "
     "Milvus indexes and Neo4j embeddings), the CSL data tier (internal "
     "tacit knowledge in SharePoint, Confluence, deal memos and IC "
     "decisions; controlled-access eRooms / VDRs; external and partner "
     "feeds including the Prudentia Sciences platform; and public / "
     "licensed sources covering literature, trials, patents, financial "
     "and market data), and the cross-cutting Security, Identity and "
     "Governance services (Entra SSO, RBAC, security and compliance "
     "controls, hybrid cloud / AI runtime, AWS PrivateLink, CloudWatch, "
     "X-Ray, KMS, MFA, and Bedrock Guardrails)."),
    ("LANDSCAPE_IMAGE", (
        NEXTGEN_RESEARCH_AGENT_SVG,
        "Figure. CSL Research Agent — next-generation reference architecture "
        "(rendered from docs/CSL_Arch.drawio.svg).",
    )),
    ("PARA",
     "Three properties of this reference are worth highlighting for "
     "stakeholders. First, the Research Agent is one specialist within a "
     "CSL-owned orchestration layer — the Eugene Knowledge Graph remains "
     "the authoritative structured source, but the architecture admits "
     "additional specialists (PubMed, SEC, ClinicalTrials, ChEMBL, and "
     "future modalities) without re-platforming. Second, all "
     "service-to-service connectivity is mediated through the AgentCore "
     "Gateway — a single audit boundary for every agent action. Third, "
     "governance is unified: Bedrock Guardrails, customer-level data "
     "isolation, and contractual no-training commitments apply uniformly "
     "across every specialist, regardless of which underlying LLM is "
     "selected."),

    ("SECTION", "15.3  Key Shifts From the Current State"),
    ("BULLETS", [
        "Single agent → Supervisor + five specialists (Eugene, Research, "
        "PubMed, SEC, ClinicalTrials, Synthesis). Domain-optimised models "
        "and tool sets.",
        "External LLM APIs → AWS Bedrock as the primary LLM runtime, with "
        "Anthropic as fallback. Data residency stays inside the AWS "
        "partition.",
        "File-based sessions → AgentCore Memory (managed) or DynamoDB / "
        "ElastiCache. Durability and horizontal scale.",
        "Graph-only retrieval → Graph + Bedrock Knowledge Base + Milvus + "
        "SharePoint / Confluence / eRooms. Eugene becomes the authoritative "
        "structured source; unstructured CSL knowledge is retrieved via "
        "Bedrock KB; deal-room artefacts via controlled-access policies.",
        "Basic logging → AgentCore Observability + CloudWatch + X-Ray. "
        "Distributed tracing, structured logs, and metrics with unified "
        "alerting.",
        "12 MCP tools → 16+ tools spanning PubMed, SEC EDGAR, "
        "ClinicalTrials, ChEMBL, plus the existing Eugene tool set.",
        "Implicit governance → Bedrock Guardrails, AWS PrivateLink, KMS, "
        "MFA, and 21 CFR Part 11-grade audit logging baked into every "
        "agent action.",
    ]),

    ("SECTION", "15.4  Specialist Agent Topology"),
    ("TABLE", [
        ["Agent",            "Responsibility",                          "Tools",                       "Model"],
        ["Supervisor",       "Intent routing, response synthesis",       "classify_intent, route_to_agent", "Claude Sonnet"],
        ["Eugene Agent",     "KG queries, relationship traversal",       "12 Eugene MCP tools",            "Claude Sonnet"],
        ["Research Agent",   "Free-text research synthesis",             "search_kb, summarise",           "Claude Sonnet"],
        ["PubMed Agent",     "Literature, citations",                    "search_pubmed, get_article",     "GPT-4.1-mini"],
        ["SEC Agent",        "Filings, M&A, financials",                 "search_sec, get_filing",         "GPT-4.1-mini"],
        ["Trials Agent",     "Trial discovery, protocol",                "search_trials, get_protocol",    "GPT-4.1-mini"],
        ["Synthesis Agent",  "Cross-source aggregation",                 "All read tools",                 "Claude Sonnet"],
    ]),

    ("CHAPTER", "16.  Four-Phase Roadmap"),

    ("SECTION", "16.1  Phasing"),
    ("TABLE", [
        ["Phase",                       "Weeks",   "Outcomes"],
        ["1. Foundation Fixes",         "1 – 4",
         "All CRITICAL + HIGH findings resolved; structured logging; deep "
         "/health; rate limiting live."],
        ["2. Session & Observability",  "5 – 8",
         "FileSessionManager replaced; OpenTelemetry + X-Ray; PII / PHI "
         "middleware; Neo4j S3 backups; first UI cohort delivered."],
        ["3. Multi-Agent & New Tools",  "9 – 12",
         "Supervisor + specialist topology; PubMed / SEC / Trials agents; "
         "Bedrock as primary LLM; UI cohort 2 delivered."],
        ["4. Vector Search & Audit",    "13 +",
         "Bedrock Knowledge Base for unstructured KB; freshness tracking; "
         "explainability lineage API; UI cohort 3 + accessibility audit."],
    ]),

    ("SECTION", "16.2  Quick Wins versus Strategic Items"),
    ("TABLE", [
        ["Category",                  "Findings",                                           "Effort"],
        ["Quick Wins (0.5 – 1 day)",
         "SEC-01, AGT-01, AGT-02, AGT-03, AGT-04, AGT-05, SEC-02, DB-01, "
         "DB-02, DB-03, OBS-04, GRAPH-01",
         "≈ 8 days"],
        ["Strategic (2 – 5 days)",
         "SEC-03, SEC-04, SEC-05, OBS-01, OBS-02, OBS-03, AGT-06, GRAPH-02",
         "≈ 23 days"],
    ]),

    ("CHAPTER", "17.  User-Experience Enhancement Programme"),

    ("PARA",
     "Fifteen concrete enhancements are sized for delivery inside Phases 2 "
     "and 3. They retain the strengths of the current Streamlit chat surface "
     "and complete the Next.js v2 implementation that is already underway."),

    ("BULLETS", [
        "Conversation snapshot export (JSON / Markdown / PDF).",
        "Citation and evidence drilldown panel with lineage API.",
        "Graph mini-map and zoom controls on the canvas.",
        "Tool-call timeline rendered as a per-turn Gantt.",
        "Role-based tool hints (read-only / admin-only / PII-risky).",
        "System-prompt templates: Default Biomedical, Patent Analyst, "
        "Clinical Trialist, Competitive Intelligence.",
        "Evidence drilldown with graph expansion to show cited paths.",
        "Share and collaborative export with read-only short links.",
        "Accessibility overhaul (WCAG 2.2 AA).",
        "Keyboard shortcuts (Cmd+K, Cmd+N, Cmd+E, Cmd+?).",
        "Light / dark theme toggle synchronised across canvas.",
        "Mobile-responsive layout (tablet and phone).",
        "Search history with autocomplete.",
        "Agent-decision lineage UI (\"Why?\" button per turn).",
        "Node-property hover tooltips on the graph canvas.",
    ]),

    ("CHAPTER", "18.  Non-Functional Targets"),

    ("TABLE", [
        ["Dimension",                       "Target"],
        ["Latency P50 (simple query)",       "< 2 seconds"],
        ["Latency P95 (multi-hop)",          "< 10 seconds"],
        ["Concurrent agents",                "100 sustained"],
        ["Throughput per service",           "1,000 req / minute"],
        ["Availability",                     "99.9 % (multi-AZ)"],
        ["Data residency",                   "Within AWS partition end-to-end"],
        ["Audit",                            "Per-decision lineage; "
                                              "21 CFR Part 11-ready"],
        ["Security posture",                 "Zero trust; gateway + service "
                                              "authn / authz"],
        ["Accessibility",                    "WCAG 2.2 AA"],
        ["Mobile experience",                "Functional on tablet and phone"],
    ]),

    ("CHAPTER", "19.  Programme Risks and Mitigations"),

    ("TABLE", [
        ["Risk",                                                       "Likelihood", "Impact",   "Mitigation"],
        ["LLM API rate limit under concurrent load",                   "Medium",     "High",     "Queueing; exponential backoff; cache frequent queries"],
        ["Bedrock service availability in eu-central-1 for Phase 3",    "Low",        "High",     "Cross-region fallback or Anthropic"],
        ["SEC EDGAR / ChEMBL licensing beyond fair-use",                "Medium",     "Medium",   "Procurement workstream in parallel with Phase 3"],
        ["Change management on persona workflows",                     "Medium",     "Medium",   "Internal champions; phased rollout"],
        ["JWT secret compromise",                                      "Low",        "Critical", "Rotation policy; future RS256"],
        ["Neo4j data loss",                                            "Low",        "Critical", "S3 snapshot policy in Phase 2"],
        ["Dependency CVE in 175-package requirements",                  "Medium",     "Medium",   "pip-audit in CI; Dependabot"],
    ]),

    ("CHAPTER", "20.  Recommendation"),

    ("PARA",
     "We recommend proceeding to the four-phase remediation and "
     "next-generation roadmap, with the eight-week Phase 1 + Phase 2 "
     "security and operational backbone as the first commitment. The "
     "platform's architectural strengths — clean DDD layering, "
     "comprehensive ontology, dual-LLM resilience, stateless MCP, "
     "streaming SSE, and parameterised Cypher — mean that hardening work "
     "compounds rather than displaces what already works."),

    ("PARA",
     "With the recommended investment, Eugene transitions from a credible "
     "first-generation internal tool to a strategic CSL asset that "
     "materially shortens BD diligence cycles by synthesising structured "
     "and unstructured intelligence in a single conversational, governed, "
     "auditable surface."),


    # ════════════════════════════════════════════════════════════════════
    # APPENDICES
    # ════════════════════════════════════════════════════════════════════
    ("PART", "Appendices"),

    ("CHAPTER", "Appendix A — Source Documents"),
    ("BULLETS", [
        "EUGENE_PROJECT_VALIDATION_DOCUMENT.md (v1.0, March 2026).",
        "EUGENE_STAGE1_ASSESSMENT_REPORT.pdf (April 2026).",
        "EUGENE_DEVELOPER_GUIDE.md (and the published PDF / DOCX).",
        "CSL_Arch_nextGen.pdf — next-generation architecture proposal.",
        "Supporting: oauth.md, entra_id.md, dns.md, csl_aws.md, "
        "maintenance.md, terraform.md, docker.md, local_dev_setup.md, "
        "ROUTE_DEEP_DIVE.md, EUGENE_PROJECT_EVALUATION.pdf, "
        "EUGENE_TECHNICAL_RECOMMENDATIONS.pdf.",
    ]),

    ("CHAPTER", "Appendix B — Glossary"),
    ("TABLE", [
        ["Term",        "Meaning"],
        ["AgentCore",   "AWS Bedrock managed services for agent runtime, memory, gateway, observability"],
        ["ALB",         "Application Load Balancer (AWS)"],
        ["APOC",        "Awesome Procedures On Cypher (Neo4j plugin library)"],
        ["DDD",         "Domain-Driven Design"],
        ["ECR / ECS",   "Elastic Container Registry / Service (AWS)"],
        ["GDS",         "Graph Data Science (Neo4j plugin)"],
        ["HS256 / RS256", "Symmetric / asymmetric JWT signing algorithms"],
        ["IaC",         "Infrastructure as Code"],
        ["MCP",         "Model Context Protocol — agent tool surface protocol"],
        ["NCT ID",      "ClinicalTrials.gov trial identifier"],
        ["PMID",        "PubMed unique identifier"],
        ["PrivateLink", "AWS service exposing endpoints inside a VPC"],
        ["RBAC",        "Role-Based Access Control"],
        ["ReAct",       "Reason–Act–Observe agent pattern"],
        ["SSE",         "Server-Sent Events"],
        ["UPN",         "User Principal Name (Entra ID identifier)"],
        ["VPC",         "Virtual Private Cloud (AWS)"],
    ]),
]
