# Eugene Documentation Generation Prompt

> **Usage**: Copy everything below the `--- BEGIN PROMPT ---` line and paste it into a capable LLM (Claude, GPT-4, etc.) along with access to the Eugene codebase. The LLM will generate complete, production-grade documentation for the project.
>
> **Audience**: This prompt produces documentation for three audiences simultaneously: **Developers**, **Architects**, and **Stakeholders**.
>
> **Last Updated**: 2026-03-20

---

## --- BEGIN PROMPT ---

You are a senior technical writer with deep expertise in biomedical software systems, cloud-native architectures, and knowledge graph technologies. Your task is to generate **complete, production-grade documentation** for a project called **Eugene** -- a biomedical knowledge graph and agentic AI platform built for CSL, a global pharmaceutical company.

This documentation must serve **three audiences simultaneously**:

- **Developers**: Engineers writing code, fixing bugs, and extending features. They need file paths, class names, method signatures, configuration keys, Cypher query patterns, and working code examples.
- **Architects**: Tech leads and solution architects making design decisions. They need component diagrams, sequence diagrams, trade-off analysis, pattern catalogs, and technology decision records.
- **Stakeholders**: Product owners, business sponsors, and non-technical managers. They need business-value framing, capability summaries, risk registers, and roadmap context -- no code.

---

## OUTPUT FORMAT INSTRUCTIONS

1. **Format**: GitHub-flavored Markdown with Mermaid diagrams. Every diagram MUST use fenced mermaid code blocks (` ```mermaid `).
2. **Table of Contents**: Generate a fully linked TOC at the top of each major Part (Developer, Architect, Stakeholder). Generate a master TOC at the very beginning linking to all Parts.
3. **Cross-references**: Use markdown anchor links `[Section Title](#section-title)` extensively. When a Developer section references an Architect concept, link to it and vice versa.
4. **Depth calibration**:
   - **Developer sections**: Maximum detail. Include file paths, class names, method signatures, Cypher query patterns, configuration keys, and code snippets.
   - **Architect sections**: Medium-high detail. Include diagrams, decision records, trade-off analysis, and capacity models. Reference code only to demonstrate patterns.
   - **Stakeholder sections**: High-level only. Plain language, business value framing, risk/opportunity language, summary tables. No code. Diagrams simplified.
5. **Diagrams**: Use Mermaid for ALL diagrams. Required types:
   - C4 System Context diagram
   - C4 Container diagram
   - C4 Component diagrams (for each service)
   - Sequence diagrams (auth flow, chat flow, data ingestion flow)
   - ER diagram (knowledge graph schema)
   - Deployment diagram (AWS infrastructure)
   - CI/CD pipeline flowchart
6. **Code examples**: Show real code snippets from the codebase where they illustrate patterns. Use `python` syntax highlighting.
7. **Admonitions**: Use blockquote-style callouts:
   - `> **Note:**` for general information
   - `> **Warning:**` for critical caveats
   - `> **For Architects:**` for architecture-specific context
   - `> **For Developers:**` for implementation details
   - `> **For Stakeholders:**` for business context
8. **Tables**: Use markdown tables liberally for reference material (node types, endpoints, env vars, dependencies, etc.).
9. **File references**: Always use paths relative to the project root (e.g., `src/eugene_ws.py`, not absolute paths).

---

## PROJECT CONTEXT

### What is Eugene?

Eugene is a biomedical knowledge graph and agentic AI platform that integrates drug, disease, gene/protein, clinical trial, patent, PubMed, and organizational data into a Neo4j graph database. An agentic chat interface powered by LLMs allows users to query this knowledge graph conversationally for competitive intelligence on pharmaceutical companies, drug pipelines, clinical trials, and biomedical research.

### Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.13 | Primary language |
| Web Framework | FastAPI | latest | REST API services |
| Validation | Pydantic | 2.8.2 | Data models and validation |
| Graph Database | Neo4j Community Edition | 5.26.9 | Knowledge graph storage |
| Graph Plugins | APOC + GDS | 5.26.1 / 2.13.4 | Graph procedures and algorithms |
| Vector Database | Milvus (via pymilvus) | 2.4.3 | Semantic/vector search |
| LLM - AWS | AWS Bedrock | via langchain-aws | Meta Llama 3.1 70B |
| LLM - OpenAI | OpenAI API | 1.42.0 | GPT-4o |
| LLM - Local | Ollama | 0.3.1 | Local development (llama3.1) |
| LLM Orchestration | LangChain | 0.3.1 | Knowledge extraction pipelines |
| Agent Framework | Strands | latest | Agentic chat (ReAct pattern) |
| Tool Protocol | FastMCP | latest | Model Context Protocol server |
| Agent Evaluation | MLflow | latest | Prompt evaluation and tracing |
| Frontend | Streamlit | latest | Agent chat UI |
| Containers | Docker | latest | Service containerization |
| Orchestration | AWS ECS Fargate | N/A | Container hosting |
| Registry | AWS ECR | N/A | Docker image registry |
| Load Balancer | AWS ALB | N/A | Traffic routing and TLS |
| Storage | AWS S3 | N/A | Data staging and state backend |
| IaC | Terraform | latest | Infrastructure as Code |
| CI/CD | GitLab CI/CD | N/A | Build, test, deploy pipeline |
| Identity | MS Entra ID | N/A | OAuth 2.0 / JWT authentication |
| Embeddings | sentence-transformers | 3.3.0 | Semantic embeddings |
| Embeddings | model2vec | 0.3.2 | Fast embeddings |
| ML | PyTorch | 2.2.2 | ML backend for transformers |
| NLP | BioPython | 1.85 | PubMed data access |
| Graph Analytics | NetworkX | 3.3 | Graph algorithms |
| Secrets | AWS Secrets Manager | via boto3 | Credential management |

### Service Architecture

The system is a **four-tier microservice architecture** with an evaluation sidecar:

```
Users
  |
  v
eugene-agent-ui (Streamlit, port 8501)
  | HTTP POST with Bearer JWT, SSE streaming
  v
eugene-agent-ws (FastAPI + Strands Agent, port 8000, root_path=/agent/api)
  | MCP over streamable HTTP with Bearer JWT
  v
eugene-mcp (FastMCP, port 8000/8443, stateless HTTP transport)
  | HTTP GET/POST with Bearer JWT
  v
eugene_ws (FastAPI, port 8000)
  | Bolt protocol (encrypted)        | pymilvus gRPC
  v                                   v
Neo4j 5.26.9 (port 7687)           Milvus (vector DB)
```

#### Service Details

| Service | Entry Point | Framework | Purpose |
|---------|------------|-----------|---------|
| **eugene_ws** | `src/eugene_ws.py` | FastAPI | Core REST API: 20+ routers for graph queries, search, auth, stats |
| **eugene-agent-ws** | `agents/eugene-agent-ws/src/eugene_chat_ws.py` | FastAPI + Strands | Agentic chat backend with streaming SSE responses |
| **eugene-mcp** | `agents/eugene-mcp/src/eugene_mcp.py` | FastMCP | MCP tool server: 12 tools wrapping eugene_ws endpoints |
| **eugene-agent-ui** | `agents/eugene-agent-ui/src/eugene_agent_ui.py` | Streamlit | Chat frontend with tool selection, conversation management |
| **mlflow-0** | `agents/mlflow-0/src/bedrock_eval.py` | MLflow | Offline prompt evaluation and scoring |

### Directory Structure

```
knowledgeGraph/
├── src/                              # Core application source
│   ├── eugene_ws.py                  # FastAPI entry point (registers all routers)
│   ├── fetch_secrets.py              # AWS Secrets Manager integration
│   ├── helper.py                     # Environment loading helpers
│   ├── annotation/                   # Decorators
│   │   └── timer_annotation.py       #   @log_time performance decorator
│   ├── foundation/                   # PRIMARY DOMAIN: biomedical node search & traversal
│   │   ├── model/                    #   Enums, graph models, drug/patent/pubmed models
│   │   ├── provider/                 #   Business logic: n-hop, path, facts, details, facets
│   │   ├── mapper/                   #   Data transformers: graph, node, patent, pubmed, facts
│   │   ├── conf/                     #   Dependency injection (manual factory functions)
│   │   ├── infra/                    #   Infrastructure layer
│   │   │   ├── db/adapter/           #     20 Neo4j adapter classes
│   │   │   └── embedding/            #     Node embedding providers
│   │   ├── router/                   #   17+ FastAPI routers
│   │   ├── load/                     #   File/checkpoint loaders
│   │   └── writer/                   #   Output writers (TSV, export)
│   ├── organization/                 # Organization name resolution & disambiguation
│   │   ├── model/                    #   OrganizationResolution, enums
│   │   ├── provider/                 #   Multi-pass merge orchestrators
│   │   ├── analyzer/                 #   LLM-based organization analysis
│   │   ├── mapper/, conf/, infra/, router/, load/, writer/
│   │   └── ...
│   ├── graph/                        # Knowledge extraction & graph analytics
│   │   ├── model/                    #   Entity, Relationship, Extraction, Summary, Finding
│   │   ├── analyze/                  #   GraphRAG orchestrators
│   │   ├── community/                #   Community detection (Leiden algorithm)
│   │   ├── mapper/, infra/
│   │   └── ...
│   ├── patent/                       # USPTO patent processing
│   │   ├── model/, provider/, mapper/, conf/, infra/
│   │   └── ...
│   ├── pubmed/                       # PubMed article processing
│   │   ├── model/, provider/, mapper/, conf/, infra/
│   │   └── ...
│   ├── tpp/                          # Target Product Profiles
│   │   ├── model/, provider/, mapper/, conf/
│   │   └── ...
│   ├── centree/                      # Centree therapeutic area projects
│   │   ├── model/, provider/, mapper/, conf/, infra/, load/
│   │   └── ...
│   ├── clinicaltrail/                # Clinical trial data integration
│   │   └── mapper/                   #   XML/JSON response parsers
│   ├── document/                     # Document parsing & analysis
│   │   ├── parser/                   #   PDF, directory parsers
│   │   ├── analyzer/                 #   LLM-based summarization & extraction
│   │   └── load/                     #   Stored triples/summaries loaders
│   ├── infra/                        # Cross-cutting infrastructure
│   │   ├── llm/                      #   LlmFactory (Ollama, Bedrock, OpenAI)
│   │   │   ├── llm_factory.py        #     Singleton LLM instances
│   │   │   ├── prompt/               #     Prompt templates
│   │   │   ├── callback/             #     LLM callbacks
│   │   │   └── analyzer/             #     Goal analysis with concurrent LLM
│   │   ├── embedding/                #   EmbeddingProvider, SemanticSearch, Merger
│   │   ├── util/                     #   File utilities, path hashing
│   │   └── db/                       #   GraphDbConnectionFactory (Neo4j, Kuzu)
│   ├── router/                       # Shared routing & authentication
│   │   ├── auth/                     #   Entra ID + Eugene JWT auth
│   │   │   ├── auth.py              #     get_current_user dependency
│   │   │   ├── auth_router.py       #     /login, /auth/whoami, /auth/callback
│   │   │   ├── entra_id_jwts.py     #     Entra ID token handling
│   │   │   ├── eugene_jwts.py       #     Eugene JWT issuance/validation
│   │   │   ├── roles.py             #     USER_ROLE_MAP, DEFAULT_ROLES
│   │   │   ├── conf.py              #     MSAL app configuration
│   │   │   └── const.py             #     Auth constants
│   │   ├── root_router.py
│   │   ├── health_router.py
│   │   └── release_notes_router.py
│   ├── stats/                        # Database statistics
│   │   ├── model/, router/
│   │   └── ...
│   ├── util/                         # General utilities
│   └── [~25 CLI scripts]            # Data ingestion, analysis, export pipelines
│       ├── download_pubmed.py, download_patents.py, download_clinicaltrail.py
│       ├── analyze.py, analyze_organizations.py, analyze_tpps.py
│       ├── ingest_organizations.py, ingest_drug_aliases.py, ingest_centree_projects.py
│       ├── store_triples.py, store_summaries.py, train_for_search.py
│       ├── export_organizations.py, export_patent_ids.py
│       ├── cypher_query.py, graph_query.py, query_patents.py
│       └── [cleanup, fix, convert, link, lookup scripts]
│
├── agents/                           # Agent sub-projects (each self-contained)
│   ├── eugene-agent-ui/              # Streamlit chat frontend
│   │   └── src/eugene_agent_ui.py
│   ├── eugene-agent-ws/              # FastAPI + Strands agent backend
│   │   └── src/
│   │       ├── eugene_chat_ws.py     #   App entry point
│   │       ├── query/
│   │       │   ├── agent/eugene_data_agent.py  # Strands Agent (core)
│   │       │   ├── router/chat_query_agent_router.py  # /query, /query/stream
│   │       │   ├── model/            #   Request/response/metrics models
│   │       │   ├── util/             #   Validation, response unwrap, debug
│   │       │   ├── infra/llm/        #   LlmFactory (OpenAI model)
│   │       │   └── conf/             #   Configuration factories
│   │       └── router/
│   │           └── auth/             #   JWT auth (HS256), allowlist
│   ├── eugene-mcp/                   # FastMCP tool server
│   │   └── src/
│   │       ├── eugene_mcp.py         #   MCP server entry point
│   │       ├── tools/                #   7 tool modules, 12 tools total
│   │       │   ├── eugene_identity_tools.py
│   │       │   ├── eugene_fetch_tools.py
│   │       │   ├── eugene_node_tools.py
│   │       │   ├── eugene_drug_tools.py
│   │       │   ├── eugene_fact_tools.py
│   │       │   ├── eugene_graph_tools.py
│   │       │   └── eugene_organization_tools.py
│   │       ├── resources/            #   MCP resources
│   │       ├── auth/verifier.py      #   JWT verification
│   │       ├── health/               #   Health route
│   │       └── util/                 #   Request helpers, registration
│   └── mlflow-0/                     # MLflow evaluation framework
│       └── src/
│           ├── bedrock_eval.py       #   Bedrock evaluation entry
│           ├── openai_eval.py        #   OpenAI evaluation entry
│           ├── agent/                #   OrganizationAgent
│           ├── evaluate/             #   Evaluation runners + custom scorers
│           ├── dataset/              #   Test dataset management
│           ├── prompt/               #   Prompt registry (org resolution, verification, on-topic)
│           └── conf/                 #   MLflow + LLM configuration
│
├── infrastructure/                   # Terraform for AIA (prod) AWS
│   ├── modules/
│   │   ├── eugene-containers/        #   ECR repositories
│   │   ├── eugene-ec2/               #   EC2 instance + EBS volumes
│   │   ├── eugene-ecs-database/      #   Neo4j in ECS (alternative)
│   │   └── eugene-services/          #   ECS services, ALB, CloudWatch
│   └── environments/
│       ├── qa-services/              #   QA env service config
│       ├── qa-database/              #   QA env database config
│       └── qa-ec2/                   #   QA env EC2 config
│
├── difflabs/                         # Terraform + Docker for difflabs (dev) AWS
│   ├── iac/
│   │   ├── eugene-containers/        #   ECR setup
│   │   ├── eugene-services/          #   ECS services, SQS, training tasks
│   │   ├── eugene-database/          #   Neo4j ECS cluster
│   │   └── eugene-loadbalancer/      #   ALB + networking
│   └── containers/                   # Docker images (difflabs-specific)
│       ├── eugene_ws/, eugene_agent_ws/, eugene_agent_ui/
│       ├── eugene_mcp/, eugene_neo4j_ce/
│       └── patent_search_trainer/
│
├── containers/                       # Docker images for AIA environment
│   ├── eugene_ws/Dockerfile          #   python:3.13-slim + AWS CLI
│   ├── eugene_neo4j_ce/Dockerfile    #   Neo4j 5.26.9 + APOC + GDS
│   ├── patent_search_trainer/Dockerfile
│   ├── eugene_api_canaries/Dockerfile
│   └── eugene_bastion/Dockerfile
│
├── tests/                            # pytest test suite
│   ├── data/                         #   JSON fixtures
│   │   ├── organization/             #     Request/response/checkpoint data
│   │   ├── load/entity/              #     Entity fixtures (protein, drug, etc.)
│   │   ├── load/relationship/        #     Relationship fixtures
│   │   ├── triples.json              #     Knowledge graph test triples
│   │   └── community-summary.txt     #     Community analysis fixture
│   └── conftest.py files             #   Distributed across domain packages
│
├── eugene/                           # Database setup & saved queries
│   ├── saved_queries/                #   50+ Cypher queries
│   │   ├── graphsage/                #     Link prediction, embeddings
│   │   ├── fastrp/                   #     Fast Random Projection
│   │   ├── node_similarity/          #     Node similarity algorithms
│   │   ├── drug_repurposing/         #     Disease-drug discovery
│   │   ├── pubmed/, tpp/             #     Domain-specific queries
│   │   ├── label_propagation/        #     Label propagation algo
│   │   └── general/                  #     DB management (count, cleanup, etc.)
│   ├── README.md                     #   Database installation guide
│   └── MACHINE_SETUP.md             #   EC2 setup guide
│
├── api-canaries/                     # API health monitoring
│   └── src/                          #   Canary runners for health/stats/search
│
├── bin/                              # Utility scripts
│   ├── docker/                       #   Build, tag, push, compose scripts
│   ├── pre-commit                    #   Git hook: terraform validate + black + pytest
│   └── ...
│
├── docs/                             # Existing documentation
│   ├── oauth.md, dns.md, entra_id.md, docker.md, terraform.md
│   ├── folders.md, maintenance.md, local_dev_setup.md, git.md
│   └── ...
│
├── .gitlab-ci.yml                    # Main CI/CD pipeline
├── .gitlab/ci/                       # Pipeline sub-configs
│   ├── docker.yml                    #   Container build/push
│   ├── terraform-ec2.yml             #   EC2 infrastructure
│   ├── terraform-services.yml        #   ECS service infrastructure
│   ├── mr-qa.yml                     #   QA merge request scanning
│   └── mr-main.yml                   #   Main merge request scanning
├── .pytest.ini                       # pytest config (parallel, coverage)
├── .coveragerc                       # Coverage exclusions
├── pyproject.toml                    # Project metadata
├── requirements.txt                  # 176 Python dependencies
└── README.md                         # Project entry point
```

### Knowledge Graph Data Model

#### Node Types (from `src/foundation/model/foundational_node_enum.py`)

| Enum Value | Neo4j Label | Domain | Description |
|-----------|-------------|--------|-------------|
| ANATOMY | Anatomy | Foundation | Anatomical structures |
| BIOLOGICAL_PROCESS | BiologicalProcess | Foundation | Biological processes |
| CELLULAR_COMPONENT | CellularComponent | Foundation | Cell components |
| CLINICAL_TRIAL | ClinicalTrial | Foundation | Clinical trial records |
| COLLABORATOR | Collaborator | ClinicalTrial | Trial collaborators |
| CONDITION | Condition | ClinicalTrial | Trial conditions |
| DISEASE | Disease | Foundation | Disease entities |
| DRUG | Drug | Foundation | Drug compounds |
| EFFECT_PHENOTYPE | EffectPhenotype | Foundation | Drug effects/phenotypes |
| EXPOSURE | Exposure | Foundation | Chemical exposures |
| FUNDER_TYPE | FunderType | ClinicalTrial | Trial funder types |
| GENE_PROTEIN | Gene/Protein | Foundation | Genes and proteins |
| INTERVENTION | Intervention | ClinicalTrial | Trial interventions |
| MOLECULAR_FUNCTION | MolecularFunction | Foundation | Molecular functions |
| PATHWAY | Pathway | Foundation | Biological pathways |
| PATENT | Patent | Patent | Patent records |
| PHASE | Phase | ClinicalTrial | Trial phases |
| PRIMARY_OUTCOME_MEASURE | PrimaryOutcomeMeasure | ClinicalTrial | Primary outcomes |
| SECONDARY_OUTCOME_MEASURE | SecondaryOutcomeMeasure | ClinicalTrial | Secondary outcomes |
| SPONSOR | Sponsor | ClinicalTrial | Trial sponsors |
| DRUG_PRODUCT | DrugProduct | Drug | Drug product names |
| DRUG_SYNONYM | DrugSynonym | Drug | Drug synonyms |
| APPROVED_PATENT | ApprovedPatent | Patent | Approved patents |
| PATENT_APPLICATION | PatentApplication | Patent | USPTO applications |
| ORGANIZATION | Organization | Organization | Company entities |
| RESEARCH | Research | Organization | Research activities |
| INVESTIGATORS | Investigators | ClinicalTrial | Trial investigators |
| GRAPHRAG_SUMMARY | GraphragSummary | Graph | Community summaries |
| GRAPHRAG_SUMMARY_FINDING | GraphragSummaryFinding | Graph | Summary findings |
| USPTO_APPLICATION | UsptoApplication | Patent | USPTO applications |
| USPTO_PGPUB | UsptoPgpub | Patent | USPTO publications |
| CSL_TPP | CslTpp | TPP | Target Product Profiles |
| CSL_TPP_QUESTION | CslTppQuestion | TPP | TPP questions |
| PUBMED_DOCUMENT | PubmedDocument | PubMed | PubMed articles |
| PUBMED_SUMMARY | PubmedSummary | PubMed | Article summaries |
| PUBMED_SUMMARY_FINDING | PubmedSummaryFinding | PubMed | Summary findings |

#### Relationship Types (from `src/foundation/model/foundational_relationship_enum.py`)

| Enum Value | Source -> Target | Description |
|-----------|-----------------|-------------|
| OFF_LABEL_USE | Drug -> Disease | Off-label drug usage |
| ANATOMY_PROTEIN_ABSENT | Anatomy -> Protein | Protein absent in anatomy |
| ANATOMY_PROTEIN_PRESENT | Anatomy -> Protein | Protein present in anatomy |
| BIOPROCESS_BIOPROCESS | BiologicalProcess -> BiologicalProcess | Process-process relation |
| CELLCOMP_CELLCOMP | CellularComponent -> CellularComponent | Component hierarchy |
| CONTRAINDICATION | Drug -> Disease | Drug contraindication |
| DISEASE_DISEASE | Disease -> Disease | Disease relationships |
| DISEASE_PHENOTYPE_NEGATIVE | Disease -> EffectPhenotype | Negative phenotype |
| DISEASE_PHENOTYPE_POSITIVE | Disease -> EffectPhenotype | Positive phenotype |
| DISEASE_PROTEIN | Disease -> Protein | Disease-protein association |
| DRUG_DRUG | Drug -> Drug | Drug-drug interaction |
| DRUG_EFFECT | Drug -> EffectPhenotype | Drug effect |
| DRUG_PROTEIN | Drug -> Protein | Drug-protein binding |
| EXPOSURE_DISEASE | Exposure -> Disease | Exposure-disease link |
| INDICATION | Drug -> Disease | Approved indication |
| MOLFUNC_MOLFUNC | MolecularFunction -> MolecularFunction | Function hierarchy |
| PATHWAY_PATHWAY | Pathway -> Pathway | Pathway relationships |
| PATHWAY_PROTEIN | Pathway -> Protein | Pathway-protein membership |
| PROTEIN_PROTEIN | Protein -> Protein | Protein-protein interaction |
| HAS_DRUG_ALIAS | Drug -> DrugSynonym/DrugProduct | Drug alias linkage |
| DISCLOSED_IN | Drug -> Patent | Drug disclosed in patent |
| SUPPORTS_PATENT_APPLICATION | Drug -> PatentApplication | Drug supports application |
| PATENT_APP_TARGET | PatentApplication -> Gene/Protein | Patent application targets |
| FEATURED_IN | Drug -> PubmedDocument | Drug featured in article |
| ANALYZED_IN | Drug -> PubmedSummary | Drug analyzed in summary |
| EVALUATED_IN | Drug -> ClinicalTrial | Drug evaluated in trial |
| HAS_PUBLICATION | Patent -> UsptoPgpub | Patent has publication |

### Authentication Architecture

#### Authentication Flow

1. User visits `/login` on `eugene_ws`
2. **Local development**: `ENVIRONMENT=local` triggers `issue_local_development_eugene_token_with_roles()` which issues a dev JWT directly
3. **Production**: User is redirected to Microsoft Entra ID for OAuth Authorization Code flow
4. Entra callback at `/auth/callback` validates the Entra ID token (RS256), then calls `entra_token_to_eugene_token()` to issue a Eugene JWT (HS256)
5. Eugene JWT claims: `tid` (tenant ID), `sub` (subject), `roles`, `upn` (user principal name), `name`, `preferred_username`, `oid` (object ID), `iss` (issuer), `aud` (audience), `exp`, `iat`
6. Roles loaded from `USER_ROLE_MAP` in `src/router/auth/roles.py` with `DEFAULT_ROLES` fallback
7. Token propagation: UI sends Bearer token -> agent-ws validates JWT + checks allowlist -> passes token to MCP client -> MCP validates with `eugene_jwt_verifier()` -> MCP passes token to eugene_ws API calls

#### Key Auth Files
- `src/router/auth/auth.py` -- `get_current_user()` FastAPI dependency
- `src/router/auth/auth_router.py` -- `/login`, `/auth/whoami`, `/auth/callback`
- `src/router/auth/entra_id_jwts.py` -- Entra ID (RS256) token validation
- `src/router/auth/eugene_jwts.py` -- Eugene JWT (HS256) issuance and validation
- `src/router/auth/roles.py` -- Role definitions and user-role mapping
- `src/router/auth/conf.py` -- MSAL configuration
- `src/router/auth/const.py` -- Auth environment variable constants
- `agents/eugene-agent-ws/src/router/auth/` -- Agent service auth (JWT + allowlist)
- `agents/eugene-mcp/src/auth/verifier.py` -- MCP server JWT verification

### Design Patterns (with file references)

| Pattern | Where Used | Key Files |
|---------|-----------|-----------|
| **Domain-Driven Design** | Every domain package | Each follows: `model/ -> provider/ -> conf/ -> mapper/ -> infra/ -> router/` |
| **Hexagonal Architecture** | Infrastructure isolation | `src/foundation/infra/db/adapter/` (20 Neo4j adapters) isolated from `provider/` |
| **Factory Pattern** | LLM and DB creation | `src/infra/llm/llm_factory.py` (singleton), `src/infra/db/` (GraphDbConnectionFactory) |
| **Adapter Pattern** | Database access | 20 classes in `src/foundation/infra/db/adapter/` |
| **Mapper Pattern** | Data transformation | `mapper/` directories in each domain package |
| **Provider Pattern** | Business logic | `provider/` directories in each domain |
| **Orchestrator Pattern** | Multi-step workflows | `OrganizationResolutionMultipassMergeOrchestrator`, `FoundationalFactsOrchestrator`, etc. |
| **Decorator Pattern** | Cross-cutting concerns | `@log_time` in `src/annotation/timer_annotation.py` |
| **Manual DI** | Dependency wiring | `conf/conf.py` files in each domain (factory functions, no framework) |
| **ReAct Agent Pattern** | Agentic chat | `agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py` via Strands |

### CI/CD Pipeline (`.gitlab-ci.yml`)

| Stage | Purpose | Branch Rules |
|-------|---------|--------------|
| echo | Debug (commit, branch info) | All branches |
| scan | Checkov security scanning | MR to qa/main |
| docker | Build + push to ECR | qa, main, feature/* |
| terraform-ec2 | Validate + plan EC2 infra | qa, main |
| apply-ec2 | Apply EC2 changes (manual) | qa, main |
| terraform-services | Validate + plan ECS services | qa, main |
| apply-services | Apply service changes (manual) | qa, main |

- **Branch strategy**: `main` -> production, `qa` -> QA, `feature/*` -> docker build only
- **AWS auth**: GitLab OIDC token -> AWS IAM role assumption
- **Sub-pipelines**: `.gitlab/ci/docker.yml`, `.gitlab/ci/terraform-ec2.yml`, `.gitlab/ci/terraform-services.yml`

### Testing Strategy

- **Framework**: pytest with `pytest-xdist` (parallel, `-n 2`), `pytest-cov`, `pytest-mock`, `pytest-dotenv`
- **Config**: `.pytest.ini` -- minversion 7.0, `--cov=src`, `log_cli=true`
- **Test data**: JSON fixtures in `tests/data/` (organization, entity, relationship, patent, triples)
- **Markers**: `@pytest.mark.serial` (non-parallel), `@pytest.mark.integration`
- **Convention**: Colocated tests (e.g., `graph_mapper.py` alongside `graph_mapper_test.py`)
- **Coverage**: `.coveragerc` excludes `*_test.py` and `conftest.py`

### Deployment Architecture

| Environment | AWS Account | Region | Access | Deployment Method |
|-------------|-------------|--------|--------|-------------------|
| difflabs (dev) | 087084717211 | us-east-1 | Internal, Cyberark + SSO | Manual from desktop |
| AIA (prod target) | 010928221940 | eu-central-1 | GitLab CI/CD | Automated pipeline |

Both environments run: ECS Fargate tasks behind ALB, ECR for images, S3 for state/data, Neo4j on EC2 (or ECS).

**Container images** (7 total):
1. `eugene_ws` -- Core API (python:3.13-slim)
2. `eugene_agent_ws` -- Agent backend (python:3.13-slim)
3. `eugene_agent_ui` -- Streamlit frontend (python:3.13-slim)
4. `eugene_mcp` -- MCP server (python:3.13-slim)
5. `eugene_neo4j_ce` -- Neo4j 5.26.9 + APOC + GDS
6. `patent_search_trainer` -- ML model trainer (python:3.12-slim)
7. `eugene_api_canaries` -- Health monitoring

### Key Dependencies (from `requirements.txt`)

176 packages total. Key ones:
- `neo4j==5.25.0` -- Neo4j Python driver
- `langchain==0.3.1`, `langchain-aws==0.2.1`, `langchain-openai==0.2.1`, `langchain-ollama==0.2.0`
- `pymilvus==2.4.3`, `milvus-lite==2.4.10` -- Vector database
- `pydantic==2.8.2` -- Data validation
- `sentence-transformers==3.3.0`, `model2vec==0.3.2` -- Embeddings
- `torch==2.2.2` -- ML backend
- `biopython==1.85` -- PubMed/bioinformatics
- `networkx==3.3` -- Graph algorithms
- `boto3==1.34.162` -- AWS SDK
- `PyMuPDF==1.25.3` -- PDF parsing
- `gensim==4.3.3` -- NLP/topic modeling

---

## DOCUMENTATION STRUCTURE TO GENERATE

Generate the following Parts and Sections. Each section must be comprehensive, self-contained, and cross-referenced.

---

# PART 0: MASTER TABLE OF CONTENTS

Generate a fully linked master TOC covering all Parts and their Sections. Include page-like numbering (1.1, 1.2, 2.1, etc.).

---

# PART 1: STAKEHOLDER DOCUMENTATION

**Audience**: Product owners, business sponsors, CSL managers. No code. Business language only.

## 1.1 Executive Summary
- What Eugene is and what problems it solves for CSL
- Key capabilities: competitive intelligence on drugs/diseases/patents/trials, conversational AI querying, organization disambiguation
- Current state, maturity, and deployment status
- One-paragraph summary per service component

## 1.2 System Capabilities Overview
- Table of capabilities mapped to business value (columns: Capability | What It Does | Business Value | Data Source)
- Data domains covered: drugs, diseases, genes/proteins, clinical trials, patents, PubMed articles, organizations, TPPs
- Example questions users can ask via the chat agent (reference the Streamlit UI suggestion pills):
  - "What are the drug aliases for Biogen?"
  - "What organization assets does CSL have?"
  - "What are the relationships between Drug X and Disease Y?"
  - "Find clinical trials related to hemophilia"
  - "Search PubMed for recent studies on immunoglobulins"

## 1.3 Architecture at a Glance
- Simplified C4 system context diagram (Mermaid) -- show Eugene as a single box with external actors: Users, Entra ID, AWS, data sources
- One paragraph per component (UI, Agent, Tools, API, Database) -- no technical jargon
- Simple data flow diagram showing: User asks question -> AI Agent reasons -> Tools query database -> Answer returned

## 1.4 Security and Compliance Summary
- Authentication: Microsoft Entra ID SSO (same credentials as other CSL systems)
- Role-based access control: public vs. confidential data roles
- Data residency: AWS eu-central-1 (production), us-east-1 (development)
- Encryption: JWT tokens for service-to-service auth, TLS for data in transit, encrypted database connections
- Compliance posture table with known gaps

## 1.5 Operational Status and Risk Register
- Current deployment: difflabs (active), AIA (pending ECS IAM fix)
- Risk/mitigation table format:

| Risk | Impact | Likelihood | Mitigation | Status |
|------|--------|-----------|------------|--------|
| AIA deployment blocked by IAM | No prod environment | High | Escalate IAM ticket | Open |
| Neo4j CE limitations | No RBAC, no clustering | Medium | Evaluate Enterprise license | Planned |
| Network isolation in difflabs | Cannot reach OpenAI/Claude from ECS | High | Route via proxy or use Bedrock | Workaround |
| SSL cert expiry | Service outage | Low | Calendar alert for renewal | Monitored |

## 1.6 Roadmap Implications
- Adding proprietary/confidential data: requires Neo4j Enterprise (RBAC), role-based filtering in adapters, updated auth roles
- Expanding AI capabilities: additional MCP data sources (PubMed, ClinicalTrials, ChEMBL, bioRxiv MCPs -- infrastructure ready but not deployed)
- Scaling: current architecture supports horizontal scaling via ECS task count
- Cost implications: LLM API costs (Bedrock/OpenAI), Neo4j Enterprise licensing, ECS compute

---

# PART 2: ARCHITECT DOCUMENTATION

**Audience**: Solution architects, tech leads, senior engineers. Diagrams, patterns, trade-offs.

## 2.1 System Context Diagram (C4 Level 1)
- Mermaid C4 diagram showing:
  - Eugene system boundary
  - External actors: CSL Users, Microsoft Entra ID
  - External data sources: USPTO (patents), PubMed/NCBI, ClinicalTrials.gov, Centree
  - AWS cloud services
  - Include data flow arrows with labels

## 2.2 Container Diagram (C4 Level 2)
- Mermaid diagram showing all 6 containers:
  1. eugene-agent-ui (Streamlit, port 8501)
  2. eugene-agent-ws (FastAPI, port 8000)
  3. eugene-mcp (FastMCP, port 8000/8443)
  4. eugene_ws (FastAPI, port 8000)
  5. Neo4j (Bolt 7687, HTTP 7474)
  6. Milvus (gRPC)
- Show: protocols, ports, auth boundaries, ALB routing

## 2.3 Component Diagrams (C4 Level 3)

### 2.3.1 eugene_ws Components
Show all 20+ routers registered in `src/eugene_ws.py`, grouped by domain:
- Auth: auth_router
- System: root, health, release_notes, stats
- Foundation: count, label, node_id_lookup, node_details, n_hop, search_path, facet, similarity, facts
- Drug: drug_alias_search
- Patent: patent_search, patent_count
- PubMed: pubmed_search, pubmed_count
- Organization: organization_search
Show the adapter layer beneath routers and the database connections.

### 2.3.2 eugene-agent-ws Components
Show: FastAPI app -> auth middleware -> query router -> EugeneDataAgent (Strands) -> MCP client -> tool execution
Include: SlidingWindowConversationManager, FileSessionManager, streaming SSE response pipeline

### 2.3.3 eugene-mcp Components
Show: FastMCP server -> JWT auth middleware -> 7 tool modules (12 tools) -> HTTP client -> eugene_ws API
List each tool with its target eugene_ws endpoint

## 2.4 Design Patterns and Architectural Decisions

### 2.4.1 Domain-Driven Design (DDD)
- Explain the `model/ -> provider/ -> conf/ -> mapper/ -> infra/ -> router/` package structure
- How each domain (foundation, organization, graph, patent, pubmed, tpp, centree, clinicaltrail, document) follows this consistently
- Benefits: domain isolation, team scalability, independent evolution
- Reference `docs/folders.md` for the original DDD documentation

### 2.4.2 Hexagonal Architecture
- Adapter isolation: `infra/db/adapter/` classes encapsulate all Neo4j Cypher queries
- Port pattern: Providers depend on adapter abstractions, not direct database calls
- Benefits: testability (mock adapters in tests), database swappability (Neo4j and Kuzu both supported via `GraphDbConnectionFactory`)
- Diagram: hexagon with domain core, adapter ports, and external systems

### 2.4.3 Factory and Dependency Injection
- Manual DI via `conf/conf.py` factory functions -- no DI framework
- `LlmFactory` (`src/infra/llm/llm_factory.py`): singleton pattern for LLM instances (Ollama, Bedrock, OpenAI)
- `GraphDbConnectionFactory` (`src/infra/db/`): creates Neo4j and Kuzu connections
- Trade-off analysis: simplicity and explicitness vs. scalability of manual DI
- When to consider a framework: if provider count exceeds ~50 or circular dependencies emerge

### 2.4.4 Agent Architecture (Strands + MCP)
- Sequence diagram: User prompt -> EugeneDataAgent -> Strands ReAct loop -> MCP tool call -> eugene_ws API -> Neo4j -> response bubbles back
- Conversation management: SlidingWindowConversationManager (window_size=32, per_turn=3)
- Session persistence: FileSessionManager (file-based; note: S3SessionManager needed for multi-instance)
- Tool discovery: MCP client loads tool schemas from FastMCP server at connection time
- Token propagation: JWT passed through all tiers via Authorization header

### 2.4.5 Technology Decision Records (ADRs)
For each, document: **Context**, **Decision**, **Consequences**, **Alternatives Considered**.

1. **Neo4j CE vs. Enterprise**: Chose CE for cost; consequence: no RBAC, no clustering, no online backup
2. **Strands vs. LangGraph for agents**: Chose Strands for simplicity and native MCP support
3. **FastMCP for tool protocol**: Chose for Python-native MCP implementation with auth middleware support
4. **Manual DI vs. framework**: Chose manual for transparency; trade-off: more boilerplate in conf.py
5. **HS256 vs. RS256 for internal tokens**: HS256 for Eugene-to-Eugene communication (simpler, shared secret); RS256 for Entra ID (public key verification)
6. **Microservices vs. monolith**: Chose microservices (4 services) for independent scaling and deployment of agent vs. API tiers

## 2.5 Data Architecture

### 2.5.1 Knowledge Graph Schema
- Mermaid ER diagram showing all node types (from table above) with relationship types connecting them
- Explain the multi-domain graph: foundation nodes as core, with patent/pubmed/organization/tpp nodes extending the graph
- Property model: nodes have `name`, `value`, `description`, `embedding` (where applicable), domain-specific properties

### 2.5.2 Vector Search Architecture
- Milvus collections for semantic search (summaries, embeddings)
- Embedding generation pipeline: text -> sentence-transformers or model2vec -> vector
- Dual storage: embeddings stored in both Neo4j (for graph-native similarity) and Milvus (for pure vector search)
- Query pattern: user query -> embed -> Milvus ANN search -> retrieve Neo4j node IDs -> enrich from graph

### 2.5.3 Data Ingestion Pipelines
For each pipeline, show a flow diagram:
1. **Foundation data**: initial biomedical graph load (drugs, diseases, genes, proteins, pathways)
2. **Drug aliases**: DrugBank product names and synonyms -> `ingest_drug_aliases.py` -> Neo4j
3. **Organizations**: name list -> LLM analysis (`analyze_organizations.py`) -> multi-pass merge -> Neo4j ingest
4. **Patents**: USPTO download -> JSON conversion -> text extraction -> Neo4j linking
5. **Clinical trials**: ClinicalTrials.gov API -> XML/JSON parse -> Neo4j
6. **PubMed**: PubMed search -> PDF download -> LLM extraction -> Neo4j + embeddings
7. **TPPs**: PPTX parsing -> structured extraction -> Neo4j + embedding training
8. **Centree projects**: CSV export -> mapping -> Neo4j ingest
9. **Knowledge extraction**: PDF -> parse -> LLM entity/relationship extraction -> store triples

### 2.5.4 Graph Analytics
- Community detection: Leiden algorithm via Neo4j GDS
- Graph summarization: LLM-based community reports (`src/graph/analyze/`)
- Similarity algorithms: GraphSage, FastRP, cosine/Jaccard node similarity (saved queries in `eugene/saved_queries/`)
- Drug repurposing queries: `eugene/saved_queries/drug_repurposing/`

## 2.6 Security Architecture
- Full sequence diagram: OAuth flow from browser to Entra ID to Eugene JWT issuance
- JWT lifecycle diagram: issuance, validation at each tier, expiry
- Service-to-service auth: all internal calls carry Bearer JWT
- Role model: `USER_ROLE_MAP` with `public_read` and `confidential_read` roles
- Known gap: roles are defined but not yet enforced for data-level filtering (all data treated as public)
- Network security: internal ALB (no public access), VPC subnets, security groups

## 2.7 Infrastructure Architecture
- Mermaid deployment diagram showing:
  - VPC with public/private subnets
  - ALB (TLS termination, path-based routing)
  - ECS Fargate tasks (eugene_ws, eugene_agent_ws, eugene_agent_ui, eugene_mcp)
  - EC2 instance (Neo4j + data volumes)
  - ECR repositories
  - S3 buckets (terraform state, data staging)
  - Secrets Manager
- Two-environment comparison table (difflabs vs AIA)
- Terraform module dependency graph

## 2.8 CI/CD Architecture
- Mermaid flowchart: push -> echo -> scan (Checkov) -> docker build/push -> terraform plan -> manual apply
- Branch-to-environment mapping
- OIDC token flow: GitLab -> AWS IAM role
- Docker build matrix: which images for which environments
- Merge request gates: Checkov HIGH/CRITICAL failures block merge

## 2.9 Scalability and Performance Considerations
- Neo4j query optimization: pagination in adapters, `MAX_RESULT_COUNT = 10_000`, targeted Cypher queries
- `@log_time` decorator for method-level performance monitoring
- Agent conversation window: `SlidingWindowConversationManager(window_size=32, per_turn=3)` to limit context
- ECS auto-scaling: task count adjustable per service
- Known bottleneck: single Neo4j CE instance (no clustering, no read replicas)
- Milvus: horizontal scaling capabilities for vector search

## 2.10 Resilience and Error Handling
- JWT validation: structured error hierarchy (401 expired, 401 invalid, 500 unexpected)
- Agent streaming: try/catch with error event yielding (graceful degradation)
- MCP tool errors: caught and returned as tool error responses to agent
- HTTP clients: `httpx` with `verify=False` for self-signed certs, 30s timeout for MCP, 120s for agent
- No circuit breaker or retry pattern currently implemented

## 2.11 Monitoring and Observability
- Health endpoints: `/health` on every service
- API canaries: `api-canaries/` project runs periodic health/stats/search checks
- Logging: Python `logging` module, `INFO` level, `log_cli` in pytest
- `@log_time` decorator for performance timing
- `AgentMetrics` dataclass: tracks `total_tokens`, `execution_time`, `tools_used` per agent invocation
- Gap: no centralized metrics/tracing (CloudWatch logs only)

---

# PART 3: DEVELOPER DOCUMENTATION

**Audience**: Engineers writing and maintaining code. Maximum detail. File paths, code examples, method signatures.

## 3.1 Development Environment Setup

### 3.1.1 Prerequisites
- Python 3.13 (3.12 for patent_search_trainer)
- Docker (with registry mirror for Zscaler VPN environments)
- AWS CLI v2
- Neo4j Desktop 2 (for local development)
- Terraform (for infrastructure changes)
- Git with pre-commit hook (`bin/pre-commit`)

### 3.1.2 Project Setup
- Clone, virtual environment creation, pip install from `requirements.txt`
- Agent sub-projects have separate `requirements.txt` files
- `.env` configuration (reference env.template files in agents/)
- Key environment variables:
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
  - `OPENAI_API_KEY`
  - `ENVIRONMENT=local` (enables dev auth bypass)
  - `EUGENE_TENANT_ID`, `EUGENE_CLIENT_ID`, `EUGENE_CLIENT_SECRET`
  - `HF_HUB_CACHE` (HuggingFace model cache path)

### 3.1.3 Running Services Locally
- `eugene_ws`: `uvicorn eugene_ws:app --app-dir src --reload` (port 8000)
- `eugene-agent-ws`: `uvicorn eugene_chat_ws:app --app-dir agents/eugene-agent-ws/src --reload` (port 8000)
- `eugene-mcp`: `python agents/eugene-mcp/src/eugene_mcp.py --host 127.0.0.1 --port 8443`
- `eugene-agent-ui`: `streamlit run agents/eugene-agent-ui/src/eugene_agent_ui.py` (port 8501)
- Running tests: `pytest` (uses `.pytest.ini` config)

## 3.2 Code Organization and Conventions

### 3.2.1 DDD Package Structure
Every domain follows: `model/ -> provider/ -> conf/ -> mapper/ -> infra/ -> router/`
- `model/` -- Pydantic models, dataclasses, enums (domain objects)
- `provider/` -- Business logic, orchestrators (coordinates adapters and mappers)
- `conf/` -- Factory functions for dependency injection (wires adapters, mappers, providers)
- `mapper/` -- Data transformation (Neo4j records -> domain models, domain models -> API responses)
- `infra/` -- Infrastructure adapters (Neo4j queries, embedding generation)
- `router/` -- FastAPI routers (HTTP endpoints, request/response handling)

### 3.2.2 File Naming Conventions
| Suffix | Purpose | Example |
|--------|---------|---------|
| `*_adapter.py` | Database access layer | `neo4j_foundational_n_hop_adapter.py` |
| `*_provider.py` | Business logic | `foundational_n_hop_provider.py` |
| `*_orchestrator.py` | Multi-step workflow | `organization_resolution_orchestrator.py` |
| `*_mapper.py` | Data transformation | `graph_mapper.py` |
| `*_router.py` | FastAPI endpoint | `foundation_n_hop_router.py` |
| `*_factory.py` | Object creation | `llm_factory.py` |
| `*_enum.py` | Enumerations | `foundational_node_enum.py` |
| `*_test.py` | Test file (colocated) | `graph_mapper_test.py` |
| `conftest.py` | pytest fixtures | Distributed across packages |

### 3.2.3 Code Style
- Formatter: `black` (line-length 88)
- Linter: `ruff`, `pylint`, `isort`
- Pre-commit hook: `bin/pre-commit` runs `terraform validate`, `black`, `pytest`

## 3.3 API Reference

### 3.3.1 eugene_ws Endpoints (Core API)
Document every router registered in `src/eugene_ws.py`. For each endpoint, include: HTTP method, path, parameters, request body (if any), response model, authentication required.

#### Auth Endpoints (`src/router/auth/auth_router.py`)
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/login` | Initiates OAuth flow or issues dev token | No |
| GET | `/auth/whoami` | Returns current user info from JWT | Yes |
| GET | `/auth/callback` | Entra ID OAuth callback | No (redirect) |

#### System Endpoints
| Method | Path | Router File | Description |
|--------|------|-------------|-------------|
| GET | `/` | `src/router/root_router.py` | Welcome message |
| GET | `/health` | `src/router/health_router.py` | Health check |
| GET | `/release-notes` | `src/router/release_notes_router.py` | Release notes |
| GET | `/stats` | `src/stats/router/database_stats_router.py` | Database statistics |

#### Foundation Domain Endpoints (`src/foundation/router/`)
| Method | Path | Router File | Description |
|--------|------|-------------|-------------|
| GET | `/count/{label}` | `foundation_count_router.py` | Count nodes by label |
| GET | `/labels/{label}` | `foundation_label_router.py` | Get nodes by label (paginated) |
| GET | `/node-id-lookup/{id}` | `foundation_node_id_lookup_router.py` | Lookup node by ID |
| GET | `/node-details/{id}` | `foundation_node_details_router.py` | Node details with relationships |
| POST | `/n-hop` | `foundation_n_hop_router.py` | N-hop subgraph traversal |
| POST | `/search-path` | `foundation_search_path_router.py` | Shortest path between nodes |
| POST | `/facets` | `foundation_facet_router.py` | Faceted search |
| POST | `/similarity` | `foundation_similarity_router.py` | Node similarity search |
| GET | `/facts/{node_id}` | `foundation_facts_router.py` | Facts (relationships) for a node |
| GET | `/drugs/aliases/{name}` | `drug_alias_search_router.py` | Drug alias search |
| GET | `/patents/drugs` | `patent_search_router.py` | Patent search by drug |
| GET | `/patents/clinicaltrials` | `patent_search_router.py` | Patent search by trial |
| GET | `/patents/count` | `patent_count_router.py` | Patent count |
| GET | `/pubmed/drugs` | `pubmed_search_router.py` | PubMed search by drug |
| GET | `/pubmed/clinicaltrials` | `pubmed_search_router.py` | PubMed search by trial |
| GET | `/pubmed/count` | `pubmed_count_router.py` | PubMed article count |

#### Organization Endpoints (`src/organization/router/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/organizations/{name}` | Search organizations by name pattern |
| GET | `/organizations/assets/{org_id}` | Get organization assets (drugs, trials, IP) |

### 3.3.2 eugene-agent-ws Endpoints (`agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/api/query` | Synchronous chat query |
| POST | `/agent/api/query/stream` | Streaming chat query (SSE) |

**Request model** (`ChatQueryRequest`):
```python
class ChatQueryRequest(BaseModel):
    prompt: str              # User's question (max 2048 chars)
    conversation_id: str     # UUID for conversation continuity
    include_tools: list[str] # Tool sources: ["eugene", "pubmed", "http"]
```

**Response model** (`ChatQueryResponse`):
```python
class ChatQueryResponse(BaseModel):
    prompt: str             # Original prompt
    message: str            # Agent's response
    conversation_id: str    # Conversation UUID
    is_complete: bool       # Whether response is final
```

### 3.3.3 eugene-mcp Tools (`agents/eugene-mcp/src/tools/`)

| Tool | Module | Parameters | Description |
|------|--------|-----------|-------------|
| `fetch_identity` | `eugene_identity_tools.py` | none | Current user identity from JWT |
| `fetch_by_label` | `eugene_fetch_tools.py` | `label`, `page`, `page_size` | List nodes by type (drug, disease, etc.) |
| `fetch_similar` | `eugene_fetch_tools.py` | `label`, `values` | Find similar nodes by relationships |
| `lookup_node_by_value` | `eugene_node_tools.py` | `value`, `fuzzy_match` | Find node by name |
| `fetch_node_details` | `eugene_node_tools.py` | `ids` (list) | Get detailed info for node IDs |
| `fetch_drug_aliases` | `eugene_drug_tools.py` | `drug_name` | List drug aliases, indications, contraindications |
| `fetch_facts` | `eugene_fact_tools.py` | `node_id` | Fetch relationships for a node (paginated) |
| `fetch_node_relationships` | `eugene_graph_tools.py` | `node_id`, `n_hop` | Get 1-hop or 2-hop relationships |
| `fetch_paths` | `eugene_graph_tools.py` | `start_id`, `end_id`, `n_hop` | Find paths between two nodes |
| `has_reachable_path` | `eugene_graph_tools.py` | `start_id`, `end_id`, `n_hop` | Check if path exists |
| `find_organization_names` | `eugene_organization_tools.py` | `name_pattern` | Find organizations matching pattern |
| `find_organization_assets` | `eugene_organization_tools.py` | `organization_id` | Get org's drugs, trials, IP |

## 3.4 Data Model Reference

### 3.4.1 Node Types
Full table from `src/foundation/model/foundational_node_enum.py` (see Project Context above for complete list).

### 3.4.2 Relationship Types
Full table from `src/foundation/model/foundational_relationship_enum.py` (see Project Context above for complete list).

### 3.4.3 Key Domain Models
Document the primary model classes with their fields:

**Foundation models** (`src/foundation/model/`):
- `graph/graph.py` -- Graph, Node, Edge models for visualization
- `drug/` -- Drug alias and search result models
- `patent/` -- Patent search result models
- `pubmed/` -- PubMed search result models
- `generic_node_details.py` -- Node details with relationships
- `shortest_paths.py` -- Path query results
- `reachability.py` -- Reachability check results

**Graph models** (`src/graph/model/`):
- `entity.py` -- Entity (type, value, description)
- `relationship.py` -- Relationship (source, target, relation)
- `extraction.py` -- Extraction (list of entities + relationships)
- `summary.py` -- Summary (text + list of findings)
- `finding.py` -- Finding (individual insight from analysis)
- `community_report.py` -- Community detection report

**Organization models** (`src/organization/model/`):
- `OrganizationResolution` -- Resolved org with parent, subsidiaries, acquisitions, spelling variations
- `CanonicalOrganizationKey` -- Canonical identifier
- Enums for relationship types and node types

## 3.5 Database Adapter Reference

Document each adapter in `src/foundation/infra/db/adapter/`:

| Adapter Class | File | Purpose |
|---------------|------|---------|
| `Neo4jFoundationalNodeCountAdapter` | `neo4j_foundational_node_count_adapter.py` | Count nodes by label |
| `Neo4jFoundationalNodeAdapter` | `neo4j_foundational_node_adapter.py` | Basic node CRUD |
| `Neo4jFoundationalNodeDetailsAdapter` | `neo4j_foundational_node_details_adapter.py` | Node details with relationships |
| `Neo4jFoundationalOneHopAdapter` | `neo4j_foundational_one_hop_adapter.py` | Single-hop graph traversal |
| `Neo4jFoundationalNHopAdapter` | `neo4j_foundational_n_hop_adapter.py` | N-hop subgraph traversal |
| `Neo4jFoundationalPathAdapter` | `neo4j_foundational_path_adapter.py` | Shortest path queries |
| `Neo4jFoundationalFacetAdapter` | `neo4j_foundational_facet_adapter.py` | Faceted search |
| `Neo4jFoundationalSimilarityAdapter` | `neo4j_foundational_similarity_adapter.py` | Node similarity queries |
| `Neo4jPatentQueryAdapter` | `neo4j_patent_query_adapter.py` | Patent full-text search |
| `Neo4jPatentExportAdapter` | `neo4j_patent_export_adapter.py` | Patent data export |
| `Neo4jPubmedQueryAdapter` | `neo4j_pubmed_query_adapter.py` | PubMed article search |
| `Neo4jPubmedCountAdapter` | `neo4j_pubmed_count_adapter.py` | PubMed count queries |
| `Neo4jDrugAliasesAdapter` | `neo4j_drug_aliases_adapter.py` | Drug alias management |
| `Neo4jProjectGraphAdapter` | `neo4j_project_graph_adapter.py` | Project graph operations |
| `Neo4jProjectSimilarityGraphAdapter` | `neo4j_project_similarity_graph_adapter.py` | Project similarity |
| `Neo4jOnhotEncodingAdapter` | `neo4j_onehot_encoding_adapter.py` | One-hot encoding operations |
| `Neo4jTrainEmbeddingsAdapter` | `neo4j_train_embeddings_adapter.py` | Embedding training |
| `Neo4jListEmbeddingsAdapter` | `neo4j_list_embeddings_adapter.py` | Embedding listing |
| `Neo4jMissingNodeIndexEmbeddingAdapter` | `neo4j_missing_node_index_embedding_adapter.py` | Missing embedding detection |

For each adapter, show: key method signatures, example Cypher query patterns, return types.

## 3.6 Provider and Orchestrator Reference

Document key providers with their purpose, dependencies, and method signatures:

- `FoundationalNHopProvider` -- N-hop subgraph traversal with pagination and MAX_RESULT_COUNT enforcement
- `FoundationalPathProvider` -- Shortest path queries between nodes
- `FoundationalFactsOrchestrator` -- Composes n-hop adapter + facts mapper for rich node context
- `FoundationalNodeDetailsProvider` -- Detailed node information retrieval
- `DrugAliasesUpdateOrchestrator` -- Drug alias ingestion from product names and synonyms
- `OrganizationResolutionMultipassMergeOrchestrator` -- LLM-based multi-pass organization disambiguation
- `OrganizationResolutionMergeBySpellingProvider` -- Merge orgs by spelling similarity
- `OrganizationResolutionMergeByKeyProvider` -- Merge orgs by canonical key
- `OrganizationIngestOrchestrator` -- Ingest resolved organizations into Neo4j
- `PubmedOrchestrator` -- PubMed search and download coordination
- `TppOrchestrator` -- TPP parsing and graph linking

## 3.7 LLM Integration Reference

### LlmFactory (`src/infra/llm/llm_factory.py`)
Singleton factory creating LLM instances:
- `local_instance()` -- ChatOllama (localhost:11434, llama3.1)
- `bedrock_instance()` -- ChatBedrock (meta.llama3-1-70b-instruct-v1:0, temp 0.6, max_tokens 32k)
- `openai_instance()` -- ChatOpenAI (chatgpt-4o-latest)

### LlmChatFactory (`agents/mlflow-0/src/infra/llm/llm_chat_factory.py`)
Similar factory for chat-specific LLM instances used in evaluation.

### Prompt Templates (`src/infra/llm/prompt/`)
Document available prompt templates and their structure.

### Agent LLM Configuration
- `agents/eugene-agent-ws/src/query/infra/llm/llm_factory.py` -- OpenAI gpt-4.1-mini for agent
- System prompt in `eugene_data_agent.py`: "You are an agent tasked with helping investigate biomedical companies..."

## 3.8 Embedding and Vector Search

### Providers (`src/infra/embedding/`)
- `EmbeddingProvider` -- Base embedding functionality
- `SemanticSearchEmbeddingProvider` -- Semantic search embeddings using sentence-transformers
- `EmbeddingMerger` -- Combining multiple embedding sources

### Foundation Embedding (`src/foundation/infra/embedding/`)
- `FoundationalNodeEmbeddingProvider` -- Generates embeddings for graph nodes
- HuggingFace model caching via `HF_HUB_CACHE` environment variable

### Vector Storage
- Neo4j: node property `embedding` for graph-native similarity
- Milvus: `pymilvus` client for ANN search via `src/graph/infra/db/milvus_adapter.py`

## 3.9 CLI Scripts Reference

For each script in `src/`, document: purpose, usage, input requirements, output, dependencies.

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `download_pubmed.py` | Download PubMed PDFs | Search terms | PDF files to disk |
| `download_patents.py` | Download USPTO patents | Patent IDs | JSON files to disk |
| `download_clinicaltrail.py` | Download clinical trials | Search criteria | JSON/XML data |
| `analyze.py` | Analyze documents for KG extraction | Document directory | Extracted entities/relationships |
| `analyze_organizations.py` | LLM-based org disambiguation | Organization names | Resolution checkpoints |
| `analyze_tpps.py` | Parse TPP PPTX files | PPTX directory | Structured TPP data |
| `ingest_organizations.py` | Load org resolutions into Neo4j | Checkpoint files | Neo4j nodes/relationships |
| `ingest_drug_aliases.py` | Add drug synonyms/products | Drug data files | Neo4j relationships |
| `ingest_centree_projects.py` | Load Centree projects | CSV files | Neo4j nodes |
| `store_triples.py` | Store entities/relationships | Extracted triples | Neo4j nodes/relationships |
| `store_summaries.py` | Store summaries in Milvus | Summary data | Milvus vectors |
| `train_for_search.py` | Train search embeddings | Node data | Indexed embeddings |
| `link_pubmed_articles.py` | Link articles to nodes | PubMed data | Neo4j relationships |
| `export_organizations.py` | Export org mappings | Neo4j query | CSV files |
| `export_patent_ids.py` | Export patent relationships | Neo4j query | CSV files |
| `cypher_query.py` | Natural language to Cypher | User question | Cypher query + results |
| `graph_query.py` | Q&A over knowledge graph | User question | LLM-generated answer |
| `query_patents.py` | Semantic patent search | Search query | Ranked patents |
| `cleanup_organizations.py` | Clean org checkpoints | Checkpoint files | Filtered checkpoints |
| `fix_foundational_nodes.py` | Update node embeddings | Node IDs | Updated Neo4j nodes |
| `fix_pubmed_articles.py` | Fix missing article fields | PubMed node IDs | Updated Neo4j nodes |
| `convert_patents.py` | USPTO JSON to text | JSON files | Text files |
| `convert_centree_projects.py` | Centree JSON to CSV | JSON export | CSV files |
| `visualize_embeddings.py` | Generate TSV for visualization | Embeddings | TSV files |
| `fetch_secrets.py` | Fetch AWS Secrets Manager | Secret name | .env file |

## 3.10 Authentication Implementation Guide

Detailed file-by-file walkthrough of `src/router/auth/`:

1. **`auth.py`** -- `get_current_user()` FastAPI dependency: extracts Bearer token, validates JWT, returns user dict
2. **`auth_router.py`** -- Three endpoints: `/login` (initiates OAuth or issues dev token), `/auth/whoami` (returns user info), `/auth/callback` (Entra ID redirect handler)
3. **`entra_id_jwts.py`** -- Entra ID RS256 token decoding, JWKS key retrieval, claim validation
4. **`eugene_jwts.py`** -- Eugene JWT HS256 issuance (`issue_eugene_token()`) and validation (`validate_eugene_access_token()`), claim structure
5. **`roles.py`** -- `USER_ROLE_MAP` dict mapping user principal names to role lists, `DEFAULT_ROLES` fallback
6. **`conf.py`** -- MSAL ConfidentialClientApplication configuration, redirect URI, scopes
7. **`const.py`** -- Environment variable names for all auth configuration

Include code examples showing how to:
- Add a new user to the role map
- Add a new role
- Protect a new endpoint with authentication

## 3.11 Testing Guide

### Running Tests
```bash
# Run all tests (parallel, with coverage)
pytest

# Run specific domain tests
pytest src/foundation/mapper/

# Run with verbose output
pytest -v

# Run only serial tests
pytest -m serial

# Run only integration tests
pytest -m integration
```

### Configuration (`.pytest.ini`)
```ini
[pytest]
minversion = 7.0
addopts = -n 2 --cov=src --cov-report=lcov:reports/coverage/lcov.info
log_cli = true
log_cli_level = INFO
env_files = .env
markers =
    serial: Run test serially (not in parallel)
    integration: Integration tests
```

### Writing Tests
- Place test files alongside source files: `foo.py` + `foo_test.py`
- Use `conftest.py` for shared fixtures in each package
- Use `pytest-mock` (`mocker` fixture) for mocking
- Use JSON fixtures from `tests/data/` for test inputs
- All tests must pass with `pytest -n 2` (parallel safe)

## 3.12 Docker and Container Guide

### Dockerfile Pattern (`containers/eugene_ws/Dockerfile`)
```
python:3.13-slim base
-> Install system deps (gcc, AWS CLI)
-> Pre-cache HuggingFace models
-> Copy requirements.txt, pip install
-> Copy source code
-> Create non-root user "eugene"
-> EXPOSE 8000
-> CMD uvicorn
```

### Container Inventory

| Image | Base | Port | Purpose |
|-------|------|------|---------|
| eugene_ws | python:3.13-slim | 8000 | Core API |
| eugene_agent_ws | python:3.13-slim | 8000 | Agent backend |
| eugene_agent_ui | python:3.13-slim | 8501 | Streamlit UI |
| eugene_mcp | python:3.13-slim | 8000 | MCP server |
| eugene_neo4j_ce | neo4j:5.26.9 | 7687/7474 | Graph database |
| patent_search_trainer | python:3.12-slim | N/A | ML training job |
| eugene_api_canaries | python:3.13-slim | N/A | Health monitoring |

### Build and Deploy
```bash
# Login to ECR
bin/docker/ecr/login.sh

# Build and push
bin/docker/ecr/build.sh eugene_ws
bin/docker/ecr/tag.sh eugene_ws
bin/docker/ecr/push.sh eugene_ws
```

### Environment Differences
- **difflabs**: restricted network (Zscaler), local pip mirrors, pre-copied HuggingFace models
- **AIA**: standard internet access, standard pip, HuggingFace download during build

## 3.13 Terraform and Infrastructure Guide

### Module Structure
| Module | Path | Purpose |
|--------|------|---------|
| eugene-containers | `infrastructure/modules/eugene-containers/` | ECR repositories |
| eugene-ec2 | `infrastructure/modules/eugene-ec2/` | EC2 + EBS for Neo4j |
| eugene-ecs-database | `infrastructure/modules/eugene-ecs-database/` | Neo4j in ECS |
| eugene-services | `infrastructure/modules/eugene-services/` | ECS services, ALB, CloudWatch |

### Deployment Steps (difflabs)
```bash
cd difflabs/iac/eugene-services
bin/init-difflabs.sh    # terraform init
bin/plan-difflabs.sh    # terraform plan
bin/apply-difflabs.sh   # terraform apply
```

### Deployment Steps (AIA via CI/CD)
1. Push to `qa` or `main` branch
2. Pipeline runs: scan -> docker -> terraform plan -> manual apply
3. Approve apply stage in GitLab UI

## 3.14 Configuration Reference

Generate a complete table of ALL environment variables across all services:

| Variable | Service | Required | Default | Description |
|----------|---------|----------|---------|-------------|
| `NEO4J_URI` | eugene_ws | Yes | - | Neo4j Bolt URI |
| `NEO4J_USER` | eugene_ws | Yes | - | Neo4j username |
| `NEO4J_PASSWORD` | eugene_ws | Yes | - | Neo4j password |
| `OPENAI_API_KEY` | agent-ws | Yes | - | OpenAI API key |
| `ENVIRONMENT` | eugene_ws | No | `production` | `local` enables dev auth |
| `EUGENE_TENANT_ID` | all | Yes | - | Eugene tenant UUID |
| `EUGENE_CLIENT_ID` | all | Yes | - | Eugene client UUID |
| `EUGENE_CLIENT_SECRET` | all | Yes | - | Eugene JWT signing secret |
| `ENTRA_TENANT_ID` | eugene_ws | Yes | - | MS Entra ID tenant |
| `ENTRA_CLIENT_ID` | eugene_ws | Yes | - | MS Entra app registration |
| `ENTRA_CLIENT_SECRET` | eugene_ws | Yes | - | MS Entra client secret |
| `EUGENE_MCP_SERVER_URL` | agent-ws | Yes | - | MCP server endpoint |
| `EUGENE_API_BASE` | eugene-mcp | Yes | - | Eugene API base URL |
| `EUGENE_AGENT_API_URL` | agent-ui | No | `http://localhost:8000/agent/api/query` | Agent API endpoint |
| `EUGENE_AGENT_ALLOWLIST` | agent-ws | No | - | Comma-separated allowed UPNs |
| `HF_HUB_CACHE` | eugene_ws | No | `~/.cache/huggingface` | HuggingFace model cache |
| ... | ... | ... | ... | Document all remaining vars |

## 3.15 Dependency Management
- Main project: `requirements.txt` (176 packages, pinned versions)
- Agent sub-projects: separate `requirements.txt` per agent
- `pyproject.toml`: project metadata, build system
- Key version constraints: Python >=3.12 <3.14, torch==2.2.2 (CUDA compatibility)

## 3.16 Error Handling Patterns
Document common patterns with code examples:
- JWT validation errors (401 responses)
- Neo4j connection errors
- LLM API errors (timeout, rate limit)
- Agent streaming errors (error event yielding)
- Input validation (`validate_chat_query_request()`: prompt length <2048, special char filtering, UUID format)
- Provider-level enforcement (`MAX_RESULT_COUNT` ValueError)

## 3.17 Saved Cypher Queries Reference
Document categories in `eugene/saved_queries/`:
- `graphsage/` -- Link prediction, graph embeddings
- `fastrp/` -- Fast Random Projection embeddings
- `node_similarity/` -- Cosine/Jaccard similarity
- `vwd_node_similarity/` -- Von Willebrand Disease specific similarity
- `drug_repurposing/` -- Disease-drug relationship discovery
- `pubmed/` -- PubMed-specific queries
- `tpp/` -- TPP-specific queries
- `label_propagation/` -- Label propagation algorithm
- `general/` -- DB management (count nodes, list labels, cleanup, terminate transactions)

## 3.18 Operational Runbooks

### How to Add a New Data Domain
1. Create package under `src/` with DDD structure: `model/`, `provider/`, `conf/`, `mapper/`, `infra/`, `router/`
2. Define models in `model/`
3. Create Neo4j adapter in `infra/db/adapter/`
4. Create mapper in `mapper/`
5. Create provider/orchestrator in `provider/`
6. Wire in `conf/conf.py`
7. Create router in `router/`
8. Register router in `src/eugene_ws.py`
9. Add tests alongside each file

### How to Add a New MCP Tool
1. Create tool function in `agents/eugene-mcp/src/tools/` (new file or existing)
2. Use `@mcp.tool()` decorator with description
3. Register in `agents/eugene-mcp/src/util/register.py` -> `register_tools()`
4. Tool auto-discovered by Strands agent at connection time

### How to Add a New API Endpoint
1. Create router file in appropriate domain's `router/` directory
2. Define endpoint with FastAPI decorators
3. Add authentication dependency (`Depends(get_current_user)`)
4. Register in `src/eugene_ws.py` with `app.include_router()`

### How to Perform Data Ingestion
For each data source, document the step-by-step process:
1. Foundation data load
2. Drug alias ingestion
3. Organization resolution and ingestion
4. Patent download and linking
5. Clinical trial ingestion
6. PubMed article processing
7. TPP processing
8. Centree project import

### How to Deploy to Each Environment
- difflabs: Docker build -> ECR push -> Terraform apply (or ECS force-update)
- AIA: Git push to qa/main -> GitLab pipeline -> approve apply stage

### How to Rotate Secrets
1. Update secret in AWS Secrets Manager
2. Run `fetch_secrets.py` to regenerate .env
3. Restart affected ECS services (force new deployment)

### How to Troubleshoot Common Issues
- Neo4j connection timeout: check security groups, Bolt port 7687
- JWT validation failure: check secret match between services, token expiry
- MCP tool errors: check eugene_ws is running, API base URL correct
- Agent not responding: check OpenAI API key, MCP server URL, conversation session files

---

# PART 4: APPENDICES

## A. Glossary
Define all domain-specific terms:
- **Knowledge Graph**: A graph-structured database representing entities and their relationships
- **MCP (Model Context Protocol)**: Anthropic's protocol for LLM tool integration
- **Strands**: AWS agent framework implementing ReAct pattern
- **FastMCP**: Python library for building MCP servers
- **Neo4j**: Graph database using Cypher query language
- **Milvus**: Open-source vector database for similarity search
- **APOC**: "Awesome Procedures on Cypher" -- Neo4j extension library
- **GDS**: Neo4j Graph Data Science library for graph algorithms
- **GraphSage**: Graph neural network for generating node embeddings
- **FastRP**: Fast Random Projection for node embeddings
- **ReAct**: Reasoning + Acting pattern for LLM agents
- **TPP**: Target Product Profile -- pharmaceutical product specification document
- **Centree**: CSL internal project management system
- **Entra ID**: Microsoft's identity and access management service (formerly Azure AD)
- **JWT**: JSON Web Token for authentication
- **OIDC**: OpenID Connect protocol
- **ECS Fargate**: AWS serverless container orchestration
- **ECR**: AWS Elastic Container Registry
- **ALB**: AWS Application Load Balancer
- **Cypher**: Neo4j's graph query language
- **DDD**: Domain-Driven Design
- **SSE**: Server-Sent Events for streaming responses

## B. File Index
Alphabetical index of all significant files (~200) with one-line descriptions. Group by directory.

## C. Environment Variable Reference
Complete table of ALL environment variables across all services (expanded from Section 3.14).

## D. External Dependencies and Licenses
Table of all 176 Python packages with: name, version, license type, purpose in the project.

## E. Related Documentation Links
| Document | Path | Content |
|----------|------|---------|
| OAuth setup | `docs/oauth.md` | JWT token generation, HS256/RS256 config |
| DNS config | `docs/dns.md` | DNS routing setup |
| Entra ID config | `docs/entra_id.md` | MS Entra ID app registration |
| Docker guide | `docs/docker.md` | Docker build process, registry mirrors |
| Terraform guide | `docs/terraform.md` | IaC usage for both environments |
| Code structure | `docs/folders.md` | DDD package structure explanation |
| Maintenance | `docs/maintenance.md` | Operational maintenance tasks |
| Dev setup | `docs/local_dev_setup.md` | Local development environment |
| Git workflow | `docs/git.md` | Branch strategy, CI/CD pipeline |
| AWS access | `docs/csl_aws.md` | Cyberark and AWS SSO access |
| GraphRAG | `docs/graphrag.md` | GraphRAG experiments (deprecated) |
| Agent demo | `docs/agent_demo.md` | Screenshots of agent capabilities |
| Next steps | `docs/next_steps.md` | Known issues and tech debt |
| Neo4j setup | `eugene/README.md` | Database installation |
| EC2 setup | `eugene/MACHINE_SETUP.md` | EC2 instance setup |

---

## GENERATION INSTRUCTIONS

1. **Generate ALL sections** listed above. Do not skip or summarize any section.
2. **Mermaid diagrams**: Every diagram must use fenced code blocks with the `mermaid` language tag. Required diagrams: C4 system context, C4 container, C4 component (x3 services), auth sequence, chat flow sequence, data ingestion flow, ER diagram, deployment diagram, CI/CD pipeline flowchart.
3. **File paths**: Use exact paths from the project context. All paths are relative to project root.
4. **Inference**: Where you need to infer behavior (e.g., specific Cypher queries), use `> **Inferred:**` callouts.
5. **Single document**: Generate as one continuous markdown document with consistent heading hierarchy: `#` for Parts, `##` for Sections, `###` for Subsections.
6. **Tables**: Use markdown tables for all reference material.
7. **Cross-references**: Link extensively between sections using `[Section Title](#section-title)`.
8. **Completeness**: This document must serve as the single source of truth. Err on the side of more detail.
9. **No placeholders**: Do not use "TBD", "TODO", or "to be documented". If information is unavailable, state what is known and mark gaps with `> **Gap:**` callouts.
10. **Audience tags**: Mark sections with their primary audience using blockquote callouts.

## --- END PROMPT ---
