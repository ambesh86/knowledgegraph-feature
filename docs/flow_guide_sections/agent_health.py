"""ReportLab section: Eugene agent-ws health route end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 5-7 PDF pages.

This guide covers the agent-ws variant of the health route, which is
distinct from the eugene-ws (src) health route: it probes MCP server
reachability and validates LLM API key presence in addition to a
JWT-signing-secret check.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_AGENT_HEALTH_FLOW_GUIDE.pdf"
TITLE = "Eugene Agent Health Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------- title --------------------------------- #
    ready_endpoint = h.c('GET /health/ready')
    live_endpoint = h.c('GET /health')
    mcp_env = h.c('EUGENE_MCP_SERVER_URL')
    secret_env = h.c('EUGENE_CLIENT_SECRET')
    anthro_env = h.c('ANTHROPIC_API_KEY')
    openai_env = h.c('OPENAI_API_KEY')
    root_path_lit = h.c('root_path=&quot;/agent/api&quot;')

    story += [
        h.p("Eugene Agent Health Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP probe &rarr; FastAPI router &rarr; "
            "LLM key + MCP /health probe + JWT secret &rarr; JSON status "
            "envelope &rarr; k8s readiness gating for the chat UI",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers wiring up container healthchecks or k8s readiness "
            "probes against eugene-agent-ws &mdash; the WebSocket / REST "
            "agent tier that the Next.js chat UI talks to. This is the "
            "sibling of the eugene-ws health route, but it has a different "
            "dependency surface: there is no Neo4j driver here, the agent "
            "instead depends on an LLM provider and on the eugene-mcp "
            "server. Every reference uses the form "
            f"{h.c('path/to/file.py:line')}.",
        ),
        h.p("How this differs from the src (eugene-ws) health route", h.H2),
        *h.bullets([
            "Same two-endpoint split (liveness vs readiness) and same "
            f"{h.c('OK')}/{h.c('DEGRADED')} envelope shape, so orchestrator "
            "wiring is identical.",
            f"Service identifier is {h.c('eugene-agent-ws')}, not "
            f"{h.c('eugene-ws')} &mdash; useful when scraping mixed logs.",
            f"Readiness checks three things instead of one: LLM provider "
            f"key ({anthro_env} or {openai_env}), MCP reachability "
            f"({mcp_env}), and JWT signing secret ({secret_env}).",
            f"FastAPI app mounts under {root_path_lit}, so the URLs "
            f"exposed to the outside are {h.c('/agent/api/health')} and "
            f"{h.c('/agent/api/health/ready')} (the router itself still "
            f"declares unprefixed {h.c('/health')} paths).",
        ]),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{live_endpoint} &mdash; liveness probe. Returns 200 with a "
            "constant dict as long as the uvicorn process is accepting "
            "requests. No env reads, no IO.",
            f"{ready_endpoint} &mdash; readiness probe. Returns 200 only "
            "when (a) at least one LLM API key is present, (b) the MCP "
            f"server at {mcp_env} answers its own {h.c('/health')} with a "
            f"status code below 500, and (c) {secret_env} is configured. "
            "Otherwise 503 with a per-check diagnostic envelope.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 0. probe model -------------------------------- #
    story += [
        h.p("0. Probe model (read this first)", h.H1),
        h.p(
            "This route has no Neo4j schema of its own; the &quot;model&quot; "
            "is the contract between the HTTP probe, the orchestrator, and "
            "the agent's external dependencies. Four rules:"
        ),
        *h.bullets([
            f"<b>Liveness is side-effect free.</b> {live_endpoint} returns "
            "a constant dict. It must not call MCP, must not check env "
            "vars, must not reach out to the LLM provider &mdash; any of "
            "those would couple liveness to a downstream failure and turn "
            "transient outages into restart-storms.",
            f"<b>Readiness exercises real dependencies.</b> "
            f"{ready_endpoint} actually opens an httpx client and GETs "
            f"the MCP server's own health endpoint. A passing probe "
            "therefore proves not just &quot;URL is set&quot; but "
            "&quot;the MCP container is up and answering on the "
            "configured URL&quot;.",
            f"<b>LLM key presence, not LLM call.</b> The readiness probe "
            f"checks {anthro_env}/{openai_env} <i>existence</i> only. It "
            "does not round-trip to Anthropic or OpenAI &mdash; that would "
            "cost money on every probe and couple readiness to a third "
            "party's uptime. A wrong key still passes readiness; the "
            "first chat turn will surface it.",
            f"<b>Status envelope is structured.</b> The response carries "
            f"{h.c('status')}, {h.c('service')}, and a {h.c('checks')} "
            f"map. Per-check entries carry {h.c('ok')} plus check-specific "
            f"fields ({h.c('anthropic')}/{h.c('openai')} booleans, "
            f"{h.c('status_code')}/{h.c('latency_ms')}, or "
            f"{h.c('error')}).",
        ]),
        h.p("What the agent service actually depends on", h.H2),
        *h.bullets([
            f"<b>LLM provider</b> &mdash; at least one of {anthro_env} or "
            f"{openai_env} must be set. The Strands agent inside "
            "eugene-agent-ws is provider-agnostic; readiness only insists "
            "that <i>some</i> credential is available.",
            f"<b>eugene-mcp</b> &mdash; the agent calls MCP tools over "
            f"HTTP at {mcp_env}. Without it the chat tier cannot answer "
            "any biomedical query.",
            f"<b>JWT signing secret</b> &mdash; {secret_env} signs the "
            "short-lived tokens minted by the auth router; without it "
            "the WebSocket handshake cannot authenticate the UI.",
            "<b>(implicit) the Next.js UI</b> &mdash; not probed; the UI "
            "is the consumer, not a dependency.",
        ]),
        h.p("Status values", h.H2),
        h.code(
            "GET /health        -> { status: \"OK\",       service: \"eugene-agent-ws\" }\n"
            "GET /health/ready  -> { status: \"OK\"|\"DEGRADED\",\n"
            "                        service: \"eugene-agent-ws\",\n"
            "                        checks: { llm_provider: {...},\n"
            "                                  mcp:          {...},\n"
            "                                  jwt_secret:   {...} } }"
        ),
        h.p(
            f"{h.c('DEGRADED')} is paired with HTTP "
            f"{h.c('503 Service Unavailable')}; {h.c('OK')} with "
            f"{h.c('200')}. Orchestrators that only look at the status "
            "code do the right thing; humans get the JSON for triage."
        ),
        h.PageBreak(),
    ]

    # --------------------- 1. HTTP entry --------------------------------- #
    router_decl = h.c('APIRouter(prefix=&quot;&quot;, tags=[&quot;health&quot;])')
    story += [
        h.p("1. HTTP entry", h.H1),
        h.p("<font face='Courier'>agents/eugene-agent-ws/src/router/health_router.py</font>", h.PATH),
        *h.bullets([
            f"Router declared at line 16 with no prefix and tag "
            f"{h.c('health')}: {router_decl}. Routes mount at the service "
            f"root; the app-level {root_path_lit} then prepends "
            f"{h.c('/agent/api')} externally.",
            f"Two coroutines: {h.c('liveness()')} at line 23 and "
            f"{h.c('readiness(response)')} at line 28.",
            f"Module-level imports include {h.c('httpx')}, {h.c('os')}, "
            f"and {h.c('time')}. No driver/client is constructed at "
            "import time &mdash; the httpx client is created per-request "
            "inside readiness (see section 2) so import-time is safe "
            "even when env vars are not set.",
        ]),
        h.p("Verbatim liveness (health_router.py:22-24)", h.H2),
        h.code(
            "@router.get(\"/health\")\n"
            "async def liveness() -> dict[str, Any]:\n"
            "    return {\"status\": \"OK\", \"service\": \"eugene-agent-ws\"}"
        ),
        h.p(
            "Three lines, no IO. The route returns a fresh dict on every "
            "call; FastAPI serializes it with the default JSON encoder."
        ),
        h.p("Verbatim readiness signature (health_router.py:27-28)", h.H2),
        h.code(
            "@router.get(\"/health/ready\")\n"
            "async def readiness(response: Response) -> dict[str, Any]:"
        ),
        h.p(
            f"The handler takes a FastAPI {h.c('Response')} so it can "
            f"mutate {h.c('response.status_code')} in place &mdash; this "
            f"is how it flips to {h.c('503')} without raising an "
            "exception (which would lose the structured body)."
        ),
        h.p("Registration (eugene_chat_ws.py:30-37, 53-57)", h.H2),
        h.code(
            "def add_routers(app: FastAPI) -> None:\n"
            "    from router.auth import auth_router\n"
            "    from router import root_router, health_router\n"
            "    from query.router import chat_query_agent_router\n"
            "\n"
            "    routers = [auth_router, root_router, health_router,\n"
            "               chat_query_agent_router]\n"
            "    for router in routers:\n"
            "        app.include_router(router.router)\n"
            "\n"
            "app = FastAPI(\n"
            "    root_path=\"/agent/api\",\n"
            "    title=\"Eugene Agent WS\",\n"
            "    version=\"2.0.0\",\n"
            ")"
        ),
        *h.bullets([
            f"{h.c('health_router')} is included third &mdash; after "
            "auth and root &mdash; but because it carries no prefix the "
            "order does not affect routing.",
            f"The app-level {root_path_lit} means an external probe must "
            f"hit {h.c('http://host:port/agent/api/health/ready')} (the "
            "ingress strips this prefix before handing the request to "
            "uvicorn). Container-local healthchecks that bypass the "
            f"ingress use the raw {h.c('/health')} path.",
            "The router carries no auth dependency &mdash; probes must "
            "succeed before any JWT verification is exercised.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 2. Handler internals -------------------------- #
    mcp_url_var = h.c('mcp_url')
    probe_var = h.c('probe_url')
    verify_var = h.c('verify_ssl')
    story += [
        h.p("2. Handler internals &mdash; what gets checked", h.H1),
        h.p(
            f"{h.c('readiness()')} runs three independent checks "
            "sequentially. Verbatim from health_router.py:27-78:"
        ),
        h.code(
            "@router.get(\"/health/ready\")\n"
            "async def readiness(response: Response) -> dict[str, Any]:\n"
            "    checks: dict[str, dict[str, Any]] = {}\n"
            "    overall_ok = True\n"
            "\n"
            "    # 1. LLM provider: at least one API key must be present\n"
            "    has_anthropic = bool(os.environ.get(\"ANTHROPIC_API_KEY\"))\n"
            "    has_openai    = bool(os.environ.get(\"OPENAI_API_KEY\"))\n"
            "    checks[\"llm_provider\"] = {\n"
            "        \"ok\":        has_anthropic or has_openai,\n"
            "        \"anthropic\": has_anthropic,\n"
            "        \"openai\":    has_openai,\n"
            "    }\n"
            "    overall_ok &= checks[\"llm_provider\"][\"ok\"]\n"
            "\n"
            "    # 2. MCP server reachability\n"
            "    mcp_url = os.environ.get(\"EUGENE_MCP_SERVER_URL\", \"\")\n"
            "    if mcp_url:\n"
            "        start = time.perf_counter()\n"
            "        try:\n"
            "            probe_url = mcp_url.rstrip(\"/\")\n"
            "            if probe_url.endswith(\"/mcp\"):\n"
            "                probe_url = probe_url[:-4]\n"
            "            verify_ssl = os.environ.get(\n"
            "                \"EUGENE_MCP_VERIFY_SSL\", \"true\"\n"
            "            ).lower() != \"false\"\n"
            "            async with httpx.AsyncClient(\n"
            "                verify=verify_ssl, timeout=3.0\n"
            "            ) as client:\n"
            "                resp = await client.get(f\"{probe_url}/health\")\n"
            "            checks[\"mcp\"] = {\n"
            "                \"ok\": resp.status_code < 500,\n"
            "                \"status_code\": resp.status_code,\n"
            "                \"latency_ms\": int((time.perf_counter() - start) * 1000),\n"
            "            }\n"
            "        except Exception as exc:\n"
            "            checks[\"mcp\"] = {\"ok\": False,\n"
            "                              \"error\": f\"{type(exc).__name__}: {exc}\"}\n"
            "        overall_ok &= checks[\"mcp\"][\"ok\"]\n"
            "    else:\n"
            "        checks[\"mcp\"] = {\"ok\": False,\n"
            "                          \"error\": \"EUGENE_MCP_SERVER_URL not set\"}\n"
            "        overall_ok = False\n"
            "\n"
            "    # 3. JWT signing secret configured\n"
            "    secret_configured = bool(os.environ.get(\"EUGENE_CLIENT_SECRET\"))\n"
            "    checks[\"jwt_secret\"] = {\"ok\": secret_configured}\n"
            "    overall_ok &= secret_configured\n"
            "\n"
            "    if not overall_ok:\n"
            "        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE\n"
            "\n"
            "    return {\n"
            "        \"status\": \"OK\" if overall_ok else \"DEGRADED\",\n"
            "        \"service\": \"eugene-agent-ws\",\n"
            "        \"checks\": checks,\n"
            "    }"
        ),
        h.p("Per-check semantics", h.H2),
        *h.bullets([
            f"<b>{h.c('checks.llm_provider')}.</b> Two boolean env reads. "
            f"{h.c('ok')} is the OR of {h.c('anthropic')} and "
            f"{h.c('openai')}, so a single configured provider is "
            "sufficient. The individual booleans are surfaced so a "
            "human can see <i>which</i> provider is wired.",
            f"<b>{h.c('checks.mcp')}.</b> The MCP URL is normalised: "
            f"trailing {h.c('/')} is stripped, then a trailing "
            f"{h.c('/mcp')} suffix is removed so that "
            f"{h.c('https://host/mcp')} (the JSON-RPC endpoint the agent "
            f"actually calls) becomes {h.c('https://host')} (the FastAPI "
            f"root that hosts {h.c('/health')}). A 3-second timeout caps "
            "the probe latency; any exception is caught and surfaced as "
            f"{h.c('error: &quot;ExceptionClass: message&quot;')}. "
            f"{verify_var} honours an opt-out env "
            f"({h.c('EUGENE_MCP_VERIFY_SSL=false')}) for local self-signed "
            "deployments.",
            f"<b>{h.c('checks.mcp.ok')}.</b> Defined as "
            f"{h.c('resp.status_code &lt; 500')} &mdash; meaning a 404 "
            "from the MCP server is treated as &quot;healthy enough&quot;. "
            "Rationale: the goal is to prove the server is up and "
            "responding, not to assert that this exact path exists; some "
            "MCP deployments do not expose a sibling /health route.",
            f"<b>{h.c('checks.jwt_secret')}.</b> Single env existence "
            f"check on {secret_env}. No format validation &mdash; an "
            "empty-but-set secret would pass here but later fail "
            "signature verification at the auth router.",
        ]),
        h.p(
            f"Note: every {h.c('overall_ok &amp;= ...')} uses a bitwise "
            "AND on booleans, equivalent to logical AND but always "
            "evaluating both sides &mdash; intentional, so that adding a "
            "fourth check cannot accidentally short-circuit and skip its "
            "diagnostic."
        ),
        h.PageBreak(),
    ]

    # --------------------- 3. Response model ----------------------------- #
    story += [
        h.p("3. Response model", h.H1),
        h.p(
            "There is no Pydantic model. Both handlers are typed "
            f"{h.c('-&gt; dict[str, Any]')} and FastAPI serializes the "
            "dict directly. Four concrete shapes occur in practice:"
        ),
        h.p("Liveness, healthy (always)", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{ \"status\": \"OK\", \"service\": \"eugene-agent-ws\" }"
        ),
        h.p("Readiness, healthy", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"OK\",\n"
            "  \"service\": \"eugene-agent-ws\",\n"
            "  \"checks\": {\n"
            "    \"llm_provider\": { \"ok\": true,  \"anthropic\": true, \"openai\": false },\n"
            "    \"mcp\":          { \"ok\": true,  \"status_code\": 200, \"latency_ms\": 12 },\n"
            "    \"jwt_secret\":   { \"ok\": true }\n"
            "  }\n"
            "}"
        ),
        h.p("Readiness, degraded (MCP unreachable)", h.H2),
        h.code(
            "HTTP/1.1 503 Service Unavailable\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"DEGRADED\",\n"
            "  \"service\": \"eugene-agent-ws\",\n"
            "  \"checks\": {\n"
            "    \"llm_provider\": { \"ok\": true, \"anthropic\": true, \"openai\": false },\n"
            "    \"mcp\": {\n"
            "      \"ok\": false,\n"
            "      \"error\": \"ConnectError: All connection attempts failed\"\n"
            "    },\n"
            "    \"jwt_secret\": { \"ok\": true }\n"
            "  }\n"
            "}"
        ),
        h.p("Readiness, misconfigured (no LLM key, no MCP URL)", h.H2),
        h.code(
            "HTTP/1.1 503 Service Unavailable\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"DEGRADED\",\n"
            "  \"service\": \"eugene-agent-ws\",\n"
            "  \"checks\": {\n"
            "    \"llm_provider\": { \"ok\": false, \"anthropic\": false, \"openai\": false },\n"
            "    \"mcp\":          { \"ok\": false, \"error\": \"EUGENE_MCP_SERVER_URL not set\" },\n"
            "    \"jwt_secret\":   { \"ok\": false }\n"
            "  }\n"
            "}"
        ),
        *h.bullets([
            f"{h.c('status')}: literal {h.c('OK')} or {h.c('DEGRADED')} "
            "&mdash; the only two values.",
            f"{h.c('service')}: constant {h.c('&quot;eugene-agent-ws&quot;')} "
            "&mdash; distinguishes this probe from eugene-ws and "
            "eugene-mcp when scraping mixed logs.",
            f"{h.c('checks.&lt;name&gt;.error')} is a free-form "
            f"{h.c('&quot;ExceptionClass: message&quot;')} string &mdash; "
            "useful for humans, not for machines. Programmatic gating "
            "should key off the HTTP status code, not the error text.",
            f"All three check entries are always present on the "
            f"{ready_endpoint} response, even when one short-circuits "
            "&mdash; consumers can index without defensive guards.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 4. Use in production -------------------------- #
    story += [
        h.p("4. Use in production &mdash; k8s readiness gating for the chat UI", h.H1),
        h.p(
            "The agent tier sits between the Next.js chat UI and the MCP "
            "server. Readiness gating here directly controls whether the "
            "chat UI can complete its WebSocket handshake."
        ),
        h.p("Kubernetes (recommended pattern)", h.H2),
        h.code(
            "livenessProbe:\n"
            "  httpGet: { path: /agent/api/health,       port: 8000 }\n"
            "  initialDelaySeconds: 15\n"
            "  periodSeconds: 10\n"
            "  failureThreshold: 3      # -&gt; restart pod\n"
            "readinessProbe:\n"
            "  httpGet: { path: /agent/api/health/ready, port: 8000 }\n"
            "  initialDelaySeconds: 5\n"
            "  periodSeconds: 5\n"
            "  failureThreshold: 2      # -&gt; remove from Service endpoints"
        ),
        *h.bullets([
            f"<b>Readiness gates chat UI traffic.</b> A 503 from "
            f"{ready_endpoint} drops the agent-ws pod from its Service "
            "endpoints; the ingress in front of the Next.js UI then "
            "returns 503 for the WebSocket upgrade, and the UI surfaces "
            "a &quot;chat unavailable&quot; banner. No user is allowed "
            "to start a conversation that the agent cannot service.",
            f"<b>Liveness only restarts on wedged process.</b> "
            f"{live_endpoint} fails only if the uvicorn event loop has "
            "stopped responding &mdash; an unambiguous signal that a "
            "restart is the right remediation. MCP outages and missing "
            "LLM keys do <i>not</i> trigger restarts.",
            f"<b>Probes are exempt from auth.</b> The router carries no "
            f"auth dependency &mdash; do not put it behind the global "
            f"JWT verification or the kubelet will see 401 and consider "
            f"the pod unhealthy. {root_path_lit} does not affect this; "
            "auth middleware is the actual gate.",
            f"<b>Probe path must include the root_path.</b> Because the "
            f"app declares {root_path_lit}, the in-cluster probe path is "
            f"{h.c('/agent/api/health/ready')}, not "
            f"{h.c('/health/ready')}. Setting this wrong is the most "
            "common k8s wiring mistake on this service.",
            f"<b>Boot ordering.</b> The agent does not block on MCP at "
            f"startup; {ready_endpoint} is the only place that "
            "synchronously checks MCP. This means agent-ws can start "
            "before MCP is ready and will simply stay out of rotation "
            "until the dependency comes up &mdash; no explicit "
            f"{h.c('depends_on')} ordering required.",
        ]),
        h.p("docker-compose (local stack)", h.H2),
        h.p(
            f"The compose file points its container healthcheck at "
            f"{live_endpoint} (cheap, never false-negative) and lets "
            "downstream gating in the Next.js UI rely on the actual "
            f"WebSocket connect to discover whether MCP is up. The "
            f"{ready_endpoint} endpoint is still useful for ad-hoc "
            f"{h.c('curl')} diagnosis during local development."
        ),
        h.PageBreak(),
    ]

    # --------------------- 5. Debugging walk ----------------------------- #
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"<b>Confirm liveness.</b> "
            f"{h.c('curl -i http://localhost:18001/health')} (container-local) "
            f"or {h.c('curl -i http://localhost:18001/agent/api/health')} "
            f"(through ingress). Expect a 200 with "
            f"{h.c('service: &quot;eugene-agent-ws&quot;')} within ~15s of "
            "container start.",
            f"<b>Verify all three dependency checks pass.</b> "
            f"{h.c('curl -sS .../health/ready | jq .checks')}. Expect "
            f"{h.c('llm_provider.ok')}, {h.c('mcp.ok')}, and "
            f"{h.c('jwt_secret.ok')} all true, plus a "
            f"{h.c('mcp.latency_ms')} field &mdash; that confirms the "
            f"httpx round-trip to {h.c('EUGENE_MCP_SERVER_URL')} actually "
            "happened.",
            f"<b>Simulate MCP outage.</b> "
            f"{h.c('docker-compose stop eugene_mcp')}, then re-hit "
            f"{ready_endpoint}. Expect HTTP 503 with "
            f"{h.c('checks.mcp.error')} like "
            f"{h.c('&quot;ConnectError: ...&quot;')}. Liveness should "
            "still be 200 &mdash; confirms the split.",
            f"<b>Simulate missing LLM key.</b> Unset both {anthro_env} "
            f"and {openai_env} in {h.c('docker.env')} and restart "
            f"agent-ws. {ready_endpoint} returns 503 with "
            f"{h.c('llm_provider.ok: false')} and both provider booleans "
            "false &mdash; no MCP call is skipped (the checks run "
            "independently).",
            f"<b>Trace the MCP probe path.</b> Breakpoint at "
            f"{h.c('agents/eugene-agent-ws/src/router/health_router.py:53')} "
            f"({h.c('await client.get(f&quot;{{probe_url}}/health&quot;)')}). "
            f"Confirm that {probe_var} equals the MCP host root, not the "
            f"{h.c('/mcp')} JSON-RPC endpoint &mdash; the strip-suffix "
            "logic at lines 48-50 is what makes this work for either "
            f"form of {mcp_env}.",
        ]),
        h.Spacer(1, 10),

        # ----------------- 6. Reference index ---------------------------- #
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP entry\n"
            "  agents/eugene-agent-ws/src/router/health_router.py       # GET /health (L22), GET /health/ready (L27)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py             # add_routers() L30, app root_path L53\n\n"
            "Dependencies probed\n"
            "  env: ANTHROPIC_API_KEY / OPENAI_API_KEY                  # llm_provider check (L33-40)\n"
            "  env: EUGENE_MCP_SERVER_URL                               # mcp check target (L43)\n"
            "  env: EUGENE_MCP_VERIFY_SSL (default true)                # httpx verify=  (L51)\n"
            "  env: EUGENE_CLIENT_SECRET                                # jwt_secret check (L67)\n"
            "  httpx.AsyncClient(timeout=3.0).get(probe_url + /health)  # MCP reachability (L52-53)\n\n"
            "Probe consumers\n"
            "  k8s livenessProbe  -> /agent/api/health\n"
            "  k8s readinessProbe -> /agent/api/health/ready  (gates chat UI traffic)\n"
            "  docker-compose healthcheck -> /health (liveness only)\n\n"
            "Sibling routes (for contrast)\n"
            "  src/router/health_router.py                              # eugene-ws variant: probes Neo4j only\n"
            "  agents/eugene-agent-ws/src/router/root_router.py         # GET / -- service banner\n"
            "  agents/eugene-agent-ws/src/router/auth/                  # consumes EUGENE_CLIENT_SECRET\n"
        ),
    ]

    return story
