# Eugene — Developer Guide: Request Flow for 5 Demo Questions

This document traces, end-to-end, how each of five demo questions travels from
the browser UI through the Next.js route handlers, the Agent web service, the
intent classifier, the LLM (OpenAI `gpt-4.1`), the tool layer (MCP graph tools
+ native live-data tools), and back to the UI as a streamed answer plus a live
reasoning graph.

> Audience: developers extending or operating Eugene.
> Scope: the **local Docker deployment** (`docker-compose.yml`). The AWS
> deployment is identical in flow; only hostnames differ.

---

## 1. System topology

| Component | Container | Port (host→container) | Tech |
|---|---|---|---|
| Next.js UI | `eugene-agent-ui-next` | 18502→18502 | Next.js 14 (App Router), Chakra UI, Cytoscape |
| Streamlit UI (legacy) | `eugene-agent-ui` | 18501→8501 | Streamlit |
| Agent web service | `eugene-agent-ws` | 18001→8000 | FastAPI + Strands agent |
| MCP server | `eugene-mcp` | 18443→8000 | FastMCP (streamable HTTP) |
| Core API | `eugene-ws` | 18000→8000 | FastAPI |
| Neo4j | `eugene-neo4j` | 17474 / 17687 | Neo4j 5.26 CE |

**Data-plane edges**
```
Browser ──HTTP──► Next.js UI (server routes) ──HTTP──► Agent WS ──┬─ streamable HTTP ─► MCP ──Bolt──► Neo4j
                                                                  ├─ HTTPS ─► OpenAI api.openai.com
                                                                  ├─ HTTPS ─► ClinicalTrials.gov
                                                                  ├─ HTTPS ─► Europe PMC
                                                                  └─ HTTPS ─► NCBI PubMed
Next.js UI ──HTTP──► Core API (eugene-ws) for /auth/token and /graph/* expand/path
```

---

## 2. Key files (the spine of every request)

| Layer | File |
|---|---|
| UI composer (chips, send) | `agents/eugene-agent-ui-next/components/chat/Composer.tsx` |
| UI chat state machine | `agents/eugene-agent-ui-next/hooks/useChatStream.ts` |
| UI API client | `agents/eugene-agent-ui-next/lib/api.ts` |
| UI route: token | `agents/eugene-agent-ui-next/app/api/auth/token/route.ts` |
| UI route: stream proxy | `agents/eugene-agent-ui-next/app/api/stream/route.ts` |
| UI route: readiness | `agents/eugene-agent-ui-next/app/api/health/route.ts` |
| UI stream parser | `agents/eugene-agent-ui-next/lib/streamParser.ts` |
| UI graph builder | `agents/eugene-agent-ui-next/lib/graphExtractor.ts` + `lib/graphApi.ts` |
| Agent app (FastAPI) | `agents/eugene-agent-ws/src/eugene_chat_ws.py` |
| Agent route | `agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py` |
| Intent classifier | `agents/eugene-agent-ws/src/query/util/intent_classifier.py` |
| Agent core (ReAct) | `agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py` |
| Agent factory | `agents/eugene-agent-ws/src/query/conf/conf.py` |
| LLM factory | `agents/eugene-agent-ws/src/query/infra/llm/llm_factory.py` |
| Native live tools | `agents/eugene-agent-ws/src/query/tools/external_tools.py` |
| MCP graph tools | `agents/eugene-mcp/src/tools/*.py` |
| Core API auth | `src/router/auth/auth_router.py`, `src/router/auth/eugene_jwts.py` |

---

## 3. The common request lifecycle (applies to all 5 questions)

Every question follows the same 11 steps. The per-question sections (§5) only
describe what is *different* — the intent result, the tools loaded, and the
ReAct tool sequence.

### Step 1 — Page load & token bootstrap
On mount, `useChatStream.ts` (`useEffect`, line ~41) calls `requestDevToken()`
→ `POST /api/auth/token`.

`app/api/auth/token/route.ts`:
- If `EUGENE_STATIC_TOKEN` env is set (AWS-against-prod mode) it returns that.
- Otherwise it proxies `POST {EUGENE_CORE_API_URL}/auth/token` (local mode →
  `http://eugene_ws:8000/auth/token`).
- The Core API mints an **HS256 JWT** signed with `EUGENE_CLIENT_SECRET`
  (`src/router/auth/eugene_jwts.py::issue_local_development_eugene_token_with_roles`),
  claims include `iss`, `aud`, `upn`, `roles`, `exp` (24h).
- The route stores it in an **httpOnly cookie `eugene_jwt`** and returns
  `{access_token, expires_in}`.
- UI flips `tokenReady = true` → status pill shows **authenticated** → composer
  enabled (`Composer disabled={!ready}`).

### Step 2 — User selects tool chips & types
`Composer.tsx` holds `tools: ToolSelection[]` (`"eugene" | "http" | "pubmed"`).
The chips map: **Eugene KG → `eugene`**, **Web → `http`**, **PubMed → `pubmed`**
(`components/chat/ToolChips.tsx`). On Enter/Send, `submit()` calls
`onSend(text, tools)` → `useChatStream.send`.

### Step 3 — Pre-flight readiness
`send()` first does `GET /api/health`. The route (`app/api/health/route.ts`)
probes the agent at `{EUGENE_AGENT_API_URL}/health/ready` → falls back to
`/health` → `/`; **any non-5xx = ready** (so a 404 doesn't block). Returns 200.

### Step 4 — Open the stream
`send()` appends a user message + an empty assistant message, then calls
`openStream({prompt, conversation_id, include_tools}, signal)` →
`POST /api/stream`.

`app/api/stream/route.ts`:
- Reads the `eugene_jwt` cookie, re-injects as `Authorization: Bearer <jwt>`.
- Proxies `POST {EUGENE_AGENT_API_URL}/query/stream` (local →
  `http://eugene_agent_ws:8000/agent/api/query/stream`).
- Streams the upstream body back **unbuffered** (`text/event-stream`).

### Step 5 — Agent route receives the request
FastAPI app (`eugene_chat_ws.py`) mounted at `root_path="/agent/api"`. Route
`chat_query_agent_router.py::chat_query_agent_as_stream` (`POST /query/stream`):
- Auth dependency validates the Bearer JWT and checks the **allowlist**
  (`router/auth/auth.py`; empty `EUGENE_AGENT_ALLOWLIST` = allow all).
- Pydantic validates `ChatQueryRequest {prompt, conversation_id, include_tools}`.
- Returns `StreamingResponse(generate_chat_response(token, chat_request))`.

### Step 6 — Intent classification
`generate_chat_response` (line ~110) calls:
```python
user_selected = _add_default_tools(chat_request.include_tools)   # dedupe, None-safe
intent        = classify_intent(prompt, user_selected)
tools         = intent.tools
```
`intent_classifier.py` merges the user's chip selection with keyword inference:
- `_GRAPH_RE` (drug/disease/gene/trial/organization/known entities) → adds `EUGENE`
- `_WEB_RE` (web/internet/latest/recent/…) / `_PATENT_RE` / `_PUBMED_RE` → adds `HTTP`
- empty → defaults to `EUGENE`

### Step 7 — Agent construction (per request)
`eugene_data_agent.execute_stream` → `_init_agent`:
- Builds the tool list based on `include_tools`:
  - `EUGENE` present → `mcp_client.list_tools_sync()` (the 12 MCP graph tools).
  - `HTTP` present → native tools: `search_pubmed`, `search_patents_web`,
    `search_clinical_trials`, `search_europepmc`, `http_request`.
- Instantiates a Strands `Agent(model, tools, system_prompt, conversation_manager,
  session_manager, callback_handler)`.
  - `model` = OpenAI `gpt-4.1` (via `conf.py::llm_model` → `LlmFactory.openai_model`).
  - `conversation_manager` = `SlidingWindowConversationManager(window_size=10)`.
  - `session_manager` = `FileSessionManager(session_id=conversation_id)` →
    persists multi-turn history under `/tmp/strands/sessions`.

### Step 8 — The LLM call (ReAct loop)
`agent.stream_async(user_prompt)` runs the **ReAct loop**. Each turn the model
receives this message list (OpenAI chat format):
```
[ system : <the big Eugene system prompt, see §4> ,
  ...prior turns (replayed by SlidingWindowConversationManager) ,
  user   : <prompt> ,
  ...assistant tool_use + tool result messages accumulate here as the loop runs ]
```
plus the JSON **tool schemas** (name, params, docstring) for every loaded tool.
The model emits `tool_use` blocks; Strands executes the matching Python tool and
appends a `tool_result`; the loop repeats until the model emits a final answer
or a guard fires.

### Step 9 — Guards (anti-runaway)
In `execute_stream._register_tool_call`:
- `_HARD_TOOL_CALL_BUDGET = 25` total calls.
- Duplicate-input detection (`_MAX_DUPLICATE_TOOL_CALLS = 2`) — **only when the
  tool_input is populated** (empty streamed inputs are skipped to avoid false
  positives).
- `_AGENT_STREAM_TIMEOUT_S = 180` wall-clock via `_with_timeout`.

### Step 10 — Streaming events back to the UI
The agent yields newline-delimited JSON envelopes:
```json
{"type":"session", "session_id":"…"}
{"type":"content", "content":"<token>", "session_id":"…"}
{"type":"tool_call", "tool":"…", "tool_input":{…}, "tool_id":"…"}
{"type":"tool_result", "tool_id":"…", "tool_output":[…]}
{"type":"done"}
```
- Text deltas come from the model.
- `tool_call` / `tool_result` are extracted mid-stream and **authoritatively
  re-harvested** from `agent.messages` after the stream
  (`_extract_tool_events`, `_harvest_messages`).
- `_flatten_tool_output` parses each tool result block: tries `json.loads`, then
  `ast.literal_eval` (native Strands tools return Python-repr dicts), else raw.

### Step 11 — UI render + reasoning graph
`streamParser.ts` splits the NDJSON; `useChatStream` dispatches by `type`:
- `content` → append to the assistant message bubble.
- `tool_call` → create a `ToolInvocation`, `extractor.ingest(inv)`.
- `tool_result` → attach output to the invocation, `extractor.ingest(inv)` again.
- The `GraphExtractor` (`lib/graphExtractor.ts`) + `normalizeApiResponse`
  (`lib/graphApi.ts`) deep-walk every tool input/output, emitting a graph node
  for any object carrying an ID key (`node_id`, `nct_id`, `pmid`, `patent_id`,
  …) and edges from adjacency dicts / edge triples. Cytoscape renders it in the
  **Eugene Workspace** panel.

---

## 4. The system prompt (sent as the `system` message every turn)

Defined in `eugene_data_agent.py::EugeneDataAgent.system_prompt`. Sections:
1. **Identity / scope** — "You are Eugene … biomedical competitive-intelligence …".
2. **ReAct directive** — Reason → Act → Observe; don't loop; stop when graph lacks data.
3. **TOOL GUIDE** — when to use which tool, including:
   - Organization assets = **two steps**: `find_organization_names` → `find_organization_assets` (never guess an id).
   - `fetch_facts` = indications/associations (NOT trials/neighbors); `fetch_node_relationships` = edges/neighbors/trials.
   - Clinical trials link to drugs/diseases, not gene/protein nodes.
   - **Live tools** (`search_clinical_trials`, `search_europepmc`, `search_pubmed`) preferred for "latest/recent/current/this year/search the web".
4. **HARD RULES** — never repeat a tool with identical args; ≤20 tool calls; don't invent data; cite `[node_id=…, tool=…]`.
5. **Citation requirement** — emit `[node_id=<id>, tool=<tool_name>]` so the UI can build the context graph.

---

## 5. The five questions, traced

For each: chips required → `include_tools` → intent result → tools loaded →
verified ReAct sequence → data sources → what renders.

---

### Q1 — "What assets does CSL Behring have?"
**Capability:** knowledge-graph traversal + reasoning-graph viz.

| Aspect | Value |
|---|---|
| Chips | Eugene KG (default) |
| `include_tools` | `["eugene"]` |
| Intent classifier | `_GRAPH_RE` matches "CSL"/"assets" → `tools=[EUGENE]` |
| Tools loaded | 12 MCP graph tools (no native tools) |

**ReAct sequence (verified):**
1. `find_organization_names("CSL Behring")` → MCP → Core API
   `GET /organizations/{name}` → returns orgs incl. `{node_id: 6b1e0f62918e, name: "CSL Behring"}`.
2. `find_organization_assets("6b1e0f62918e")` → MCP → Core API
   `GET /organizations/assets/6b1e0f62918e?page&page_size` → paginated assets
   (trials, drugs, diseases via `SPONSORS`/`evaluated_in`/`featured_in`).
3. Model composes the answer with `[organization_id=6b1e0f62918e, tool=find_organization_assets]` citation.

**Data source:** Neo4j (via MCP → Core API).
**Graph render:** org + asset nodes (org_id/drug_id/nct_id all carry IDs →
nodes); relationships from the assets payload → edges.
**Why it's a strong demo:** shows the mandatory **two-step id-resolution**
chain and live graph materialization from pure KG data.

---

### Q2 — "Find the gene-protein neighbors of Factor VIII and which clinical trials reference them."
**Capability:** multi-hop relationship reasoning.

| Aspect | Value |
|---|---|
| Chips | Eugene KG |
| `include_tools` | `["eugene"]` |
| Intent classifier | `_GRAPH_RE` matches "gene"/"protein"/"clinical trials"/"factor" → `[EUGENE]` |
| Tools loaded | 12 MCP graph tools |

**ReAct sequence (verified):**
1. `lookup_node_by_value("Factor VIII")` → MCP → Core API `GET /node/find/{value}`
   → `{node_id: 5d8cfcaf9ac7, label: gene_protein}`.
2. `fetch_node_relationships("5d8cfcaf9ac7")` → MCP → Core API
   `GET /graph/relationship/start/5d8cfcaf9ac7` → 9 neighbors + adjacency dict
   (Von Willebrand Factor, Thrombin, Protein C [gene_protein]; Hemlibra,
   Eloctate, Afstyla [drug]; Hemophilia A [disease]; Coagulation Cascade [pathway]).
3. `fetch_node_relationships(<each gene-protein neighbor id>)` — **different
   inputs each call** (this is what the false-positive loop-breaker fix enables).
4. Model concludes: gene/protein nodes have **no direct clinical-trial links**
   in the graph (trials attach to drugs/diseases) — reported honestly.

**Data source:** Neo4j.
**Graph render:** rich connected subgraph (~10 nodes, ~8 edges) from the
adjacency dict in step 2 (`normalizeApiResponse` Shape B).
**Engineering note:** this query is the regression test for the
**duplicate-call fingerprint bug** — multiple `fetch_node_relationships` calls
with empty streamed `tool_input` previously all hashed to
`fetch_node_relationships::{}` and tripped the breaker; the fix skips
fingerprinting when `tool_input` is empty.

---

### Q3 — "Find the latest recruiting clinical trials for emicizumab."
**Capability:** real-time clinical trials (headline feature).

| Aspect | Value |
|---|---|
| Chips | **Web** (enables `http`) |
| `include_tools` | `["eugene","http"]` |
| Intent classifier | "latest"/"recent" → `_WEB_RE` adds `HTTP`; "trials"/"emicizumab" → `EUGENE` |
| Tools loaded | 12 MCP tools **+** native `search_pubmed`, `search_patents_web`, `search_clinical_trials`, `search_europepmc`, `http_request` |

**ReAct sequence (verified):**
1. `search_clinical_trials("emicizumab", max_results=5)` →
   `GET https://clinicaltrials.gov/api/v2/studies?query.term=emicizumab&pageSize=5`
   → normalized to `{count, results:[{nct_id, title, status, phase, sponsor, conditions, url}]}`.
2. Model filters to **recruiting** and renders the list with NCT links,
   prefaced "live data from ClinicalTrials.gov".

**Data source:** ClinicalTrials.gov v2 (live, no key).
**Graph render:** each result has `nct_id` (in `ID_KEYS`) → CLINICAL_TRIAL nodes.
**Critical fix that makes the graph work:** native tools return Python dicts that
Strands serialized as `str(dict)` (single quotes); `_flatten_tool_output` now
falls back to `ast.literal_eval`, so the UI receives real objects (not opaque
strings) and the normalizer can walk them.

---

### Q4 — "Search the latest literature and patents on emicizumab."
**Capability:** real-time literature + patents.

| Aspect | Value |
|---|---|
| Chips | **Web + PubMed** |
| `include_tools` | `["eugene","http","pubmed"]` |
| Intent classifier | "latest" → `HTTP`; "patents"/"literature" → `_PATENT_RE`/`_PUBMED_RE` → `HTTP` |
| Tools loaded | MCP tools + all native live tools |

**ReAct sequence (verified):**
1. `search_europepmc("emicizumab", max_results=5)` →
   `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=emicizumab&format=json&pageSize=5`
   → `{count, results:[{id, source, title, authors, year, url}]}`.
2. `search_europepmc("emicizumab", patents_only=True)` → same endpoint with
   `query=emicizumab AND SRC:PAT` → patent documents.
   *(The model issues both calls — different `patents_only` args.)*
3. (Optional) `search_pubmed("emicizumab")` → NCBI E-utilities esearch+esummary.
4. Model merges and labels each section "live from Europe PMC / PubMed".

**Data source:** Europe PMC + NCBI PubMed (live, no keys).
**Graph render:** records carry `id`/`pmid` → literature/patent nodes.
**Note:** `search_patents_web` is intentionally a *link builder* (Google Patents
blocks scrapers); Europe PMC `SRC:PAT` is the real structured patent source.

---

### Q5 — "What does Eugene know about Hemophilia A, and what are the most recent trials for its treatments?"
**Capability:** static graph + live data fusion (the "wow" finish).

| Aspect | Value |
|---|---|
| Chips | **All** (Eugene KG + Web + PubMed) |
| `include_tools` | `["eugene","http","pubmed"]` |
| Intent classifier | "Hemophilia A"/"treatments" → `EUGENE`; "most recent" → `HTTP` |
| Tools loaded | MCP graph tools + all native live tools |

**ReAct sequence (verified):**
1. `lookup_node_by_value("Hemophilia A")` → `{node_id: 34c734063e8e, label: disease}`.
2. `fetch_facts("34c734063e8e")` → Core API `GET /graph/facts/start/34c734063e8e`
   → associated gene/protein (Factor VIII) + indicated drugs
   (Helixate FS, Afstyla, Hemlibra, Eloctate, Qfitlia, …).
3. `search_clinical_trials("Hemophilia A treatment")` → live ClinicalTrials.gov
   trials (NCT IDs, statuses, sponsors).
4. Model composes a **two-part answer**: KG facts (cited `[node_id=…, tool=fetch_facts]`)
   + live trials ("live data from ClinicalTrials.gov"), and even self-corrects
   (e.g. omits a Hemophilia B result as off-target).

**Data sources:** Neo4j (facts) **and** ClinicalTrials.gov (live trials) in one turn.
**Graph render:** Hemophilia A node + trial nodes. **Known limitation:** drugs
from `fetch_facts` come back as plain name *strings* (no IDs) so they appear in
the text but not as graph nodes; live trials have no edge back to the disease in
the source payload, so they render as nodes without a connecting edge.
**Why it's the finale:** one prompt, two data planes (curated graph + real-time
web), unified answer with provenance distinguishing the two.

---

## 6. Quick reference — what each chip changes

| Chip | `ToolSelection` | Effect on `_init_agent` tool list |
|---|---|---|
| Eugene KG | `eugene` | loads the 12 MCP graph tools (`fetch_*`, `find_organization_*`, `lookup_*`, `has_reachable_path`, `fetch_paths`) |
| Web | `http` | loads `search_clinical_trials`, `search_europepmc`, `search_pubmed`, `search_patents_web`, `http_request` |
| PubMed | `pubmed` | (today, same native bundle as Web; reserved for finer-grained gating later) |

The intent classifier can also *add* `HTTP` automatically from keywords even if
the Web chip is off — but for the demo, toggle the chips explicitly so behavior
is deterministic.

---

## 7. Environment variables that govern the flow

| Var | Where | Purpose |
|---|---|---|
| `EUGENE_CORE_API_URL` | UI | base for `/auth/token` + `/graph/*` (local: `http://eugene_ws:8000`) |
| `EUGENE_AGENT_API_URL` | UI | base for `/health` + `/query/stream` (local: `http://eugene_agent_ws:8000/agent/api`) |
| `EUGENE_STATIC_TOKEN` | UI | optional — return a fixed JWT (AWS-against-prod mode) |
| `EUGENE_MCP_SERVER_URL` | Agent | MCP endpoint (local: `http://eugene_mcp:8000/mcp`) |
| `LLM_PROVIDER` / `OPENAI_MODEL_ID` | Agent | `openai` / `gpt-4.1` |
| `OPENAI_API_KEY` | Agent | LLM auth |
| `EUGENE_CLIENT_SECRET` | Core+Agent | shared HS256 JWT signing/verification |
| `EUGENE_AGENT_ALLOWLIST` | Agent | pipe-separated UPNs; empty = allow all |
| `NEO4J_URI` / `NEO4J_PASSWORD` | Core+MCP | graph connection (local: `bolt://neo4j:7687`) |

---

## 8. Sequence diagram (Q3 as the canonical live example)

```
Browser           Next.js UI            Agent WS              OpenAI         ClinicalTrials.gov
   │  type prompt     │                     │                    │                  │
   │ ───────────────► │                     │                    │                  │
   │                  │ POST /api/health    │                    │                  │
   │                  │ ──► /agent/api/health/ready (200)        │                  │
   │                  │ POST /api/stream    │                    │                  │
   │                  │ ──Bearer JWT──► POST /agent/api/query/stream                │
   │                  │                     │ classify_intent → [eugene,http]       │
   │                  │                     │ _init_agent(+native tools)            │
   │                  │                     │ stream_async(prompt)                  │
   │                  │                     │ ───system+user+tool schemas──► │       │
   │                  │                     │ ◄──tool_use: search_clinical_trials── │
   │                  │                     │ search_clinical_trials() ──GET studies──────────► │
   │                  │                     │ ◄──────────── JSON trials ───────────────────────│
   │                  │                     │ ───tool_result──► │ (model writes answer)        │
   │                  │ ◄═ NDJSON: session/content/tool_call/tool_result/done ═     │
   │ ◄═ render bubble + graph nodes ═       │                    │                  │
```

---

## 9. Extending the flow (cheat-sheet)

- **New live tool:** add an `@tool` fn in `external_tools.py`, import it in
  `eugene_data_agent.py`, append to the `HTTP` branch in `_init_agent`, document
  it in the system prompt's TOOL GUIDE. Ensure the return dict has an ID-bearing
  key so the graph renders it.
- **New MCP graph tool:** add it under `agents/eugene-mcp/src/tools/`, register
  it; the agent picks it up via `list_tools_sync()` — no agent code change.
- **New chip:** add to `ToolSelection` (`lib/types.ts`), `ToolChips.tsx`,
  `ToolRequestEnum` (agent), and gate it in `_init_agent`.
```
