# L1 → L2 → L3 Agent Architecture Refactoring Plan

Scope: full monorepo (`src/`, `agents/*`, `ingestion/`). Goal: reorganize existing
code into a 3-layer agent architecture **without changing business logic** —
this is a structural/wrapping refactor, not a rewrite. Every existing class,
router, adapter, and Cypher query keeps its current implementation; only the
*calling boundary* changes.

---

## 1. Current Architecture Diagram

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION                                                              │
│  eugene-agent-ui (Streamlit, legacy)   eugene-agent-ui-next (Next.js)      │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │ HTTP (chat prompt, include_tools[])
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ agents/eugene-agent-ws  (FastAPI, "eugene_chat_ws.py")                    │
│  query/router/chat_query_agent_router.py  → POST /query, /query/stream    │
│  query/agent/eugene_data_agent.py         → Strands Agent (ReAct loop)    │
│  query/tools/external_tools.py            → search_pubmed/_europepmc/     │
│                                              _patents_web/_clinical_trials│
│  query/util/intent_classifier.py, connectivity.py, temporal.py            │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │ MCP (streamable-http, JWT)
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ agents/eugene-mcp  (FastMCP server, "eugene_mcp.py")                      │
│  tools/eugene_graph_tools.py, eugene_node_tools.py, eugene_fact_tools.py,  │
│  eugene_drug_tools.py, eugene_organization_tools.py, eugene_vector_tools.py│
│  eugene_stats_tools.py, eugene_identity_tools.py, eugene_fetch_tools.py    │
│  → each tool is an HTTP client (make_eugene_request) to eugene_ws          │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │ HTTPS (Bearer token forwarded)
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ src/eugene_ws.py  (Core FastAPI REST API, "Eugene Core API")               │
│  routers (add_routers): auth, root, health, release_notes, database_stats,│
│  foundation.* (count/label/node_id/node_details/n_hop/search_path/facet/  │
│    similarity/drug_alias/patent_search/patent_count/pubmed_search/        │
│    pubmed_count/facts/vector_search/digest),                              │
│  organization.router.organization_search_router                           │
│                                                                            │
│  Each router → Provider/Orchestrator (src/foundation/provider/*) →         │
│  Adapter (src/foundation/infra/db/adapter/neo4j_*.py) → Cypher → Neo4j     │
│                                                                            │
│  Sibling domains NOT behind eugene_ws routers, invoked only as CLI scripts:│
│   src/patent/*, src/pubmed/*, src/clinicaltrail/*, src/document/*,        │
│   src/graph/* (GraphRAG), src/tpp/*, src/centree/*                        │
│   (download_pubmed.py, download_patents.py, download_clinicaltrail.py,    │
│    analyze.py, store_triples.py, store_summaries.py, ...)                 │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │ bolt://
                                 ▼
                              Neo4j (+ APOC, GDS)

┌───────────────────────────────────────────────────────────────────────────┐
│ DOCUMENT DOMAIN (parallel, separately deployed — see docs/                │
│ FOUNDATION_GRAPH_API_SWAGGER_GUIDE.md and prior document-domain analysis)  │
│                                                                            │
│  ingestion/scheduler/service.py  (APScheduler, FastAPI)                   │
│    → ingestion/src/pipeline/orchestrator.py  (discover via Europe PMC)    │
│    → HTTP POST /ade/ingest  →  agents/eugene-ade/src/ade/api.py           │
│         → ade/pipeline.py → ade/fetch.py, parser.py, layout.py,          │
│           tables.py, verify.py, enrich.py, indexer.py, storage.py (S3)   │
│    → ingestion/src/pipeline/steps/centrality_step.py                     │
│         → pipeline/graph/projection.py, centrality.py  → Neo4j            │
│  Config: agents/eugene-ade/src/pipeline/config/ade-analysis-config.yaml.yml│
│          ingestion/src/pipeline/config/research_areas.yaml                │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ SCOUT DOMAIN (parallel, separately deployed)                              │
│  agents/eugene-scout/src/scout/api.py  → orchestrator.py                  │
│    → collectors/{trials,literature,patents,epo,edgar}.py                 │
│    → scoring.py, dedupe.py, digest.py, duediligence/*  → S3               │
└───────────────────────────────────────────────────────────────────────────┘
```

**Key observations (evidence for the refactor):**

1. **A 3-tier shape already exists informally**: UI → agent-ws (coordinator) →
   mcp (tool executor) → core API (business logic) → Neo4j. The gap is that
   this chain only covers the Foundation/Organization/Graph/Vector domains
   reachable through `eugene_ws.py` routers. Patent, PubMed, Clinical Trial,
   Document (legacy GraphRAG), and TPP domains have real business logic
   (`src/patent`, `src/pubmed`, `src/clinicaltrail`, `src/document`, `src/tpp`)
   but are **not** wrapped as MCP tools — they are only invoked as standalone
   CLI scripts (`download_patents.py`, `download_pubmed.py`,
   `download_clinicaltrail.py`, `analyze.py`, `store_triples.py`, ...).
2. **Document domain (ADE/ingestion)** and **Scout domain** are each
   self-contained L2+L3 stacks (scheduler/orchestrator = L2, pipeline
   stages/collectors = L3) that do not yet report through the agent-ws L2
   coordinator; they run on their own schedule and are invoked only by REST
   or cron.
3. **No single L1 concept exists today.** `eugene-agent-ui-next` is a
   UI, `chat_query_agent_router.py` is an HTTP entry point, and
   `intent_classifier.py` / `ToolRequestEnum` / `include_tools` in
   `ChatQueryRequest` are the closest things to "agent selection" — they
   already function as a proto-L1 selector but are embedded inside the L2
   FastAPI service rather than being a distinct layer.

---

## 2. Proposed L1 → L2 → L3 Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│ L1 — AGENT (User Interaction Layer)                                     │
│                                                                          │
│  Entry points (existing, reclassified — no code moves required):        │
│   • agents/eugene-agent-ui-next (Next.js UI)                            │
│   • agents/eugene-agent-ui (Streamlit UI, legacy)                       │
│   • agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py  │
│       POST /query, POST /query/stream                                   │
│   • ingestion/scheduler/service.py  (non-chat trigger surface:           │
│       POST /ingest/run, /ingest/dry-run, /ingest/centrality)             │
│   • agents/eugene-scout/src/scout/api.py (trigger surface)              │
│                                                                          │
│  New thin L1 module (wraps existing code, adds nothing to business      │
│  logic):  agents/eugene-agent-ws/src/l1/                                 │
│   - session_context.py   wraps ChatQueryRequest + conversation_id        │
│     (existing FileSessionManager / SlidingWindowConversationManager)     │
│   - agent_selector.py    wraps existing intent_classifier.py +           │
│     ToolRequestEnum + include_tools resolution (_add_default_tools)      │
│   - config_loader.py     loads ade-analysis-config.yaml.yml +            │
│     research_areas.yaml + scout/config.py as declarative L1 manifests    │
│   - prompt_context.py    wraps build_source_directive /                  │
│     _all_sources_directive / build_temporal_directive                    │
│                                                                          │
│  Responsibility: authenticate, accept a request (chat prompt, ingest     │
│  trigger, scout trigger), resolve session + conversation state, pick     │
│  which L2 coordinator(s) and tool-set apply, forward to L2. NO business  │
│  logic, no Cypher, no Neo4j/S3 access.                                   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ in-process call / same FastAPI process
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ L2 — COORDINATOR (Orchestration Layer)                                  │
│                                                                          │
│  Existing coordinators, reclassified in place:                          │
│   • agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py          │
│       (Strands Agent — the primary ReAct coordinator; tiered-cascade     │
│        policy in build_source_directive / _all_sources_directive)        │
│   • ingestion/src/pipeline/orchestrator.py  (document sweep coordinator) │
│   • ingestion/scheduler/service.py           (cron + run-lock coordinator)│
│   • agents/eugene-scout/src/scout/orchestrator.py (due-diligence/radar)  │
│   • src/graph/analyze/eugene_graph_summary_orchestrator.py               │
│       (legacy GraphRAG coordinator — reclassified, not rewritten)        │
│   • src/patent/conf/orchestator.py, src/patent/provider/                 │
│       patent_orchestrator.py, src/pubmed/provider/pubmed_orchestrator.py,│
│       src/pubmed/provider/pubmed_fix_orchestrator.py,                    │
│       src/foundation/provider/foundational_facts_orchestrator.py,        │
│       src/foundation/provider/drug_aliases_update_orchestrator.py,       │
│       src/foundation/provider/foundational_node_fix_orchestrator.py,     │
│       src/tpp/provider/tpp_patent_train_orchestrator.py,                 │
│       src/tpp/provider/tpp_search_orchestrator.py                        │
│                                                                          │
│  New thin L2 module (routing glue only):                                 │
│   agents/eugene-agent-ws/src/l2/agent_router.py                          │
│     - maps ToolRequestEnum → {mcp tool-set | external_tools set |        │
│       document-domain client | scout-domain client}                     │
│     - centralizes error handling already present in                     │
│       chat_query_agent_router.py (try/except, hard caps                 │
│       _AGENT_MAX_ITERATIONS / _HARD_TOOL_CALL_BUDGET /                  │
│       _MAX_DUPLICATE_TOOL_CALLS) — moved, not rewritten                  │
│     - state: FileSessionManager / SlidingWindowConversationManager        │
│       (existing) + AgentMetrics (existing query/model/agent_metrics.py)  │
│                                                                          │
│  Responsibility: given an L1-resolved request + tool-set, run the       │
│  ReAct loop / cron job / batch sweep, decide which L3 agent(s)/tools to  │
│  call, aggregate results, apply retry/error policy, persist              │
│  session/run state. NO direct Neo4j/S3 driver access — always through    │
│  L3 tool calls.                                                          │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ tool invocation (MCP call / in-process function / HTTP)
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ L3 — EXECUTOR AGENTS (Tools — one per business domain)                 │
│                                                                          │
│  L3.Foundation   agents/eugene-mcp/src/tools/eugene_graph_tools.py,      │
│                  eugene_node_tools.py, eugene_fact_tools.py,             │
│                  eugene_drug_tools.py, eugene_fetch_tools.py,            │
│                  eugene_identity_tools.py, eugene_stats_tools.py         │
│                  → HTTP → src/foundation/router/*.py → provider/adapter  │
│  L3.Organization eugene_organization_tools.py                            │
│                  → src/organization/router/*.py → adapter                │
│  L3.Vector/Search eugene_vector_tools.py                                 │
│                  → src/foundation/router/vector_search_router.py         │
│                  → src/foundation/vector/{fusion_search_service,intent,  │
│                    rerank_service,corpus_ingest_service}.py              │
│  L3.Patent       NEW WRAPPER (see §4) around                             │
│                  src/patent/provider/patent_orchestrator.py,             │
│                  src/patent/application/*, src/patent/pgpub/*            │
│                  + already-agent-facing search_patents_web               │
│                  (query/tools/external_tools.py)                         │
│                  + src/foundation/router/patent_search_router.py,        │
│                    patent_count_router.py (already REST, needs MCP tool) │
│  L3.PubMed       NEW WRAPPER around src/pubmed/provider/*.py             │
│                  + already-agent-facing search_pubmed / search_europepmc │
│                  + src/foundation/router/pubmed_search_router.py,        │
│                    pubmed_count_router.py                                │
│  L3.ClinicalTrial NEW WRAPPER around                                     │
│                  src/clinicaltrail/provider/clinical_trail_provider.py   │
│                  + already-agent-facing search_clinical_trials            │
│  L3.Document     agents/eugene-ade/src/ade/{api,pipeline,parser,layout,  │
│                  tables,verify,enrich,indexer,storage,fetch,render}.py   │
│                  + ingestion/src/pipeline/{orchestrator,graph/           │
│                    projection,graph/centrality,steps/centrality_step,    │
│                    util/identity}.py                                     │
│                  + legacy: src/document/parse/*, src/document/analyze/*  │
│  L3.Graph/GraphRAG src/graph/analyze/*, src/graph/community/*,           │
│                  src/graph/infra/db/neo4j_graphrag_adapter.py,           │
│                  neo4j_graphrag_linking_adapter.py                       │
│  L3.TPP          src/tpp/provider/*, src/tpp/infra/db/adapter/*          │
│  L3.Scout        agents/eugene-scout/src/scout/collectors/*.py           │
│                  (trials, literature, patents, epo, edgar)               │
│                                                                          │
│  Each L3 tool = a thin, named, single-purpose wrapper function around   │
│  ONE existing business method. No adapter/Cypher/service code changes.  │
│  Every current router/provider/adapter file stays exactly where it is;  │
│  L3 only adds a registration entry (MCP `@tool`, or a Python callable    │
│  registered in a tool registry) that calls the existing function.       │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ HTTP / bolt:// / S3 API
                                 ▼
                     Neo4j (+APOC/GDS)   Milvus   S3 (ADE/Scout artifacts)
```

---

## 3. Agent Mapping Matrix (Module → Agent Layer → Tool)

| Module / File | Layer | Proposed Agent / Tool Name |
|---|---|---|
| `agents/eugene-agent-ui-next`, `agents/eugene-agent-ui` | L1 | `ui.agent-ui-next`, `ui.agent-ui-legacy` |
| `agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py` | L1 | `l1.chat_entrypoint` |
| `agents/eugene-agent-ws/src/query/util/intent_classifier.py` | L1 | `l1.agent_selector` |
| `agents/eugene-agent-ws/src/query/model/tool_request_enum.py`, `chat_query_request.py` | L1 | `l1.session_context` |
| `ingestion/scheduler/service.py` (`/ingest/run`, `/ingest/dry-run`, `/ingest/centrality`) | L1 (trigger) | `l1.ingestion_trigger` |
| `agents/eugene-scout/src/scout/api.py` | L1 (trigger) | `l1.scout_trigger` |
| `agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py` | L2 | `l2.coordinator.chat` |
| `ingestion/src/pipeline/orchestrator.py` | L2 | `l2.coordinator.document_sweep` |
| `agents/eugene-scout/src/scout/orchestrator.py` | L2 | `l2.coordinator.scout_scan` |
| `src/graph/analyze/eugene_graph_summary_orchestrator.py` | L2 | `l2.coordinator.graphrag_summary` |
| `src/patent/conf/orchestator.py`, `patent_orchestrator.py` | L2 | `l2.coordinator.patent_ingest` |
| `src/pubmed/provider/pubmed_orchestrator.py`, `pubmed_fix_orchestrator.py` | L2 | `l2.coordinator.pubmed_ingest` |
| `src/foundation/provider/foundational_facts_orchestrator.py` | L2 | `l2.coordinator.facts` |
| `src/foundation/provider/drug_aliases_update_orchestrator.py` | L2 | `l2.coordinator.drug_alias_refresh` |
| `src/foundation/provider/foundational_node_fix_orchestrator.py` | L2 | `l2.coordinator.node_fix` |
| `src/tpp/provider/tpp_patent_train_orchestrator.py`, `tpp_search_orchestrator.py` | L2 | `l2.coordinator.tpp` |
| `eugene_graph_tools.py` (`fetch_node_relationships`, `fetch_paths`, `has_reachable_path`) | L3 | `l3.foundation.graph` |
| `eugene_node_tools.py` (`lookup_node_by_value`, `fetch_node_details`) | L3 | `l3.foundation.node` |
| `eugene_fact_tools.py` (`fetch_facts`) | L3 | `l3.foundation.facts` |
| `eugene_drug_tools.py` (`fetch_drug_aliases`) | L3 | `l3.foundation.drug_alias` |
| `eugene_fetch_tools.py` (`fetch_by_label`, `fetch_similar`) | L3 | `l3.foundation.label_similarity` |
| `eugene_identity_tools.py` (`fetch_identity`) | L3 | `l3.foundation.identity` |
| `eugene_stats_tools.py` | L3 | `l3.foundation.stats` |
| `eugene_organization_tools.py` | L3 | `l3.organization` |
| `eugene_vector_tools.py` (`search_summaries`, `search_fused`) | L3 | `l3.vector.search` |
| `query/tools/external_tools.py::search_pubmed`, `search_europepmc` | L3 | `l3.pubmed.web` |
| `query/tools/external_tools.py::search_patents_web` | L3 | `l3.patent.web` |
| `query/tools/external_tools.py::search_clinical_trials` | L3 | `l3.clinicaltrial.web` |
| `src/foundation/router/patent_search_router.py`, `patent_count_router.py` + `src/patent/**` | L3 | `l3.patent.graph` (new MCP tool needed) |
| `src/foundation/router/pubmed_search_router.py`, `pubmed_count_router.py` + `src/pubmed/**` | L3 | `l3.pubmed.graph` (new MCP tool needed) |
| `src/clinicaltrail/**` | L3 | `l3.clinicaltrial.graph` (new MCP tool needed) |
| `agents/eugene-ade/src/ade/*.py` | L3 | `l3.document.ade` |
| `ingestion/src/pipeline/graph/projection.py`, `centrality.py`, `steps/centrality_step.py` | L3 | `l3.document.centrality` |
| `src/document/parse/*.py`, `src/document/analyze/*.py` (legacy) | L3 | `l3.document.legacy_parser` |
| `src/graph/community/*`, `src/graph/infra/db/neo4j_graphrag_adapter.py` | L3 | `l3.graphrag` |
| `src/tpp/infra/db/adapter/*.py` | L3 | `l3.tpp` |
| `agents/eugene-scout/src/scout/collectors/{trials,literature,patents,epo,edgar}.py` | L3 | `l3.scout.<collector>` |

---

## 4. Business Function → Tool Mapping (representative, non-exhaustive by design)

Each row = one existing method that becomes one Tool with the same signature and body.

| Existing Function | File | New Tool Name | Notes |
|---|---|---|---|
| `Neo4jFoundationalNHopAdapter.collect_by_start_id_and_end_id` (via `FoundationalNHopProvider`) | `src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py` | `tool.graph.relationship` | Already exposed via `eugene_graph_tools.fetch_node_relationships` |
| `Neo4jFoundationalPathAdapter.find_shortest_path_by_start_id_and_end_id` | `src/foundation/infra/db/adapter/neo4j_foundational_path_adapter.py` | `tool.graph.path` | Already exposed via `eugene_graph_tools.fetch_paths` |
| `Neo4jFoundationalPathAdapter.find_is_reachable_by_start_id_and_end_id` | same | `tool.graph.reachability` | Already exposed via `eugene_graph_tools.has_reachable_path` |
| `FoundationalFactsOrchestrator.find_facts_by_start_id` | `src/foundation/provider/foundational_facts_orchestrator.py` | `tool.graph.facts` | Already exposed via `eugene_fact_tools.fetch_facts` |
| `Neo4jFoundationalNodeAdapter.find_node_id_by_node_name` | `src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py` | `tool.node.find` | Already exposed via `eugene_node_tools.lookup_node_by_value` |
| `Neo4jFoundationalNodeDetailsAdapter.find_node_details_by_node_ids` | `src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py` | `tool.node.details` | Already exposed via `eugene_node_tools.fetch_node_details` |
| `Neo4jFoundationalNodeAdapter.find_by_label` | same | `tool.labels.list` | Already exposed via `eugene_fetch_tools.fetch_by_label` |
| `Neo4jFoundationalNodeCountAdapter.count_all_by_label` | `neo4j_foundational_node_count_adapter.py` | `tool.labels.count` | **Gap**: no MCP tool today; add thin wrapper, no logic change |
| `Neo4jFoundationalFacetAdapter.collect_facet_by_label` | `neo4j_foundational_facet_adapter.py` | `tool.facet.collect` | **Gap**: not exposed as MCP tool |
| `Neo4jFoundationalSimilarityAdapter.calculate_similar_by_label_and_values` | `neo4j_foundational_similarity_adapter.py` | `tool.similarity.calculate` | Already exposed via `eugene_fetch_tools.fetch_similar` |
| `Neo4jDrugAliasesAdapter.*` | `neo4j_drug_aliases_adapter.py` | `tool.drug.alias` | Already exposed via `eugene_drug_tools.fetch_drug_aliases` |
| `Neo4jOrganizationSearchAdapter.find_companies_by_name_pattern`, `find_assets_by_org_id` | `src/organization/infra/db/neo4j_organization_search_adapter.py` | `tool.organization.search` | Already exposed via `eugene_organization_tools.*` |
| `FusionSearchService.*` | `src/foundation/vector/fusion_search_service.py` | `tool.vector.fusion` | Already exposed via `eugene_vector_tools.search_fused` |
| `PatentOrchestator.*` (ingest flow) | `src/patent/provider/patent_orchestrator.py` | `tool.patent.ingest` | Batch tool, run from L2 coordinator, not chat-facing |
| `Neo4jPatentQueryAdapter.find_related_patents_by_drug/_by_clinicaltrail/_by_gene` | `src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py` | `tool.patent.search_graph` | Exposed today only via REST (`patent_search_router.py`); needs MCP wrapper |
| `PgpubProvider`, `ApplicationOrchestator` | `src/patent/pgpub/provider/pgpub_provider.py`, `src/patent/application/provider/application_orchestrator.py` | `tool.patent.pgpub_fetch` | L2/batch tool |
| `PubmedOrchestrator.search_and_download` | `src/pubmed/provider/pubmed_orchestrator.py` | `tool.pubmed.ingest` | Batch tool |
| `Neo4jPubmedQueryAdapter.find_related_pubmed_by_drug/_by_clinicaltrail/_by_gene` | `src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py` | `tool.pubmed.search_graph` | Exposed today only via REST; needs MCP wrapper |
| `ClinicalTrailProvider.*` | `src/clinicaltrail/provider/clinical_trail_provider.py` | `tool.clinicaltrial.ingest` | Batch tool (loader from ClinicalTrials.gov) |
| `Neo4jClinicalTrialAdapter.find_node_id_by_nct` | `src/clinicaltrail/infra/db/neo4j_clinical_trial_adapter.py` | `tool.clinicaltrial.lookup` | New MCP wrapper |
| `ade.pipeline.ingest` / `ingest_safe` | `agents/eugene-ade/src/ade/pipeline.py` | `tool.document.ingest` | Already an HTTP tool (`/ade/ingest`); register as callable L3 tool for L2 coordinators beyond ingestion scheduler |
| `ade.indexer.index_document` | `agents/eugene-ade/src/ade/indexer.py` | `tool.document.index` | Internal to pipeline; keep as-is, referenced by L2 |
| `ade.render.render_evidence`, `render_page` | `agents/eugene-ade/src/ade/render.py` | `tool.document.evidence_render` | Already HTTP (`/ade/evidence/...`, `/ade/page/...`) |
| `centrality.compute`, `centrality.write_back` | `ingestion/src/pipeline/graph/centrality.py` | `tool.document.centrality` | Already invoked by `centrality_step.run()` |
| `EugeneGraphSummaryOrchestrator.summarize` | `src/graph/analyze/eugene_graph_summary_orchestrator.py` | `tool.graphrag.summarize` | Legacy, kept as-is under L3.GraphRAG |
| `DocumentAnalyzer.analyze_document_pages/_tasks` | `src/document/analyze/document_analyzer.py` | `tool.document.legacy_analyze` | Legacy L3 |
| `PdfParser.parse` | `src/document/parse/pdf_parser.py` | `tool.document.legacy_pdf_parse` | Legacy L3 |
| `TppSearchOrchestrator.find_patent_applications_by_embedding` | `src/tpp/provider/tpp_search_orchestrator.py` | `tool.tpp.search` | Already REST via `tpp/router/search_router.py`; needs MCP wrapper |
| `TrialsCollector`, `LiteratureCollector`, `PatentsCollector`, `EpoCollector`, `EdgarCollector` | `agents/eugene-scout/src/scout/collectors/*.py` | `tool.scout.<source>` | Called only from `scout/orchestrator.py` today; keep that call path, add named tool registration for discoverability |

**Rule applied uniformly:** every "Tool" in this mapping is a **wrapper**, not a
rewrite — the wrapper function's body is exactly one call into the existing
class/method. No Cypher, no adapter, no orchestrator logic is edited.

---

## 5. YAML Configuration Mapping

| Config File | Current Role | L1/L2/L3 Role After Refactor |
|---|---|---|
| `agents/eugene-ade/src/pipeline/config/ade-analysis-config.yaml.yml` | Descriptive manifest of the document domain (sources, scheduler, pipeline stages, storage, graph schema) | **L1 declarative entry-point manifest** for `l1.config_loader` — defines which L3.Document tools exist and their enablement flags (`document_sources.enabled`, `scheduler.enabled`, `vector_search.enabled`) |
| `ingestion/src/pipeline/config/research_areas.yaml` | Research-area queries consumed by `orchestrator.load_config()` | **L2 coordinator config** — drives `l2.coordinator.document_sweep` area selection; unchanged consumption code |
| `agents/eugene-scout/src/scout/config.py` (+ env-driven thresholds) | Scout scoring/collector configuration | **L2 coordinator config** for `l2.coordinator.scout_scan` |
| `docker.env` / `docker.env.template` | Neo4j/Milvus/Entra/CORS/rerank settings for `eugene_ws.py` | **L3 executor runtime config** (Neo4j/Milvus connection is an L3 concern, not L1/L2) |
| `agents/eugene-agent-ws/.env.template`, `env.template` | `EUGENE_MCP_SERVER_URL`, `EUGENE_CORE_API_URL`, `EUGENE_AGENT_MAX_ITERATIONS`, `EUGENE_MAX_TOOL_CALLS`, `EUGENE_ALLOW_*` | **L2 coordinator config** — iteration/tool-call budgets belong to the coordinator layer |
| `agents/eugene-mcp/.env.template` | `EUGENE_API_BASE`, JWT issuer/audience | **L3 executor config** — each MCP tool's HTTP client target |
| `docker-compose.yml` / `docker-compose.fetcher.yml` / `docker-compose.prod.yml` | Service wiring for all of the above | Update service *labels/comments* only to reflect L1/L2/L3 (no port/dependency changes required) |

Recommendation: introduce one new top-level `agent-layers.yaml` (per service) that
declares, for each existing YAML file above, which layer it belongs to and which
L3 tool-set it activates — this is additive documentation/config, not a change
to how `orchestrator.load_config()` or `ade-analysis-config.yaml.yml` are read.

---

## 6. API / Route → Agent Flow Mapping

| Route | Current Handler | L1 Entry | L2 Coordinator | L3 Tool |
|---|---|---|---|---|
| `POST /agent/api/query`, `/query/stream` | `chat_query_agent_router.py` | `l1.chat_entrypoint` | `l2.coordinator.chat` (`eugene_data_agent.execute`) | any of `l3.foundation.*`, `l3.organization`, `l3.vector.search`, `l3.pubmed.web`, `l3.patent.web`, `l3.clinicaltrial.web` |
| `GET /graph/relationship/start/{start_id}` | `src/foundation/router/n_hop_router.py` | REST caller (Swagger/Postman) or `l3.foundation.graph` via MCP | `FoundationalNHopProvider` (business logic, unchanged) | `Neo4jFoundationalNHopAdapter` |
| `GET /graph/path/...`, `/graph/reachability/...` | `search_path_router.py` | same | `FoundationalPathProvider` | `Neo4jFoundationalPathAdapter` |
| `GET /graph/facts/start/{start_id}` | `facts_router.py` | same | `FoundationalFactsOrchestrator` | `Neo4jFoundationalNHopAdapter` + `FactsMapper` |
| `GET /node/find/{node_value}`, `POST /node/details` | `node_id_lookup_router.py`, `node_details_router.py` | same | `FoundationalNodeIdProvider`, `FoundationalNodeDetailsProvider` | `Neo4jFoundationalNodeAdapter`, `Neo4jFoundationalNodeDetailsAdapter` |
| `GET /labels/{label}`, `GET /count/{label}` | `label_router.py`, `count_router.py` | same | direct adapter call (no provider today) | `Neo4jFoundationalNodeAdapter.find_by_label`, `Neo4jFoundationalNodeCountAdapter.count_all_by_label` |
| `POST /facet/{label}`, `POST /similarity/{label}` | `facet_router.py`, `similarity_router.py` | same | direct adapter call | `Neo4jFoundationalFacetAdapter`, `Neo4jFoundationalSimilarityAdapter` |
| `GET /patents/*`, `/count/patents/*` | `patent_search_router.py`, `patent_count_router.py` | REST only today — **add MCP tool** | none today | `Neo4jPatentQueryAdapter` |
| `GET /pmids/*`, `/count/pmids/*` | `pubmed_search_router.py`, `pubmed_count_router.py` | REST only today — **add MCP tool** | none today | `Neo4jPubmedQueryAdapter` |
| `POST /research/digest` | `digest_router.py` | REST only | none today | inline Cypher against `paper`/`clinical_trial` |
| `POST /ingest/run`, `/ingest/dry-run`, `/ingest/centrality` | `ingestion/scheduler/service.py` | `l1.ingestion_trigger` | `l2.coordinator.document_sweep` (`orchestrator.run`) | `l3.document.ade` (`/ade/ingest`), `l3.document.centrality` |
| `POST /ade/ingest`, `/ade/ingest/batch`, `/ade/reindex` | `agents/eugene-ade/src/ade/api.py` | called by L2 document-sweep, or directly for backfill | n/a (executor endpoint) | `ade.pipeline.ingest`, `ade.pipeline.reindex` |
| `GET /ade/documents/{doc_id}*`, `/ade/evidence/*`, `/ade/page/*` | same file | serves L1 UI evidence viewer directly | n/a | `ade.storage`, `ade.render` |
| Scout `POST /scan`, etc. | `agents/eugene-scout/src/scout/api.py` | `l1.scout_trigger` | `l2.coordinator.scout_scan` | `l3.scout.<collector>` |

---

## 7. Refactoring Phases (with priorities)

**Phase 0 — Inventory freeze (P0, no code change).**
Confirm this document against the running system; tag every router/provider/
adapter file referenced above with a `# layer: L1|L2|L3` marker comment (one
line, non-functional) so the mapping is discoverable in-code.

**Phase 1 — L3 tool registry, additive only (P1).**
Add MCP tool wrappers for the currently-missing domains without touching
their adapters:
- `tool.labels.count` (wraps `Neo4jFoundationalNodeCountAdapter.count_all_by_label`)
- `tool.facet.collect` (wraps `Neo4jFoundationalFacetAdapter.collect_facet_by_label`)
- `tool.patent.search_graph` (wraps `Neo4jPatentQueryAdapter.*`)
- `tool.pubmed.search_graph` (wraps `Neo4jPubmedQueryAdapter.*`)
- `tool.clinicaltrial.lookup` (wraps `Neo4jClinicalTrialAdapter.find_node_id_by_nct`)
- `tool.tpp.search` (wraps `TppSearchOrchestrator.find_patent_applications_by_embedding`)

Each is a new file in `agents/eugene-mcp/src/tools/`, following the existing
`EugeneGraphTools` pattern (HTTP call to `eugene_ws`, token passthrough). Zero
changes to `src/foundation`, `src/patent`, `src/pubmed`, `src/clinicaltrail`,
`src/tpp`.

**Phase 2 — L2 coordinator extraction inside eugene-agent-ws (P1).**
Move the routing/error-handling/budget logic already living inline in
`chat_query_agent_router.py` and `eugene_data_agent.py` into a named
`l2/agent_router.py` module that the router calls. This is a **move**, not a
rewrite: `_add_default_tools`, `_manage_conversation_id`, the hard caps
(`_AGENT_MAX_ITERATIONS`, `_HARD_TOOL_CALL_BUDGET`, `_MAX_DUPLICATE_TOOL_CALLS`)
relocate unchanged.

**Phase 3 — L1 extraction inside eugene-agent-ws (P2).**
Extract `intent_classifier.classify_intent`, `ToolRequestEnum` resolution, and
`ChatQueryRequest` validation into `l1/agent_selector.py` and
`l1/session_context.py`. Router functions become thin: validate → call L1 →
call L2 → return.

**Phase 4 — Document-domain L1/L2/L3 labeling (P2).**
No code changes: annotate `ingestion/scheduler/service.py` as L1
(trigger surface) + L2 (cron coordinator, since `_execute`/`_centrality`
already orchestrate), `ingestion/src/pipeline/orchestrator.py` as L2, and all
of `agents/eugene-ade/src/ade/*.py` as L3. Optionally add a
`l3.document.*` tool registry file in `agents/eugene-mcp` that lets the chat
agent trigger `/ade/ingest` and `/ade/documents/{doc_id}` directly (net-new
capability, additive).

**Phase 5 — Scout-domain L1/L2/L3 labeling (P3).**
Same additive labeling for `agents/eugene-scout`; optionally expose
`scout/collectors/*` as MCP tools if cross-domain chat queries are desired
later. Not required for the architecture goal.

**Phase 6 — Legacy GraphRAG / TPP / Patent / PubMed CLI scripts (P3).**
Reclassify `src/graph/analyze/*`, `src/tpp/*`, `download_patents.py`,
`download_pubmed.py`, `download_clinicaltrail.py`, `store_triples.py`,
`store_summaries.py` as L2 (script-level coordinators) + L3 (business
functions) without wrapping them as MCP tools, since they are offline/batch
scripts, not chat-facing. Document this explicitly so no one assumes they need
an L1 entry point.

**Phase 7 — Documentation and folder alignment (P3).**
Apply the folder structure in §8. Update `README.md` files per service to
reference the new layer names.

Priority order: **Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 0 (can run in
parallel as comments) → Phase 5/6/7.**

---

## 8. Folder Structure Recommendation

```text
agents/eugene-agent-ws/src/
  l1/                          # NEW — thin, additive
    __init__.py
    session_context.py         # wraps ChatQueryRequest, conversation_id mgmt
    agent_selector.py          # wraps intent_classifier + ToolRequestEnum resolution
    config_loader.py           # reads ade-analysis-config.yaml.yml, research_areas.yaml refs
    prompt_context.py          # wraps build_source_directive, temporal directive
  l2/                          # NEW — thin, additive
    __init__.py
    agent_router.py            # tool-set resolution, budgets, error handling (moved from router/agent)
  query/                       # UNCHANGED — existing L2 execution + L3 web tools
    agent/eugene_data_agent.py
    router/chat_query_agent_router.py
    tools/external_tools.py
    model/, util/, conf/

agents/eugene-mcp/src/
  tools/                       # L3 — existing tools stay; new ones added alongside
    eugene_graph_tools.py
    eugene_node_tools.py
    ...
    eugene_patent_tools.py      # NEW (Phase 1)
    eugene_pubmed_tools.py      # NEW (Phase 1)
    eugene_clinicaltrial_tools.py  # NEW (Phase 1)
    eugene_tpp_tools.py         # NEW (Phase 1)

agents/eugene-ade/                # L3.Document — unchanged internals
agents/eugene-scout/               # L1(trigger)/L2(orchestrator)/L3(collectors) — unchanged internals
ingestion/                         # L1(trigger)/L2(coordinator) — unchanged internals

src/
  foundation/ organization/ patent/ pubmed/ clinicaltrail/ document/
  graph/ tpp/ centree/            # L3 business logic — UNCHANGED, referenced by tool wrappers only
  eugene_ws.py                    # L3 REST surface — UNCHANGED

docs/
  L1_L2_L3_AGENT_ARCHITECTURE_REFACTORING_PLAN.md   # this document
  agent-layers.yaml (optional, Phase 7)              # declarative layer manifest
```

No existing file moves in Phases 1–4; only new files are added under `l1/`
and `l2/`, and new tool-wrapper files are added under `tools/`.

---

## 9. Migration Strategy (minimal code changes)

1. **Additive-first.** Every phase above adds new files/wrappers; it does not
   edit `src/foundation/**`, `src/patent/**`, `src/pubmed/**`,
   `src/clinicaltrail/**`, `src/document/**`, `src/graph/**`, `src/tpp/**`,
   or any Cypher string. Business logic, Cypher, and response models are
   frozen.
2. **Router functions become call-throughs.** In `chat_query_agent_router.py`,
   replace inline logic with two calls: `l1_result = agent_selector.resolve(...)`
   then `l2_result = agent_router.dispatch(l1_result)`. The existing
   `eugene_data_agent.execute(...)` call signature does not change.
3. **New MCP tools reuse the existing HTTP helper.** `make_eugene_request` /
   `post_eugene_request` (`agents/eugene-mcp/src/util/request.py`) is reused
   verbatim for `eugene_patent_tools.py`, `eugene_pubmed_tools.py`,
   `eugene_clinicaltrial_tools.py`, `eugene_tpp_tools.py` — copy the pattern
   from `eugene_graph_tools.py`.
2. **Backward compatibility.** All existing REST routes on `eugene_ws.py`
   remain unchanged and callable directly (Swagger/Postman testing in
   `docs/FOUNDATION_GRAPH_API_SWAGGER_GUIDE.md` keeps working). MCP tool
   wrappers are additive callers of the same routes.
3. **Feature flag rollout.** Gate new MCP tools behind the existing
   `register_tools(...)` list in `eugene_mcp.py::_register_tools` — add
   entries incrementally, one PR per domain (Phase 1 bullets), so any
   regression is isolated to one tool.
4. **No schema/config migration needed.** `ade-analysis-config.yaml.yml` and
   `research_areas.yaml` keep their current readers
   (`orchestrator.load_config`); the L1 `config_loader.py` only *also* reads
   them for layer classification, it does not replace the existing loader.
5. **Testing strategy.** Reuse existing test suites per domain
   (`src/foundation/**/*_test.py`, `agents/eugene-scout/tests/*`,
   `agents/eugene-ade/tests/*`) unchanged; add new unit tests only for the
   new `l1/`, `l2/`, and tool-wrapper files, asserting they call through to
   the existing function with the same arguments (mock the adapter/provider).
6. **Rollback.** Because Phases 1–4 are additive, rollback = delete the new
   files and revert the two call-through edits in
   `chat_query_agent_router.py`; no data or schema rollback required.

---

## 10. Risks, Dependencies, and Impact Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| New MCP tools (Phase 1) duplicate auth/token handling incorrectly, bypassing `extract_token()` / `CONTEXT_TOKEN_ERROR_MSG` checks | Medium | High (auth bypass) | Copy the exact pattern from `eugene_graph_tools.py`; add a unit test asserting the token guard fires |
| `chat_query_agent_router.py` refactor into `l1/`+`l2/` accidentally changes `_manage_conversation_id` or hard-cap semantics | Medium | High (session bleed across sources, runaway tool loops) | Move code verbatim in one commit with no logic edits; diff-review against original functions line by line |
| Facet/similarity adapters already have a known Cypher-injection style risk (`_build_facet_by_label_query`, `_build_similarity_query_by_label_and_values` interpolate `values` into regex) | Existing, unchanged by this refactor | Medium–High (pre-existing) | Out of scope for this refactor (explicitly "without changing business logic"); flag separately for a security fix, not bundled here |
| Document-domain (`ingestion` + `eugene-ade`) and Scout-domain are on independent schedules; labeling them L1/L2/L3 does not by itself unify session/state management with the chat coordinator | High (by design) | Low (no functional regression, but architecture diagram implies more unification than Phase 1–5 delivers) | Document explicitly in Phase 4/5 that these remain independently-scheduled L1/L2/L3 stacks unless a future phase adds a chat-facing MCP tool for them |
| `EUGENE_MCP_SERVER_URL`, `EUGENE_API_BASE`, `EUGENE_CORE_API_URL` env vars must stay consistent across the three services after folder changes | Low | Medium (broken service-to-service calls) | No env var renames in this plan; only new files, same var names |
| Adding tool wrappers increases `_HARD_TOOL_CALL_BUDGET` pressure per chat turn (more tools = more candidate calls) | Low | Low–Medium | Keep new tools opt-in per `ToolRequestEnum`, not part of default `_add_default_tools` |
| GDS/APOC availability (`gds.nodeSimilarity.filtered.stream`, `apoc.map.merge`) is a hard dependency for `tool.similarity.calculate` and `tool.facet.collect` | Existing | Medium | Confirm `NEO4J_PLUGINS=["apoc","graph-data-science"]` remains set in `docker-compose.yml` (already true) |
| Team unfamiliarity with "L1/L2/L3" naming causing confusion with existing "Tier 1/2/3" source-cascade naming in `eugene_data_agent.py`'s `_all_sources_directive` | Medium | Low | Use distinct terminology in code comments (`# layer: L1` vs. the prompt's "TIER 1/2/3" data-source cascade, which is a different concept) |

**Dependencies to verify before Phase 1:**
- `agents/eugene-mcp` reachability to `eugene_ws` (`EUGENE_API_BASE`) for new tool wrappers.
- Neo4j APOC + GDS plugins enabled (already configured in `docker-compose.yml`).
- JWT/Entra auth wiring (`eugene_jwt_verifier`, `router/auth/auth.py`) unaffected by new files.
- `docs/FOUNDATION_GRAPH_API_SWAGGER_GUIDE.md` remains the source of truth for the underlying REST contracts the new MCP tools will wrap.

---

## Summary

The system already exhibits an informal 3-layer shape for the
Foundation/Organization/Vector domains (UI → agent-ws → mcp tools → core API →
Neo4j). This plan formalizes that shape as L1 (session/selection) → L2
(coordination/ReAct/scheduling) → L3 (one tool per existing business
function), closes the tool-coverage gap for Patent/PubMed/ClinicalTrial/TPP,
and explicitly classifies the independently-scheduled Document (ADE/ingestion)
and Scout domains as self-contained L1/L2/L3 stacks — all without editing a
single adapter, provider, Cypher query, or response model.
