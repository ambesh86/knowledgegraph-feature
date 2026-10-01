"""Per-route flow guide for Eugene agent-ws root_router.

Endpoint: GET / (mounted under FastAPI root_path="/agent/api")

The bare service root for the agent-ws (agentic chat) sidecar. A trivial,
unauthenticated hello-world used as a liveness / smoke endpoint. Walks an
engineer from the FastAPI boundary through the handler into the JSON shape
returned to the caller. Every reference is in path/to/file.py:line form so
it can be opened directly in an IDE.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_AGENT_ROOT_FLOW_GUIDE.pdf"
TITLE = "Eugene Agent Root Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    welcome_msg = h.c(
        "&quot;Welcome to the EUGENE agentic chat webservice. "
        "Visit the Swagger docs at /docs&quot;"
    )
    root_path_literal = h.c("root_path=&quot;/agent/api&quot;")
    message_key = h.c("message")
    swagger_path = h.c("/docs")
    include_line = h.c("app.include_router(router.router)")

    # ---------- cover -------------------------------------------------------
    story += [
        h.p("Eugene Agent Root Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP boundary &rarr; FastAPI router &rarr; "
            "static welcome payload (no auth, no I/O)",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers onboarding to the Eugene <b>agent-ws</b> sidecar "
            f"(the agentic chat webservice) who need a single, file-referenced "
            f"trace of {h.c('GET /')} as it lives on that service. This is "
            f"<b>not</b> the same root as the main {h.c('eugene_ws')} service "
            f"&mdash; that one is documented in "
            f"{h.c('EUGENE_ROOT_FLOW_GUIDE.pdf')}. The agent-ws variant is "
            f"thinner still: no JWT dependency, no user claims, just a single "
            f"static message. The only subtle bit is the FastAPI "
            f"{root_path_literal} prefix on the app, which means the route "
            f"appears externally at {h.c('/agent/api/')} even though the "
            f"router itself declares {h.c('prefix=&quot;&quot;')}. Every "
            f"reference uses the form {h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoint", h.H2),
        h.p(
            f"{h.c('GET /')} on the agent-ws app &mdash; externally reachable "
            f"as {h.c('GET /agent/api/')} when fronted by the standard "
            f"ingress. No path params, no query params, no body, no auth "
            f"requirement. Response is a JSON object with a single key, "
            f"{message_key}.",
        ),
        h.p("Sample call"),
        h.code(
            "# direct against the agent-ws container (no ingress):\n"
            "curl -s 'http://localhost:18510/' | jq .\n"
            "\n"
            "# through the ingress / reverse proxy (root_path applied):\n"
            "curl -s 'http://localhost:8080/agent/api/' | jq .\n"
        ),
        h.p(
            f"Declared in "
            f"{h.c('agents/eugene-agent-ws/src/router/root_router.py:14-18')}. "
            f"Router prefix {h.c('&quot;&quot;')} (empty), tag {h.c('root')}.",
        ),
        h.PageBreak(),
    ]

    # ---------- 0. purpose --------------------------------------------------
    story += [
        h.p("0. Purpose (read this first)", h.H1),
        h.p(
            "This route exists for three concrete reasons, all operational "
            "rather than functional:",
        ),
        *h.bullets([
            "<b>Liveness signal for the agent sidecar.</b> Container probes "
            "and curl-from-laptop sanity checks need a cheap endpoint that "
            f"returns 200 when the agent-ws process is up. Unlike the main "
            f"service&#39;s root, this one is unauthenticated &mdash; it "
            "is suitable as a Kubernetes / Docker liveness probe target "
            "directly.",
            "<b>Swagger pointer.</b> The literal welcome string explicitly "
            f"directs the caller to {swagger_path} for OpenAPI exploration. "
            f"An operator hitting the bare {h.c('/')} with a browser gets "
            "actionable guidance instead of a 404.",
            "<b>Routing smoke test.</b> Because the agent-ws app is mounted "
            f"behind {root_path_literal}, a successful 200 at "
            f"{h.c('/agent/api/')} proves end-to-end that (a) the ingress / "
            "reverse proxy is forwarding correctly, (b) FastAPI is rewriting "
            "incoming paths with the root_path stripped, and (c) the "
            "router was registered before the app started serving.",
        ]),
        h.p("What it deliberately is not", h.H2),
        *h.bullets([
            f"<b>Not a health check with deep checks.</b> Real health probes "
            f"go to {h.c('/health')} on the agent-ws health router "
            f"({h.c('agents/eugene-agent-ws/src/router/health_router.py')}).",
            f"<b>Not authenticated.</b> Unlike the main service&#39;s root "
            f"({h.c('src/router/root_router.py')}), this handler takes no "
            f"{h.c('Depends(get_current_user)')} and returns no user "
            f"claims. Do not treat a 200 here as evidence that JWT auth is "
            "wired correctly.",
            f"<b>Not an OpenAPI landing page.</b> FastAPI&#39;s generated "
            f"docs live at {swagger_path} (i.e. externally at "
            f"{h.c('/agent/api/docs')}); the root route does not redirect "
            "there, it only mentions the path in the welcome string.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 1. HTTP entry -----------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("App construction", h.H2),
        h.p(
            f"{h.c('agents/eugene-agent-ws/src/eugene_chat_ws.py:53-57')} "
            "constructs the FastAPI app:",
        ),
        h.code(
            "app = FastAPI(\n"
            "    root_path=\"/agent/api\",\n"
            "    title=\"Eugene Agent WS\",\n"
            "    version=\"2.0.0\",\n"
            ")\n"
        ),
        h.p(
            f"The {root_path_literal} argument is load-bearing for this "
            f"guide. FastAPI uses it to (a) generate correct URLs in the "
            f"OpenAPI document so Swagger UI works when fronted by a reverse "
            f"proxy that strips {h.c('/agent/api')}, and (b) advertise the "
            f"effective external mount point. Internally, the route is still "
            f"declared at {h.c('/')} on the {h.c('APIRouter')}; the prefix "
            "is applied by the ingress, not by the app itself.",
        ),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('agents/eugene-agent-ws/src/eugene_chat_ws.py:32')} &mdash; "
            f"{h.c('from router import root_router, health_router')}. "
            f"{h.c('agents/eugene-agent-ws/src/eugene_chat_ws.py:35')} packs "
            f"the routers into a list "
            f"{h.c('[auth_router, root_router, health_router, chat_query_agent_router]')}, "
            f"and line 37 calls {include_line} for each. {h.c('root_router')} "
            "is registered second &mdash; immediately after the auth router "
            "&mdash; which means the bare slash is bound very early in app "
            "startup.",
        ),
        h.p("Router file (verbatim)", h.H2),
        h.p(h.c("agents/eugene-agent-ws/src/router/root_router.py"), h.PATH),
        h.code(
            "import logging\n"
            "\n"
            "from fastapi import APIRouter\n"
            "\n"
            "\n"
            "router = APIRouter(\n"
            "    prefix=\"\",\n"
            "    tags=[\"root\"],\n"
            ")\n"
            "\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            "\n"
            "@router.get(\"/\")\n"
            "async def app_root():\n"
            "    return {\n"
            "        \"message\": \"Welcome to the EUGENE agentic chat "
            "webservice. Visit the Swagger docs at /docs\"\n"
            "    }\n"
        ),
        h.p("Things to notice", h.H2),
        *h.bullets([
            f"<b>Empty prefix.</b> {h.c('prefix=&quot;&quot;')} means the "
            f"route binds at the literal {h.c('/')} of the app. Combined "
            f"with {root_path_literal} on the app constructor, this becomes "
            f"{h.c('/agent/api/')} externally.",
            f"<b>No {h.c('Depends')}.</b> The handler signature is "
            f"{h.c('async def app_root()')} &mdash; no parameters, no "
            f"dependencies, no auth. Anyone who can reach the port gets "
            f"a 200.",
            f"<b>Tag.</b> {h.c('tags=[&quot;root&quot;]')} groups the "
            f"operation under a {h.c('root')} section in the auto-generated "
            f"Swagger UI at {swagger_path}.",
            f"<b>No {h.c('response_model')}.</b> The dict is serialized "
            f"as-is by FastAPI&#39;s default {h.c('jsonable_encoder')}.",
            f"<b>{h.c('async def')} but no I/O.</b> The handler awaits "
            f"nothing. It exists as a coroutine purely for stylistic "
            "consistency with the rest of the agent-ws routes.",
            f"<b>Module logger declared but unused.</b> "
            f"{h.c('logger = logging.getLogger(__name__)')} is present at "
            f"module load but never called inside the handler; successful "
            "calls log nothing handler-side.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 2. handler internals ----------------------------------------
    story += [
        h.p("2. Handler internals", h.H1),
        h.p(
            f"The handler body is a single {h.c('return')} of a one-key "
            f"dict literal. There is no dependency resolution, no database "
            f"call, no adapter, no mapper, and no logging. By volume this is "
            "the simplest handler in the entire Eugene codebase.",
        ),
        h.p("Resolution order", h.H2),
        *h.bullets([
            f"FastAPI receives an HTTP request whose path (after ingress "
            f"strips {h.c('/agent/api')}) is {h.c('/')}.",
            f"It matches against the registered {h.c('GET /')} operation on "
            f"{h.c('root_router')} and invokes {h.c('app_root()')}.",
            f"No parameters, no dependencies &mdash; the coroutine returns "
            "immediately with the welcome dict.",
            f"FastAPI serializes the dict via {h.c('jsonable_encoder')} and "
            f"writes a 200 response with "
            f"{h.c('content-type: application/json')}.",
        ]),
        h.p("Middleware that still runs", h.H2),
        h.p(
            f"Even though the handler itself does nothing, the request still "
            f"traverses the middleware stack configured in "
            f"{h.c('agents/eugene-agent-ws/src/eugene_chat_ws.py')}:",
        ),
        *h.bullets([
            f"<b>SEC-03 rate limiting</b> (lines 60-63): "
            f"{h.c('SlowAPIMiddleware')} with the limiter from "
            f"{h.c('make_limiter()')}. Excessive calls to "
            f"{h.c('GET /')} will eventually be throttled.",
            f"<b>CORS</b> (lines 66-73): "
            f"{h.c('CORSMiddleware')} with origins controlled by the "
            f"{h.c('EUGENE_CORS_ORIGINS')} environment variable (default: "
            f"{h.c('http://localhost:18502,http://localhost:3000')}).",
            f"<b>OBS-01 request-id</b> (line 76): "
            f"{h.c('request_id_middleware')} attaches a request id used in "
            f"logs and surfaced back to the caller via the "
            f"{h.c('X-Request-ID')} response header.",
            f"<b>Rate-limit exception handler</b> (line 62): "
            f"{h.c('RateLimitExceeded')} is translated by "
            f"{h.c('_rate_limit_exceeded_handler')} into a 429 response.",
        ]),
        h.p("Set your first breakpoint", h.H2),
        h.p(
            f"At {h.c('agents/eugene-agent-ws/src/router/root_router.py:16')} "
            f"(the {h.c('return')} statement). There is essentially nothing "
            f"to inspect; the value is hard-coded. A breakpoint here is "
            "useful only to confirm the handler is being reached at all "
            "(useful if you are diagnosing a 404 caused by misconfigured "
            f"{root_path_literal} or a stale ingress).",
        ),
        h.PageBreak(),
    ]

    # ---------- 3. response model -------------------------------------------
    story += [
        h.p("3. Response model", h.H1),
        h.p(
            f"The handler returns a Python {h.c('dict')} literal with a "
            f"single string-valued key. FastAPI serializes it via the "
            f"default {h.c('jsonable_encoder')}; the route declares no "
            f"{h.c('response_model')}, so the wire format is exactly the "
            "dict structure.",
        ),
        h.p("Response shape (verbatim from the handler)", h.H2),
        h.code(
            "{\n"
            "  \"message\": \"Welcome to the EUGENE agentic chat webservice. "
            "Visit the Swagger docs at /docs\"\n"
            "}\n"
        ),
        h.p("Notes on the message string", h.H2),
        *h.bullets([
            f"The message references {swagger_path}. When the service is "
            f"behind the standard ingress, the externally reachable Swagger "
            f"UI is at {h.c('/agent/api/docs')} &mdash; the message gives "
            f"the <i>internal</i> path, which is what curl-from-inside-the-"
            "container will see, but external callers need to remember the "
            f"{h.c('/agent/api')} prefix.",
            f"The string is hard-coded; it does not include the service "
            f"version. Build / release metadata is not exposed by this "
            "endpoint.",
            f"There are no template substitutions; the response is byte-"
            "identical from one call to the next.",
        ]),
        h.p("Status codes", h.H2),
        *h.bullets([
            f"{h.c('200 OK')} &mdash; normal path. Always returned unless a "
            "middleware short-circuits the request.",
            f"{h.c('429 Too Many Requests')} &mdash; from "
            f"{h.c('SlowAPIMiddleware')} when the rate limit configured in "
            f"{h.c('make_limiter()')} is exceeded.",
            f"{h.c('500 Internal Server Error')} &mdash; only if an "
            f"unhandled exception escapes the middleware stack. The handler "
            "itself cannot raise.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 4. use in production ----------------------------------------
    story += [
        h.p("4. Use in production &mdash; frontend probe and liveness echo", h.H1),
        h.p(
            "Because the route does no I/O at all, it is the cheapest "
            "endpoint on the agent-ws sidecar and is the natural target for "
            "any check that just needs &quot;is the process answering "
            "HTTP?&quot;",
        ),
        h.p("Recommended uses", h.H2),
        *h.bullets([
            f"<b>Frontend probe.</b> The Next.js UI in "
            f"{h.c('agents/eugene-agent-ui-next/')} can hit "
            f"{h.c('GET /agent/api/')} on startup to confirm the agent "
            "backend is reachable before enabling chat features. A 200 "
            "with the expected welcome string is positive confirmation "
            "that DNS, CORS, and ingress are all wired correctly.",
            f"<b>Kubernetes / Docker liveness probe.</b> Unlike the main "
            f"service&#39;s root, this one is unauthenticated, so a probe "
            f"definition pointing at {h.c('/agent/api/')} works without "
            "embedding service-principal credentials. (Prefer "
            f"{h.c('/agent/api/health')} when available, since it is "
            "purpose-built for that role.)",
            f"<b>Ingress smoke test.</b> When deploying a new reverse "
            f"proxy / ingress rule that maps {h.c('/agent/api/*')} to the "
            f"agent-ws container, a single {h.c('curl /agent/api/')} "
            f"confirms that (a) the rule matches, (b) {root_path_literal} "
            f"is being respected, and (c) {message_key} comes back with "
            "the agent-ws welcome (not the main service&#39;s).",
            f"<b>Operator banner.</b> An engineer poking at a new "
            f"environment can hit the bare URL in a browser and instantly "
            f"learn (i) the service is the agent-ws variant and (ii) "
            f"{swagger_path} is the path to Swagger UI.",
        ]),
        h.p("Anti-patterns", h.H2),
        *h.bullets([
            f"<b>Don&#39;t use it for auth validation.</b> The handler has "
            f"no {h.c('Depends(get_current_user)')}; a 200 here proves "
            f"nothing about JWT validity. For that, call the main "
            f"service&#39;s {h.c('GET /')} instead.",
            f"<b>Don&#39;t parse the welcome string in clients.</b> The "
            f"text is descriptive, not contractual; treat {message_key} as "
            "opaque except for unit tests that explicitly check it.",
            f"<b>Don&#39;t use it as a deep readiness check.</b> The "
            f"agent-ws integrates with several upstream services (Neo4j, "
            f"LLM provider, etc.) &mdash; a 200 here says nothing about "
            f"those. Use the health router for real readiness.",
        ]),
        h.p("Observability tips", h.H2),
        *h.bullets([
            f"The OBS-01 request-id middleware tags every call with an "
            f"{h.c('X-Request-ID')} response header. Capture it client-side "
            "if you need to correlate a failing probe with server logs.",
            f"Access logging is configured via "
            f"{h.c('configure_json_logging(&quot;eugene-agent-ws&quot;)')} "
            f"at line 49 of {h.c('eugene_chat_ws.py')}. Filter logs by "
            f"{h.c('path=/')} to isolate root-route hits.",
            f"If you need throttle telemetry, watch for "
            f"{h.c('RateLimitExceeded')} on this route &mdash; an unusual "
            "rate here often indicates a misconfigured probe interval.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 5. debugging walk -------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"<b>Bring the agent-ws sidecar up.</b> "
            f"{h.c('docker-compose up eugene_agent_ws')} (or run "
            f"{h.c('uvicorn eugene_chat_ws:app')} from "
            f"{h.c('agents/eugene-agent-ws/src/')}). Confirm the boot "
            f"sequence in the logs &mdash; line 49 prints the JSON logging "
            f"banner, line 78 calls {h.c('add_routers(app)')}.",
            f"<b>Smoke the route directly.</b> "
            f"{h.c('curl -s -i http://localhost:18510/')}. Expect a 200 "
            f"with body {welcome_msg}. If you get a 404, "
            f"check that {h.c('root_router')} is still in the list at "
            f"{h.c('eugene_chat_ws.py:35')}.",
            f"<b>Smoke it through the ingress.</b> "
            f"{h.c('curl -s http://localhost:8080/agent/api/ | jq .')}. "
            f"If this 404s while the direct call succeeds, the problem is "
            f"the reverse proxy strip rule, not the app; verify that "
            f"{root_path_literal} matches what the ingress is stripping.",
            f"<b>Set a breakpoint.</b> Put one at "
            f"{h.c('agents/eugene-agent-ws/src/router/root_router.py:16')}. "
            f"Hit the route; if the breakpoint never fires while the "
            "client still gets a non-200, the request is being intercepted "
            "in middleware (rate limiter, CORS preflight, request-id) "
            "before it reaches the handler.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 6. reference index ------------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Router\n"
            "  agents/eugene-agent-ws/src/router/root_router.py        "
            "(entire file, 18 lines)\n"
            "\n"
            "App construction + wiring\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:32         "
            "(import root_router)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:35-37      "
            "(routers list + include loop)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:53-57      "
            "(FastAPI(root_path=\"/agent/api\", ...))\n"
            "\n"
            "Middleware stack (request still traverses these)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:60-63      "
            "(SEC-03 rate limiter / SlowAPIMiddleware)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:66-73      "
            "(CORSMiddleware, EUGENE_CORS_ORIGINS)\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py:76         "
            "(OBS-01 request_id_middleware)\n"
            "\n"
            "Related operational routes on the same sidecar\n"
            "  agents/eugene-agent-ws/src/router/health_router.py      "
            "(deep health checks)\n"
            "\n"
            "Sibling route on the MAIN service (distinct!)\n"
            "  src/router/root_router.py                               "
            "(auth-gated, returns user claims)\n"
        ),
        h.p("Key takeaways", h.H2),
        *h.bullets([
            f"{h.c('GET /')} on the agent-ws is a five-line, "
            f"<b>unauthenticated</b> hello-world. No DB, no adapter, no "
            f"mapper, no {h.c('Depends')}, no response model.",
            f"The route appears externally at {h.c('/agent/api/')} because "
            f"of {root_path_literal} on the FastAPI constructor &mdash; not "
            "because the router declares any prefix.",
            f"It is distinct from the main service&#39;s "
            f"{h.c('src/router/root_router.py')}: that one is JWT-gated and "
            f"returns user claims; this one is anonymous and returns a "
            f"single {message_key} string.",
            f"Its job is operational: confirm the agent-ws process is up "
            f"and the {h.c('/agent/api')} ingress prefix is wired. It is "
            "safe to use as a Kubernetes liveness probe target.",
        ]),
    ]

    return story
