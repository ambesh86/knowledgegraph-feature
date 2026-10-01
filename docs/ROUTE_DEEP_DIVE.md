# Eugene: End-to-End Route Deep Dive
## Route: `POST /agent/api/query/stream`
### Example Query: *"What are the relationships of Hemophilia A?"*

> **Audience:** Python & Agent Developers
> **Purpose:** Understand exactly what happens — function by function, layer by layer — when a user types a question in the Chat UI and gets a streamed answer back.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer 1 — Streamlit UI](#2-layer-1--streamlit-ui)
3. [Layer 2 — Agent Backend (FastAPI Router)](#3-layer-2--agent-backend-fastapi-router)
4. [Layer 3 — EugeneDataAgent (Strands Agent)](#4-layer-3--eugenedataagent-strands-agent)
5. [Layer 4 — MCP Server (FastMCP Tools)](#5-layer-4--mcp-server-fastmcp-tools)
6. [Layer 5 — Core API (eugene_ws)](#6-layer-5--core-api-eugene_ws)
7. [Layer 6 — Neo4j Graph Database](#7-layer-6--neo4j-graph-database)
8. [Response: Streaming Back to the User](#8-response-streaming-back-to-the-user)
9. [Full Call Chain Summary](#9-full-call-chain-summary)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 1         LAYER 2          LAYER 3      LAYER 4    LAYER 5  LAYER 6│
│                                                                           │
│  Streamlit  ──►  Agent Backend ──► Strands  ──► MCP    ──► Core  ──► Neo4j│
│  UI             (FastAPI)          Agent        Server     API           │
│  :18501         :18001             (in-proc)    :18443     :18000   :17687│
└──────────────────────────────────────────────────────────────────────────┘
```

The system uses a **ReAct (Reason → Act → Observe)** pattern:
- The **LLM reasons** about what data it needs
- It **acts** by calling MCP tools
- It **observes** the tool results
- It repeats until it can generate a complete answer

---

## 2. Layer 1 — Streamlit UI

**File:** `agents/eugene-agent-ui/src/eugene_agent_ui.py`
**Port:** `http://localhost:18501`

### What happens

The user types in the chat box:

```
"What are the relationships of Hemophilia A?"
```

Streamlit captures this via `st.chat_input()` and calls `display_streamed_response()`.

### Key Functions

#### `display_streamed_response(api_endpoint, prompt)`
```python
async def display_streamed_response(api_endpoint: str, prompt: str):
    full_response = ""
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        async for chunk in stream_response(
            api_endpoint,
            prompt,
            st.session_state.conversation_id,   # UUID persisted in session
            st.session_state.selected_tools,     # e.g. ["eugene"]
            st.session_state.get("oauth_token"), # Bearer token from sidebar
        ):
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")   # live cursor
        message_placeholder.markdown(full_response)              # final answer
```

#### `stream_response(api_endpoint, prompt, conversation_id, include_tools, oauth_token)`
```python
async def stream_response(...) -> AsyncGenerator[str, None]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}",   # JWT from /login page
    }
    async with httpx.AsyncClient(verify=False) as client:
        async with client.stream(
            "POST",
            api_endpoint,   # http://eugene_agent_ws:8000/agent/api/query/stream
            json={
                "prompt": "What are the relationships of Hemophilia A?",
                "conversation_id": "a1b2c3d4-...",    # UUID
                "include_tools": ["eugene"],           # selects which MCP tools
            },
            headers=headers,
            timeout=120,
        ) as response:
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk     # each text chunk rendered immediately
```

### State held in session
| Key | Value | Purpose |
|---|---|---|
| `conversation_id` | UUID string | Groups messages into one conversation |
| `selected_tools` | `["eugene"]` | Controls which MCP toolsets are loaded |
| `oauth_token` | Bearer JWT | Passed to every API call |
| `messages` | list of dicts | Chat history displayed in UI |

---

## 3. Layer 2 — Agent Backend (FastAPI Router)

**File:** `agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py`
**Port:** `http://localhost:18001`
**Full Route:** `POST /agent/api/query/stream`

### Request arrives

FastAPI receives the HTTP POST. Two FastAPI `Depends()` run **before** the handler:

#### Step 1 — Extract token: `get_current_token()`
```python
# Extracts raw JWT string from Authorization header
token: str = Depends(get_current_token)
# → returns "eyJhbGciOiJIUzI1NiIs..."
```

#### Step 2 — Validate user: `get_current_user()`
```python
# Validates JWT signature + required claims
user: dict = Depends(get_current_user)
# calls validate_eugene_access_token(token)
# checks: tid, sub, roles, upn fields exist
# → returns {"upn": "eugene.test@cslbehring.com", "roles": ["user.public.read"], ...}
```

#### Step 3 — Validate request: `validate_chat_query_request()`
```python
# Pydantic AfterValidator runs these checks:
# - prompt length ≤ 2048 chars
# - conversation_id is valid UUID format
# - no special injection characters
```

#### Step 4 — Route handler: `chat_query_agent_as_stream()`
```python
@router.post("/query/stream")
async def chat_query_agent_as_stream(
    chat_request: ChatQueryRequest,
    token: str = Depends(get_current_token),
    user: dict = Depends(get_current_user),
):
    logger.info(f"streaming chat query user: {user['upn']}")
    return StreamingResponse(
        generate_chat_response(token, chat_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff",
        },
    )
```

The response is **not buffered** — it is a `StreamingResponse` backed by an async generator. Text arrives at the browser word-by-word as the LLM generates it.

#### Step 5 — Async generator: `generate_chat_response()`
```python
@log_time
async def generate_chat_response(token, chat_request) -> AsyncGenerator[str, None]:
    prompt = chat_request.prompt.strip()
    tools = _add_default_tools(chat_request.include_tools)
    async for chunk in eugene_agent.execute_stream(
        token=token,
        user_prompt=prompt,
        conversation_id=chat_request.conversation_id,
        include_tools=tools,
    ):
        content = chunk["content"]
        yield content        # each dict chunk → plain text string sent to client
```

### `ChatQueryRequest` model
```python
class ChatQueryRequest:
    prompt: str              # "What are the relationships of Hemophilia A?"
    conversation_id: str     # "a1b2c3d4-0000-..."
    include_tools: list      # ["eugene"]
```

---

## 4. Layer 3 — EugeneDataAgent (Strands Agent)

**File:** `agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py`
**Class:** `EugeneDataAgent`

This is the **brain** of the system. It wraps the Strands agent framework and orchestrates the ReAct loop.

### Initialisation (at startup, once)

```python
# In conf.py — called once when the service boots
eugene_agent = EugeneDataAgent(
    eugene_mcp_server_url="http://eugene_mcp:8000/mcp",
    model=<OpenAIModel or AnthropicModel>,   # from LLM_PROVIDER env var
)
self.conversation_manager = SlidingWindowConversationManager(
    window_size=10,              # keep last 10 turns in context
    should_truncate_results=True,
    per_turn=2,
)
```

**System Prompt (hardcoded):**
```
You are an agent tasked with helping investigate biomedical companies to assess
competitive threat and collaboration opportunities.
In our case assets here mean any drug, disease, patents, clinical trials,
intellectual property, or financial deals the company may have involvement.
As an agent follow the Reason, Act, Observe (ReAct) pattern.
You are an agent that may call tools to retrieve data.
```

### `execute_stream()` — the main entry point

```python
async def execute_stream(
    self,
    token: str,
    user_prompt: str,
    conversation_id: str,
    include_tools: list[ToolRequestEnum],
) -> AsyncGenerator[dict[str, str], None]:

    # Step 1: initialise tools + agent for THIS request
    agent = self._init_agent(token, conversation_id, include_tools)

    # Step 2: emit session event so UI knows the conversation ID
    yield {"type": "session", "session_id": conversation_id, "content": ""}

    # Step 3: open MCP connection and run the ReAct loop
    with self.eugene_mcp_client:
        async for event in agent.stream_async(user_prompt):
            if "data" in event:
                yield {
                    "type": "content",
                    "content": event["data"],    # LLM text token(s)
                    "session_id": conversation_id,
                }

    # Step 4: signal completion
    yield {"type": "done", "content": "", "session_id": conversation_id}
```

### `_init_agent()` — builds the Strands Agent

```python
def _init_agent(self, token, conversation_id, include_tools) -> Agent:
    self._init_tool_clients(token=token)   # creates MCPClient with Bearer token

    with self.eugene_mcp_client:
        # Load tools from MCP server
        mcp_tools = []
        if ToolRequestEnum.EUGENE in include_tools:
            mcp_tools.extend(self.eugene_mcp_client.list_tools_sync())
            # → fetches 12 tool schemas from http://eugene_mcp:8000/mcp

        # Local tools (no MCP needed)
        local_tools = [calculator, current_time, python_repl]

        tools = [*mcp_tools, *local_tools]

    session_manager = FileSessionManager(session_id=conversation_id)
    # → writes conversation history to local file system

    return Agent(
        name="EugeneDataAgent",
        tools=tools,                              # all 12 MCP + 3 local
        model=self.model,                         # Claude / GPT-4.1-mini
        system_prompt=self.system_prompt,
        callback_handler=debugger_callback_handler,
        conversation_manager=self.conversation_manager,   # sliding window
        session_manager=session_manager,
    )
```

### `_init_tool_clients()` — MCP connection with auth

```python
def _init_tool_clients(self, token: str) -> None:
    self.eugene_mcp_client = MCPClient(
        lambda: streamable_http_client(
            url=self.eugene_mcp_server_url,    # http://eugene_mcp:8000/mcp
            http_client=httpx.AsyncClient(
                verify=False,
                headers={"Authorization": f"Bearer {token}"}
                # ↑ The user's JWT is forwarded to MCP server
            ),
        )
    )
```

### The ReAct Loop (what Strands does internally)

For the query *"What are the relationships of Hemophilia A?"*, the LLM reasons through multiple steps:

```
ITERATION 1:
  REASON: I need to find the node_id for "Hemophilia A" before I can query relationships.
  ACT:    Call tool → lookup_node_by_value(value="Hemophilia A", fuzzy_match=True)
  OBSERVE: { node_id: "abc123", label: "Disease", value: "Hemophilia A" }

ITERATION 2:
  REASON: I have node_id "abc123". Now I can get relationships at 2-hop depth.
  ACT:    Call tool → fetch_node_relationships(node_id="abc123", n_hop=2)
  OBSERVE: { count: 47, results: [drugs, trials, patents, orgs...] }

ITERATION 3:
  REASON: I have enough data to generate a comprehensive answer.
  ACT:    Generate streaming text response.
```

---

## 5. Layer 4 — MCP Server (FastMCP Tools)

**File:** `agents/eugene-mcp/src/eugene_mcp.py`
**Port:** `http://localhost:18443`
**Transport:** `streamable-http` (MCP protocol over HTTP)

### Server setup

```python
mcp = FastMCP(
    name="EUGENE Knowledge Graph MCP Server",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,                     # no server-side session state
    auth=eugene_jwt_verifier(),              # validates incoming JWT
    middleware=[AuthMiddleware(auth=require_auth)],
)
mcp.run(transport="streamable-http")
```

### 12 Registered Tools

| Tool | Class | What it does |
|---|---|---|
| `fetch_identity` | `EugeneIdentityTools` | Who is the current user |
| `fetch_by_label` | `EugeneFetchTools` | List all nodes of a label (drug/disease) |
| `fetch_similar` | `EugeneFetchTools` | Semantic similarity search |
| `lookup_node_by_value` | `EugeneNodeTools` | Translate name → node_id |
| `fetch_node_details` | `EugeneNodeTools` | Get node properties by IDs |
| `fetch_drug_aliases` | `EugeneDrugTools` | Drug brand/generic name aliases |
| `fetch_facts` | `EugeneFactTools` | Facts linked to a node |
| `fetch_node_relationships` | `EugeneGraphTools` | N-hop graph traversal |
| `has_reachable_path` | `EugeneGraphTools` | Boolean: path exists between nodes? |
| `fetch_paths` | `EugeneGraphTools` | All paths between two nodes |
| `find_organization_names` | `EugeneOrganizationTools` | Search org names by pattern |
| `find_organization_assets` | `EugeneOrganizationTools` | Assets of an organisation |

### Tool call: `lookup_node_by_value`

**File:** `agents/eugene-mcp/src/tools/eugene_node_tools.py`

```python
@staticmethod
async def lookup_node_by_value(
    value: str,
    fuzzy_match: bool = False
) -> list[dict] | dict | str:
    """
    find node by value

    Lookup a node id for any type of node, including;
    drug, disease, gene protein, exposure, pathway, anatomy, molecular function
    """
    token = extract_token()      # pulls JWT from incoming HTTP request headers
    if not token:
        return CONTEXT_TOKEN_ERROR_MSG

    url = f"{EUGENE_API_BASE}/node/find/{value}"
    params = {"fuzzy_match": str(fuzzy_match)}
    data = await make_eugene_request(token=token, url=url, params=params)

    if not data:
        return f"Unable to fetch node with {value}"
    return data
```

### Token extraction: `extract_token()`

**File:** `agents/eugene-mcp/src/util/context.py`

```python
def extract_token() -> str | None:
    from fastmcp.server.dependencies import get_http_request
    request = get_http_request()                        # FastMCP injects HTTP context
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]
    return token
    # The token was set by _init_tool_clients() in the agent layer
    # It travels: UI → AgentWS → MCPClient → MCP Server header
```

### HTTP call to Core API: `make_eugene_request()`

**File:** `agents/eugene-mcp/src/util/request.py`

```python
async def make_eugene_request(
    token: str,
    url: str,
    params: dict[str, str] | None = None
) -> list[dict] | dict | None:
    headers = {
        "User-Agent": "eugene-mcp/1.0",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",    # JWT forwarded again to Core API
    }
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
```

**Actual HTTP request sent:**
```
GET http://eugene_ws:8000/node/find/Hemophilia%20A?fuzzy_match=True
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Tool call: `fetch_node_relationships`

**File:** `agents/eugene-mcp/src/tools/eugene_graph_tools.py`

```python
@staticmethod
async def fetch_node_relationships(
    node_id: str,
    n_hop: int = 2
) -> list[dict] | dict | str:
    """
    Fetch relationships for a node.

    For a drug: includes indications, contraindications, off-label uses
    For a disease: includes genes, proteins, drugs
    """
    token = extract_token()
    if not token:
        return CONTEXT_TOKEN_ERROR_MSG

    url = f"{EUGENE_API_BASE}/graph/relationship/start/{node_id}"
    params = {"n_hop": str(n_hop)}
    data = await make_eugene_request(token=token, url=url, params=params)

    if not data:
        return f"Unable to fetch relationships for node {node_id}"
    return data
```

**Actual HTTP request sent:**
```
GET http://eugene_ws:8000/graph/relationship/start/abc123?n_hop=2
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 6. Layer 5 — Core API (eugene_ws)

**Port:** `http://localhost:18000`
**Framework:** FastAPI + Uvicorn

### Route 1: `GET /node/find/{node_value}`

**File:** `src/foundation/router/node_id_lookup_router.py`

```python
router = APIRouter(prefix="/node", tags=["foundation"])
node_id_provider = foundational_node_id_provider()   # DI at startup

@router.get("/find/{node_value}")
async def lookup_node_id_by_value(
    node_value: str,          # "Hemophilia A"
    fuzzy_match: bool = False,
):
    return node_id_provider.find_node_id_by_node_name(
        value=node_value,
        fuzzy_match=fuzzy_match,
    )
```

**Provider:** `FoundationalNodeIdProvider`
**Adapter:** `Neo4jFoundationalNodeAdapter`
**Cypher:**
```cypher
MATCH (n { node_name: $value })
RETURN n.node_id AS node_id, n.node_name AS node_name, labels(n) AS labels
```
For fuzzy: uses `=~` regex operator instead of exact match.

---

### Route 2: `GET /graph/relationship/start/{start_id}`

**File:** `src/foundation/router/n_hop_router.py`

```python
router = APIRouter(prefix="/graph", tags=["foundation"])
n_hop_provider = foundational_n_hop_provider()   # DI at startup

@router.get("/relationship/start/{start_id}")
async def find_n_hop(
    start_id: str,         # "abc123"
    end_id: str | None = None,
    n_hop: int = 1,        # 2 in our example
):
    return n_hop_provider.find_subgraph_by_start_id_and_end_id(
        start_id=start_id,
        end_id=end_id,
        n_hop=n_hop,
    )
```

### Provider: `FoundationalNHopProvider`

**File:** `src/foundation/provider/foundational_n_hop_provider.py`

```python
class FoundationalNHopProvider:
    MAX_RESULT_COUNT = 10_000

    def find_subgraph_by_start_id_and_end_id(
        self, start_id, n_hop, page=1, page_size=MAX_RESULT_COUNT, end_id=None
    ) -> Graph | None:
        df = self.neo4j_foundational_n_hop_adapter.collect_by_start_id_and_end_id(
            start_id=start_id,
            end_id=end_id,
            n_hop=n_hop,
            page=page,
            page_size=page_size,
        )
        self._ensure_result_size_or_raise(df)     # guard: max 10,000 rows
        return self.graph_mapper.map(df=df)       # DataFrame → Graph model
```

### Adapter: `Neo4jFoundationalNHopAdapter`

**File:** `src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py`

```python
class Neo4jFoundationalNHopAdapter:
    MAX_SUPPORTED_HOPS = 2    # hard cap at 2-hop (graph is highly connected)

    def _build_n_hop_by_id_query(
        self, n_hop, page, page_size, include_end_condition=False
    ) -> str:
        return """
            MATCH (startNode { node_id: $start_id })-[r]-{0,%s}(endNode%s)
            UNWIND(r) AS rel
            RETURN DISTINCT
                startNode(rel).node_name AS startName,
                toStringOrNull(startNode(rel).node_id) AS startId,
                labels(startNode(rel)) AS startLabels,
                endNode(rel).node_name AS endName,
                toStringOrNull(endNode(rel).node_id) AS endId,
                labels(endNode(rel)) AS endLabels,
                type(rel) AS relType
            ORDER BY startName
            SKIP %s
            LIMIT %s
        """ % (n_hop, "{ node_id: $end_id }" if include_end_condition else "",
               offset, limit)

    def _collect_n_hop(self, query, params) -> DataFrame | None:
        records = self.driver.execute_query(
            query_=query,
            parameters_=params,
            result_transformer_=neo4j.Result.to_df,   # returns pandas DataFrame
        )
        return records
```

### Dependency Injection (DI) chain at startup

The Core API uses **manual DI via factory functions** in `conf.py` — no framework:

```
foundational_n_hop_provider()
    └── Neo4jFoundationalNHopAdapter(driver=neo4j_driver())
    └── GraphMapper()
```

All objects are created **once at startup** and reused for every request.

---

## 7. Layer 6 — Neo4j Graph Database

**Port:** `bolt://localhost:17687`
**Browser:** `http://localhost:17474`
**Version:** Neo4j 5.26.9 Community with APOC plugin

### Cypher Query executed for our example

```cypher
-- Step 1: Find node_id for "Hemophilia A"
MATCH (n { node_name: $value })
RETURN n.node_id AS node_id, n.node_name AS node_name, labels(n) AS labels

-- Parameters: { "value": "Hemophilia A" }
-- Result:     { "node_id": "abc123", "node_name": "Hemophilia A", "labels": ["Disease"] }
```

```cypher
-- Step 2: Find all 2-hop relationships from Hemophilia A node
MATCH (startNode { node_id: $start_id })-[r]-{0,2}(endNode)
UNWIND(r) AS rel
RETURN DISTINCT
    startNode(rel).node_name  AS startName,
    toStringOrNull(startNode(rel).node_id) AS startId,
    labels(startNode(rel))    AS startLabels,
    endNode(rel).node_name    AS endName,
    toStringOrNull(endNode(rel).node_id)   AS endId,
    labels(endNode(rel))      AS endLabels,
    type(rel)                 AS relType
ORDER BY startName
SKIP 0
LIMIT 10000

-- Parameters: { "start_id": "abc123" }
-- Example results:
-- startName      | relType           | endName               | endLabels
-- Hemophilia A   | HAS_INDICATION    | Emicizumab            | [Drug]
-- Hemophilia A   | STUDIED_IN        | NCT01214096           | [ClinicalTrial]
-- Hemophilia A   | PATENTED_BY       | Roche                 | [Organisation]
-- Emicizumab     | TARGETS           | Factor IXa            | [GeneProtein]
```

### Node Labels in the Eugene Graph

| Label | Example | Description |
|---|---|---|
| `Drug` | Emicizumab | Therapeutic drug |
| `Disease` | Hemophilia A | Medical condition |
| `GeneProtein` | Factor VIII | Gene or protein target |
| `ClinicalTrial` | NCT01214096 | Clinical study |
| `Patent` | US10344093 | Intellectual property |
| `Organisation` | Roche | Company |
| `Anatomy` | Liver | Body part |
| `Pathway` | Coagulation cascade | Biological pathway |

### Relationship Types

| Relationship | Meaning |
|---|---|
| `HAS_INDICATION` | Drug treats Disease |
| `TARGETS` | Drug/Trial targets GeneProtein |
| `STUDIED_IN` | Disease studied in ClinicalTrial |
| `PATENTED_BY` | Drug/Trial patented by Organisation |
| `ASSOCIATED_WITH` | General association |
| `CONTRAINDICATED_FOR` | Drug contraindicated for Disease |

---

## 8. Response: Streaming Back to the User

The response travels back through the same layers in reverse.

### How Neo4j result becomes a streaming UI response

```
Neo4j DataFrame
    │
    ▼ GraphMapper.map(df)
Graph model { nodes: [...], relationships: [...] }
    │
    ▼ FastAPI JSON serialization
HTTP 200 JSON body  →  MCP tool returns dict to Strands
    │
    ▼ Strands Agent observes tool result
LLM generates text: "Hemophilia A has 47 relationships including..."
    │
    ▼ agent.stream_async() yields events
{ "data": "Hemophilia A" }
{ "data": " has 47" }
{ "data": " relationships..." }
    │
    ▼ EugeneDataAgent.execute_stream() wraps each event
{ "type": "content", "content": "Hemophilia A", "session_id": "..." }
    │
    ▼ generate_chat_response() yields content string
"Hemophilia A"
    │
    ▼ FastAPI StreamingResponse (text/event-stream)
HTTP chunks arrive at Streamlit UI
    │
    ▼ stream_response() aiter_text()
chunk → full_response += chunk
message_placeholder.markdown(full_response + "▌")   # live update
    │
    ▼ Final render
message_placeholder.markdown(full_response)         # complete answer
```

### SSE Event types yielded by `execute_stream()`

| Event type | When emitted | Content |
|---|---|---|
| `session` | First, immediately | Empty — carries `session_id` |
| `content` | Every LLM token | The actual text fragment |
| `done` | After final token | Empty — signals completion |
| `error` | On exception | Error message string |

---

## 9. Full Call Chain Summary

```
User types: "What are the relationships of Hemophilia A?"
│
├─ [UI] eugene_agent_ui.py
│    stream_response()  →  POST /agent/api/query/stream
│    Headers: Authorization: Bearer <token>
│    Body: { prompt, conversation_id, include_tools: ["eugene"] }
│
├─ [AgentWS] chat_query_agent_router.py
│    get_current_token()          → extract JWT
│    get_current_user()           → validate JWT, get upn
│    validate_chat_query_request()→ prompt ≤ 2048, valid UUID
│    chat_query_agent_as_stream() → StreamingResponse
│    generate_chat_response()     → async generator
│
├─ [Agent] eugene_data_agent.py : EugeneDataAgent
│    execute_stream()
│    ├─ _init_tool_clients()      → MCPClient(Bearer token forwarded)
│    ├─ _init_agent()
│    │    ├─ list_tools_sync()    → fetch 12 tool schemas from MCP
│    │    ├─ FileSessionManager   → load/save conversation history
│    │    └─ Agent(tools, model, system_prompt, conversation_manager)
│    └─ agent.stream_async(prompt)
│         [ReAct Iteration 1]
│         REASON: need node_id for "Hemophilia A"
│         ACT:    tool call → lookup_node_by_value("Hemophilia A", fuzzy=True)
│         OBSERVE: node_id = "abc123"
│         [ReAct Iteration 2]
│         REASON: now fetch relationships
│         ACT:    tool call → fetch_node_relationships("abc123", n_hop=2)
│         OBSERVE: 47 relationships returned
│         [ReAct Iteration 3]
│         REASON: enough context, generate answer
│         ACT:    stream LLM text tokens
│
├─ [MCP] eugene_mcp.py / eugene_node_tools.py / eugene_graph_tools.py
│    lookup_node_by_value()
│    ├─ extract_token()           → pull JWT from request header
│    └─ make_eugene_request()     → GET /node/find/Hemophilia A?fuzzy_match=True
│
│    fetch_node_relationships()
│    ├─ extract_token()
│    └─ make_eugene_request()     → GET /graph/relationship/start/abc123?n_hop=2
│
├─ [CoreAPI] node_id_lookup_router.py / n_hop_router.py
│    lookup_node_id_by_value()    → node_id_provider.find_node_id_by_node_name()
│    find_n_hop()                 → n_hop_provider.find_subgraph_by_start_id_and_end_id()
│
├─ [Provider] foundational_n_hop_provider.py
│    find_subgraph_by_start_id_and_end_id()
│    ├─ neo4j_adapter.collect_by_start_id_and_end_id()
│    └─ graph_mapper.map(df)
│
├─ [Adapter] neo4j_foundational_n_hop_adapter.py
│    _build_n_hop_by_id_query()   → parametrised Cypher string
│    driver.execute_query()       → pandas DataFrame
│
└─ [Neo4j] bolt://neo4j:7687
     MATCH (startNode { node_id: $start_id })-[r]-{0,2}(endNode)
     → returns 47 rows of relationships
     → streamed back through all layers as text tokens
```

---

## 10. Key Design Decisions

### 1. Token passthrough (no re-authentication)
The user's JWT travels from UI → AgentWS → MCPClient headers → MCP server → Core API headers. No service re-issues tokens. All layers validate the same JWT.

### 2. Manual Dependency Injection
The Core API uses factory functions in `conf.py` instead of a DI framework. All providers, adapters, and mappers are instantiated **once at startup** and shared across requests.

### 3. Stateless MCP (`stateless_http=True`)
The MCP server holds no per-request state. Each tool call is self-contained — token extracted from the incoming HTTP request, used once, discarded.

### 4. Conversation memory via files
`FileSessionManager(session_id=conversation_id)` writes conversation turns to disk. `SlidingWindowConversationManager(window_size=10)` keeps only the last 10 turns in the LLM context window, preventing token overflow.

### 5. Max 2 hops enforced at adapter level
```python
MAX_SUPPORTED_HOPS = 2
```
The Eugene graph is highly connected. A 3-hop query could return the entire graph. The adapter enforces this hard limit before sending any Cypher query.

### 6. Streaming over JSON
Instead of waiting for the full LLM response (which can take 10–30 seconds), `StreamingResponse` + `aiter_text()` deliver each token as it is generated, giving users a ChatGPT-like experience.
