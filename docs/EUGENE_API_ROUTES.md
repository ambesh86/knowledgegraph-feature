# Eugene — Complete API Route Reference

Every HTTP route in the system, in one file.

**How this was produced:** routes were extracted by parsing the source AST, then
**verified against the live `/openapi.json` of each running service**. Auth
behaviour was confirmed by calling the endpoints. Nothing here is from memory.

**Verified:** 2026-08-04, against the running local stack.

---

## Contents

- [Summary](#summary)
- [1. Core API — `eugene-ws` (:18000)](#1-core-api--eugene-ws-18000)
- [2. Agent API — `eugene-agent-ws` (:18001)](#2-agent-api--eugene-agent-ws-18001)
- [3. Document extraction — `eugene-ade` (:18100)](#3-document-extraction--eugene-ade-18100)
- [4. Ingestion scheduler — `eugene-ingestion` (:18200)](#4-ingestion-scheduler--eugene-ingestion-18200)
- [5. MCP tool server — `eugene-mcp` (:18443)](#5-mcp-tool-server--eugene-mcp-18443)
- [6. Web app BFF — `eugene-agent-ui-next` (:18502)](#6-web-app-bff--eugene-agent-ui-next-18502)
- [7. Defined but NOT mounted](#7-defined-but-not-mounted)
- [8. Auth model](#8-auth-model)
- [9. Quick reference — curl](#9-quick-reference--curl)

---

## Summary

| # | Service | Base URL (host) | Routes | Source of truth |
|---|---|---|---|---|
| 1 | `eugene-ws` — Core API | `http://localhost:18000` | **44** | `src/**/router/*.py` |
| 2 | `eugene-agent-ws` — Agent | `http://localhost:18001` | **6** | `agents/eugene-agent-ws/src/**/router/*.py` |
| 3 | `eugene-ade` — Extraction | `http://localhost:18100` | **10** | `agents/eugene-ade/src/ade/api.py` |
| 4 | `eugene-ingestion` — Scheduler | `http://localhost:18200` | **4** | `ingestion/scheduler/service.py` |
| 5 | `eugene-mcp` — Tools | `http://localhost:18443` | 1 + **17 tools** | `agents/eugene-mcp/src/**` |
| 6 | `eugene-agent-ui-next` — BFF | `http://localhost:18502` | **34** (25 files) | `app/api/**/route.ts` |
| | **Total HTTP endpoints** | | **98** | |

> **Note on the agent service:** it is mounted with `root_path="/agent/api"`, so
> every route is served under that prefix. The router files declare `/query`; the
> real URL is `/agent/api/query`.

Interactive docs: `http://localhost:18000/docs`, `:18001/agent/api/docs`,
`:18100/docs`, `:18200/docs`.

---

## 1. Core API — `eugene-ws` (:18000)

Graph queries, vector search, statistics, auth. **44 routes.**

### 1.1 Root, health, auth, releases

| Method | Path | Handler | Purpose | Auth |
|---|---|---|---|---|
| GET | `/` | `app_root` | Service root | **Yes** |
| GET | `/health` | `liveness` | Liveness probe | No |
| GET | `/health/ready` | `readiness` | Readiness — checks dependencies | No |
| GET | `/health/data-freshness` | `data_freshness` | When internal data was last refreshed, and how stale it is. **Read by the agent so it can date internal facts honestly.** | No |
| GET | `/login` | `login` | Starts the Entra ID OAuth flow | No |
| GET | `/auth/callback` | `auth_callback` | OAuth redirect target. Path comes from `REDIRECT_PATH` (default `/auth/callback`) | No |
| POST | `/auth/token` | `issue_local_token` | JSON token endpoint for programmatic / SPA clients | No |
| GET | `/auth/whoami` | `protected` | Returns the decoded caller identity | **Yes** |
| GET | `/releases` | `get_releases` | Release notes | No |

*Source: `src/router/root_router.py`, `health_router.py`, `auth/auth_router.py`, `release_notes_router.py`*

### 1.2 Node lookup and traversal

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/node/find/{node_value}` | `lookup_node_id_by_value` | Resolve a name/value to node id(s). Supports fuzzy matching |
| POST | `/node/details` | `lookup_node_details_by_id` | Full details for node id(s). **Use this to resolve an alias node to its canonical entity** |
| GET | `/labels/{label}` | `list_by_label` | Page through all nodes of one label |
| GET | `/count/{label}` | `count_by_label` | Count nodes of one label |
| GET | `/graph/relationship/start/{start_id}` | `find_n_hop` | N-hop neighbourhood. Default `n_hop=1` |
| GET | `/graph/facts/start/{start_id}` | `find_n_hop` | Indications / contraindications / off-label (drugs), or associated genes/drugs (diseases). **Does not return trials** |
| GET | `/graph/path/start/{start_id}/end/{end_id}` | `find_search_paths_by_start_id_and_end_id` | Concrete paths between two nodes |
| GET | `/graph/reachability/start/{start_id}/end/{end_id}` | `find_is_reachable_by_start_id_and_end_id` | Boolean reachability — cheaper than fetching paths |
| POST | `/facet/{label}` | `collect_facets_by_label_and_values` | Facet counts for filtering |
| POST | `/similarity/{label}` | `calculate_similarity_by_label_and_values` | Similarity between nodes of a label |

*Source: `src/foundation/router/{node_id_lookup,node_details,label,count,n_hop,facts,search_path,facet,similarity}_router.py`*

### 1.3 Drugs

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/drugs/aliases/{drug_name}` | `search_drug_aliases_by_value` | Aliases/synonyms by name |
| GET | `/drugs/aliases/id/{drug_id}` | `search_drug_aliases_by_id` | Aliases/synonyms by id |

### 1.4 Patents and PubMed

Same three-entity shape for each: `drugs`, `clinicaltrials`, `geneproteins`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/patents/drugs` | Patents related to a drug id |
| GET | `/patents/clinicaltrials` | Patents related to a trial id |
| GET | `/patents/geneproteins` | Patents related to a gene/protein id |
| GET | `/count/patents/drugs` | Count only — avoids paging a large result set |
| GET | `/count/patents/clinicaltrials` | Count only |
| GET | `/count/patents/geneproteins` | Count only |
| GET | `/pmids/drugs` | PubMed docs related to a drug id |
| GET | `/pmids/clinicaltrials` | PubMed docs related to a trial id |
| GET | `/pmids/geneproteins` | PubMed docs related to a gene/protein id |
| GET | `/count/pmids/drugs` | Count only |
| GET | `/count/pmids/clinicaltrials` | Count only |
| GET | `/count/pmids/geneproteins` | Count only |

*Source: `src/foundation/router/{patent_search,patent_count,pubmed_search,pubmed_count}_router.py`*

### 1.5 Organizations

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/organizations/{organization_name}` | `list_organization_names` | Matching organizations **with their real `node_id`** |
| GET | `/organizations/assets/{organization_id}` | `list_organization_assets` | Assets for one organization |

> **Two-step, always.** The id passed to `/organizations/assets/{id}` **must** come
> from a prior `/organizations/{name}` result. The agent's system prompt forbids
> guessed ids here, because a placeholder id returns a plausible-looking empty
> result rather than an error.

### 1.6 Vector and fused retrieval

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/vector/health` | `vector_health` | Collection present and populated? |
| GET | `/vector/search/{query}` | `vector_search` | Semantic search over the summary store. `top_k` 1–20 |
| GET | `/vector/fusion/health` | `fusion_health` | Readiness of **both** retrievers |
| GET | `/vector/fusion?q=...` | `fusion_search_q` | **Hybrid retrieval. Use this one.** |
| GET | `/vector/fusion/{query}` | `fusion_search` | Path-parameter variant — **avoid** |

> **Why `?q=` and not the path variant.** A query containing a slash — and
> `BAFF/APRIL` is a central term in this corpus — is decoded as a path separator
> and returns 404 *even when percent-encoded*. That silently broke fused search
> for a whole class of biomedical queries: the agent received "returned nothing"
> and correctly reported the graph had no such information, when the same query
> without the slash returned 15 graph hits. The path variant is kept for
> compatibility only.

**`/vector/fusion` query parameters:**

| Param | Type | Default | Meaning |
|---|---|---|---|
| `q` | string | *required* | The search query |
| `top_k` | int 1–500 | 10 | Fused evidence items to return |
| `candidates` | int 1–500 | `3×top_k`, max 60 | Retriever depth **before** fusion. Raise it when you rerank — a reranker can only reorder the pool it is given |
| `rerank` | bool | `false` | Cross-encoder rerank of the fused pool |

> **Cost warning:** `rerank=true` costs ~20–30 s per query on CPU (measured
> ~0.46 s per candidate at the default 60-candidate cap). It is **off by default**
> for that reason. It raised measured retrieval@15 from 26.1% to 100% on the
> table-cell evaluation set — see [eval/README.md](../eval/README.md).

### 1.7 Statistics and research digest

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/stats` | `fetch_database_stats` | Node/relationship counts |
| GET | `/stats/top-proteins` | `fetch_top_connected_proteins` | Gene/proteins by connectivity. `limit` default 20 |
| GET | `/stats/shared-gene-diseases` | `fetch_shared_gene_diseases` | Disease pairs sharing ≥ `min_shared` genes (default 3) |
| POST | `/research/digest` | `digest` | **What landed in a researcher's areas since `since`.** Primary signal is our own graph, where every paper carries `indexed_at` from the nightly run |

> **Why the digest reads our own graph rather than live APIs.** Europe PMC does
> not reliably honour `sort=P_PDATE_D desc` — measured results came back ordered
> 2026-06-11, 2026-07-01, 2026-03-03, which is not sorted at all. There was also
> a sort but no date *filter*, so a panel headed "overnight" happily showed
> 2002–2010 patent grants. An empty result is a real answer here.

---

## 2. Agent API — `eugene-agent-ws` (:18001)

The LLM agent. **6 routes**, all under `root_path="/agent/api"`.

| Method | Path | Handler | Purpose | Auth |
|---|---|---|---|---|
| GET | `/agent/api/` | `app_root` | Service root | No |
| GET | `/agent/api/health` | `liveness` | Liveness | No |
| GET | `/agent/api/health/ready` | `readiness` | Readiness | No |
| GET | `/agent/api/auth/whoami` | `protected` | Caller identity | **Yes** |
| POST | `/agent/api/query` | `chat_query_agent` | One turn, single JSON response | **Yes** |
| POST | `/agent/api/query/stream` | `chat_query_agent_as_stream` | One turn, **Server-Sent Events** (`text/event-stream`). This is what the UI uses | **Yes** |

**Request body** (`ChatQueryRequest`) carries the prompt, an optional
`conversation_id`, and the enabled tool sources.

**Tool sources** (`ToolRequestEnum`): `eugene`, `http`, `all_sources`,
`clinical_trials`, `chembl`, `biorxiv`, `pubmed`.

`all_sources` is a cascading mode: Eugene KG → ClinicalTrials.gov → PubMed.

**Stream event types:** `session`, tool-call chips, text deltas. On transient
model errors the stream retries up to `EUGENE_AGENT_MODEL_RETRIES` (default 3),
each retry with a **fresh session id** so a failed turn's partial tool-use state
is not replayed into the model.

---

## 3. Document extraction — `eugene-ade` (:18100)

**10 routes.** No auth — internal to the Docker network, reached by the browser
only through the Next.js proxy (§6).

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/health` | `health` | Liveness + S3 reachability + layout-model status |
| POST | `/ade/ingest` | `ingest` | Run the pipeline for one document. **Idempotent** |
| POST | `/ade/ingest/batch` | `ingest_batch` | Queue ≤ 25 documents for background extraction; returns immediately |
| POST | `/ade/reindex` | `reindex_all` | Re-run graph indexing from existing S3 artifacts — **no re-extraction**. `?doc_id=` for one |
| GET | `/ade/documents/{doc_id}` | `get_document` | The manifest |
| GET | `/ade/documents/{doc_id}/chunks` | `get_chunks` | Chunks. Filters: `chunk_type`, `page`, `limit` (≤ 5000) |
| GET | `/ade/documents/{doc_id}/markdown` | `get_markdown` | `parse.md` |
| GET | `/ade/documents/{doc_id}/pdf` | `get_pdf` | The original PDF — byte-identical evidence of record. `?download=true` |
| GET | `/ade/evidence/{doc_id}/{chunk_id}.png` | `evidence_png` | **The proof image:** source page with the cited region highlighted. `dpi` 96–300, default 150 |
| GET | `/ade/page/{doc_id}/{page_no}.png` | `page_png` | Plain page render, no highlight |

**Ingest body:** `{"source": "pubmed"|"europepmc"|"pmc"|"url", "id": "...", "force": false}`

**Ingest response statuses:**

| Status | Meaning |
|---|---|
| `ready` | Extracted and indexed |
| `unavailable` | No open-access PDF (paywalled). **A normal outcome, not an error.** Cached — the answer will not change on retry |
| `failed` | Transient error. **Not cached** — stays retryable, carries `retryable: true` |

Evidence and page renders return `Cache-Control: public, max-age=86400`; they are
deterministic for a given `(doc_id, chunk_id, dpi)`.

---

## 4. Ingestion scheduler — `eugene-ingestion` (:18200)

**4 routes.** No auth. Runs the nightly sweep at **01:00 UTC** by default.

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/health` | `health` | Schedule, whether a run is in flight, last result, run count |
| POST | `/ingest/run` | `trigger` | Force a sweep now. Returns immediately — **poll `/health`** |
| POST | `/ingest/dry-run` | `dry_run` | Discovery only. No extraction, no writes. Shows what a sweep *would* fetch |
| POST | `/ingest/centrality` | `centrality_only` | Re-rank the corpus **without re-parsing anything**. Backgrounded |

Only one run may be in flight; a second request returns
`{"status": "busy"}` rather than queueing.

> **Why `/ingest/centrality` is separate.** Parsing is the expensive stage and
> ranking is the cheap one, so decoupling them lets the whole corpus be retuned
> without re-parsing it. It is backgrounded because a synchronous version *died
> mid-computation the moment a client timed out*, losing the work with nothing
> written back.

---

## 5. MCP tool server — `eugene-mcp` (:18443)

Speaks **MCP** (Model Context Protocol) over streamable HTTP, not plain REST.
Consumed by the agent via `strands.tools.mcp.MCPClient` with a bearer token. It
also registers a health route.

**17 registered tools:**

| Tool | Backed by | Purpose |
|---|---|---|
| `fetch_identity` | — | Caller identity |
| `fetch_by_label` | `/labels/{label}` | Nodes of one label |
| `fetch_similar` | `/similarity/{label}` | Similar nodes |
| `lookup_node_by_value` | `/node/find/{value}` | Name → node id. Supports `fuzzy_match` |
| `fetch_node_details` | `/node/details` | Full node details; resolves alias → canonical |
| `fetch_drug_aliases` | `/drugs/aliases/*` | Drug synonyms |
| `fetch_facts` | `/graph/facts/...` | Indications / contraindications / associations |
| `fetch_node_relationships` | `/graph/relationship/...` | Graph edges — **use for "which trials reference X"** |
| `has_reachable_path` | `/graph/reachability/...` | Boolean connectivity |
| `fetch_paths` | `/graph/path/...` | Concrete paths |
| `find_organization_names` | `/organizations/{name}` | **Step 1** of the two-step org lookup |
| `find_organization_assets` | `/organizations/assets/{id}` | **Step 2** — id must come from step 1 |
| `search_summaries` | `/vector/search/{query}` | Semantic summary search |
| `search_fused` | `/vector/fusion` | **The recommended starting point for any entity question** |
| `fetch_graph_stats` | `/stats` | Graph statistics |
| `fetch_top_connected_proteins` | `/stats/top-proteins` | Connectivity ranking |
| `fetch_shared_gene_diseases` | `/stats/shared-gene-diseases` | Disease pairs by shared genes |

Local (non-MCP) tools the agent may also load, depending on enabled sources:
`search_pubmed`, `search_europepmc`, `search_clinical_trials`,
`search_patents_web`, `http_request`, `current_time`, `calculator`.

---

## 6. Web app BFF — `eugene-agent-ui-next` (:18502)

Next.js API routes. **34 method-level endpoints across 25 route files.** These are
a backend-for-frontend layer: they hold the session cookie, talk to Postgres, and
proxy the internal services the browser cannot reach directly.

### 6.1 Auth and session

| Methods | Path | Purpose |
|---|---|---|
| POST | `/api/atlas/auth/register` | Create an account |
| POST | `/api/atlas/auth/login` | Sign in, set the session cookie |
| POST | `/api/atlas/auth/logout` | Clear the session |
| GET | `/api/atlas/auth/me` | Current user |
| PATCH | `/api/atlas/auth/profile` | Update profile / focus areas |
| POST | `/api/auth/token` | Mint a Eugene backend token |

### 6.2 Conversations

| Methods | Path | Purpose |
|---|---|---|
| GET, POST | `/api/atlas/conversations` | List / create |
| GET, PATCH, DELETE | `/api/atlas/conversations/[id]` | Read / rename / delete |
| POST | `/api/atlas/conversations/[id]/messages` | Append a message |
| POST | `/api/atlas/conversations/[id]/title` | Auto-title a conversation |

### 6.3 Chat streaming and graph

| Methods | Path | Purpose |
|---|---|---|
| POST | `/api/stream` | Proxies the agent's SSE stream to the browser |
| GET | `/api/graph/node/[id]` | Node detail for the context graph |
| GET | `/api/graph/expand/[id]` | Expand a node's neighbours |
| GET | `/api/graph/path` | Path between two nodes |

### 6.4 Documents, evidence, artifacts

| Methods | Path | Purpose |
|---|---|---|
| GET, POST | `/api/atlas/ade/[...path]` | **Catch-all proxy to `eugene-ade`.** Binary responses (evidence PNGs, PDFs) stream through untouched |
| GET, POST | `/api/atlas/uploads` | List / upload user documents |
| GET, DELETE | `/api/atlas/uploads/[id]` | Read / delete an upload |
| GET, POST | `/api/atlas/artifacts` | List / create artifacts |
| GET, DELETE | `/api/atlas/artifacts/[id]` | Read / delete |
| GET | `/api/atlas/artifacts/[id]/export` | Export an artifact |

> **Why one catch-all instead of eight routes.** ADE is internal to the Docker
> network and unreachable from the browser, but duplicating each of its ~8
> endpoints here would mean two places to keep in sync every time the service
> grows one. Timeouts differ by operation: **300 s** for ingest (a cold
> fetch + parse + YOLO run was measured at ~70 s), 60 s for reads.

### 6.5 Digest and status

| Methods | Path | Purpose |
|---|---|---|
| GET | `/api/atlas/digest` | Overnight digest for the user's focus areas |
| GET | `/api/atlas/intel` | Live intel panel |
| GET | `/api/atlas/freshness` | Data-freshness banner |
| GET, POST | `/api/atlas/backend-config` | Read / set backend configuration |
| GET | `/api/health` | UI liveness |

---

## 7. Defined but NOT mounted

These routers exist in the source but are **not** in `eugene_ws.py`'s include
list, so they are **not reachable** — confirmed absent from the live OpenAPI spec.

| File | Prefix | Routes | Status |
|---|---|---|---|
| `src/organization/router/organization_alias_search_router.py` | `/list` | `GET /list/organization/aliases/{organization_name}` | **Dead** |
| `src/tpp/router/search_router.py` | `/embeddings` | `POST /embeddings/`, `GET /embeddings/tpps/{tpp_id}`, `GET /embeddings/tpps/{tpp_id}/graph`, `GET /embeddings/tpps/{tpp_id}/question/{question_type}` | **Dead** |

Five routes total. Either wire them into `add_routers()` or delete them — right
now they read as available API surface and are not.

One route **is** conditionally mounted, and that is deliberate:
`vector_search_router` is imported inside a `try/except`. A bad or unset
`EUGENE_MILVUS_URI` makes `pymilvus` raise at *import* time, so guarding it means
a misconfigured vector store disables five routes instead of taking down the
entire core API.

---

## 8. Auth model

Verified by calling the live endpoints:

| Service | Behaviour |
|---|---|
| **Core API** | Auth is **per-route**, not global. Only `/` and `/auth/whoami` are gated (`403` without a token). Data routes — `/stats`, `/labels/*`, `/vector/*`, `/graph/*` — respond **without** a token in this local configuration |
| **Agent API** | `/agent/api/query` and `/query/stream` require a bearer token (`401` without) |
| **ADE** | **No auth.** Internal to the Docker network |
| **Ingestion** | **No auth.** Internal to the Docker network |
| **MCP** | Bearer token, forwarded by the agent |
| **Next.js BFF** | Session cookie, set at login |

> ⚠️ **Before exposing anything publicly:** ADE and the ingestion scheduler have
> no authentication at all, and the core API's data routes are open in this
> configuration. `POST /ingest/run` and `POST /ade/ingest` both trigger expensive
> work. They are safe behind the Docker network and are **not** safe on a public
> interface.

Token acquisition: `POST /auth/token` on the core API (programmatic/SPA), or the
browser flow `GET /login` → `GET /auth/callback`.

---

## 9. Quick reference — curl

```bash
# --- health across the stack -------------------------------------------------
curl -s localhost:18000/health                 # core API
curl -s localhost:18001/agent/api/health       # agent
curl -s localhost:18100/health                 # ADE (includes S3 + model status)
curl -s localhost:18200/health                 # scheduler (includes next run)
curl -s localhost:18000/vector/fusion/health   # both retrievers

# --- retrieval ---------------------------------------------------------------
# Always use ?q= — the path variant 404s on queries containing "/"
curl -s "localhost:18000/vector/fusion?q=BAFF/APRIL%20inhibitor&top_k=10"

# High-accuracy mode: deep pool + cross-encoder rerank (~20-30s, CPU)
curl -s "localhost:18000/vector/fusion?q=what+p+value+for+D4A1J3&top_k=15&candidates=200&rerank=true"

# --- graph -------------------------------------------------------------------
curl -s "localhost:18000/node/find/emicizumab"
curl -s "localhost:18000/graph/relationship/start/DB13923?n_hop=1&page_size=25"
curl -s "localhost:18000/stats"

# Organizations — ALWAYS two steps, never guess the id
curl -s "localhost:18000/organizations/CSL"                     # 1. get real node_id
curl -s "localhost:18000/organizations/assets/<node_id>"        # 2. use it

# --- document extraction and evidence ----------------------------------------
curl -X POST localhost:18100/ade/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source":"europepmc","id":"PMC13202553"}'

curl -s "localhost:18100/ade/documents/pmc13202553" | jq '.status, .chunk_count'
curl -s "localhost:18100/ade/documents/pmc13202553/chunks?chunk_type=table_cell&page=4"

# The proof image
curl -s "localhost:18100/ade/evidence/pmc13202553/<chunk_id>.png?dpi=150" -o evidence.png

# --- ingestion ---------------------------------------------------------------
curl -X POST localhost:18200/ingest/dry-run    # what WOULD be fetched; writes nothing
curl -X POST localhost:18200/ingest/run        # force a sweep; poll /health
curl -X POST localhost:18200/ingest/centrality # re-rank without re-parsing

# --- agent (needs a bearer token) --------------------------------------------
TOKEN=$(curl -s -X POST localhost:18000/auth/token | jq -r .access_token)
curl -N -X POST localhost:18001/agent/api/query/stream \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"Which trials evaluate telitacicept in IgA nephropathy?","tools":["eugene"]}'
```

---

## Regenerating this file

Routes come from the live specs, which is the only listing that cannot drift:

```bash
for p in 18000 18100 18200 18001; do curl -s "localhost:$p/openapi.json"; done
```

For the Next.js layer:

```bash
cd agents/eugene-agent-ui-next/app/api
for f in $(find . -name route.ts | sort); do
  echo "$(grep -oE 'export async function (GET|POST|PUT|DELETE|PATCH)' "$f" \
    | awk '{print $4}' | paste -sd,) $(dirname "$f" | sed 's|^\.|/api|')"
done
```
