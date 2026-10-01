"""ReportLab section: Eugene health route end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 5-7 PDF pages.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_HEALTH_FLOW_GUIDE.pdf"
TITLE = "Eugene Health Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------- title --------------------------------- #
    story += [
        h.p("Eugene Health Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP probe &rarr; FastAPI router &rarr; "
            "Neo4j driver verify_connectivity &rarr; JSON status envelope &rarr; "
            "container orchestrator gating",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers wiring up container healthchecks, k8s probes, or external "
            "monitors against eugene-ws. The health route is the smallest router in "
            "the codebase (two endpoints, fifty-three lines) but it is the contract "
            "that docker-compose and any future orchestrator use to decide whether "
            "the API is alive and whether traffic can be routed to it. Every "
            "reference uses the form "
            f"{h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('GET /health')} &mdash; liveness probe. Always returns 200 as "
            "long as the FastAPI process is accepting requests.",
            f"{h.c('GET /health/ready')} &mdash; readiness probe. Verifies the "
            f"Neo4j driver can reach the configured {h.c('NEO4J_URI')} and "
            "returns 200 only when every dependency check passes; otherwise "
            "503 with a per-check diagnostic envelope.",
        ]),
        h.p("Probe model", h.H2),
        h.p(
            "Eugene splits the two concerns deliberately:"
        ),
        *h.bullets([
            "<b>Liveness</b> answers <i>is the Python process wedged?</i> &mdash; "
            "no external IO, no driver calls, no env lookups. A failure means "
            "restart the container.",
            "<b>Readiness</b> answers <i>can this replica serve traffic right "
            "now?</i> &mdash; it actually round-trips to Neo4j. A failure means "
            "stop routing traffic, but do <i>not</i> restart (a flaky Neo4j or "
            "an unset env var is not fixed by a bounce).",
            "Both endpoints are tagged "
            f"{h.c('health')} and live on the unprefixed router "
            f"({h.c('APIRouter(prefix=&quot;&quot;, tags=[&quot;health&quot;])')}). "
            "No authentication is required &mdash; probes must work before any "
            "Entra ID middleware is exercised.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 0. probe model -------------------------------- #
    story += [
        h.p("0. Probe model (read this first)", h.H1),
        h.p(
            "Unlike the other Eugene guides this route has no Neo4j schema of "
            "its own; the &quot;model&quot; is the contract between the HTTP "
            "probe and the orchestrator. Three rules:"
        ),
        *h.bullets([
            f"<b>Liveness is cheap and side-effect free.</b> {h.c('GET /health')} "
            "returns a constant dict. It must not allocate driver connections, "
            "read env vars, or touch the filesystem &mdash; any of those would "
            "couple liveness to a downstream failure mode and turn restarts "
            "into a self-inflicted outage.",
            f"<b>Readiness exercises the real dependency.</b> {h.c('GET /health/ready')} "
            f"calls {h.c('driver.verify_connectivity()')} which opens a Bolt "
            "session against Neo4j. A passing probe therefore proves not just "
            "&quot;URI is set&quot; but &quot;credentials work and the server "
            "answered&quot;.",
            f"<b>Status envelope is structured.</b> The response always includes "
            f"{h.c('status')}, {h.c('service')}, and a {h.c('checks')} map. "
            f"Per-check entries carry {h.c('ok')}, optional "
            f"{h.c('latency_ms')}, and optional {h.c('error')} so a human "
            "reading {h.c('curl /health/ready')} can see exactly which "
            "dependency is sour.",
        ]),
        h.p("Status values", h.H2),
        h.code(
            "GET /health        -> { status: \"OK\",       service: \"eugene-ws\" }\n"
            "GET /health/ready  -> { status: \"OK\"|\"DEGRADED\",\n"
            "                        service: \"eugene-ws\",\n"
            "                        checks: { neo4j: { ok, latency_ms?, error? } } }"
        ),
        h.p(
            f"The string {h.c('DEGRADED')} is paired with HTTP "
            f"{h.c('503 Service Unavailable')}; {h.c('OK')} is paired with "
            f"{h.c('200')}. Orchestrators that only look at the status code "
            "do the right thing; humans get the JSON for triage.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 1. HTTP entry --------------------------------- #
    story += [
        h.p("1. HTTP entry", h.H1),
        h.p("<font face='Courier'>src/router/health_router.py</font>", h.PATH),
        *h.bullets([
            f"Router declared at line 11 with no prefix and tag "
            f"{h.c('health')}: routes mount at the service root.",
            f"Two coroutines: {h.c('liveness()')} at line 15 and "
            f"{h.c('readiness(response)')} at line 20.",
            "No DI, no module-load side effects. The driver is constructed "
            "lazily inside the readiness handler (see section 2) so importing "
            "the module is safe even without env vars set &mdash; important "
            "because the router is registered unconditionally at boot.",
        ]),
        h.p("Verbatim liveness (health_router.py:14-16)", h.H2),
        h.code(
            "@router.get(\"/health\")\n"
            "async def liveness() -> dict[str, Any]:\n"
            "    return {\"status\": \"OK\", \"service\": \"eugene-ws\"}"
        ),
        h.p(
            "Three lines, no IO. The route returns a fresh dict on every call &mdash; "
            "FastAPI serializes it to JSON with the default encoder."
        ),
        h.p("Verbatim readiness signature (health_router.py:19-20)", h.H2),
        h.code(
            "@router.get(\"/health/ready\")\n"
            "async def readiness(response: Response) -> dict[str, Any]:"
        ),
        h.p(
            f"The handler takes a FastAPI {h.c('Response')} so it can mutate "
            f"{h.c('response.status_code')} in place &mdash; this is how it "
            f"flips to {h.c('503')} without raising an exception (which would "
            "lose the structured body)."
        ),
        h.p("Registration (eugene_ws.py:33, 58)", h.H2),
        h.code(
            "def add_routers(app: FastAPI) -> None:\n"
            "    from router.auth import auth_router\n"
            "    from router import root_router, health_router, release_notes_router\n"
            "    ...\n"
            "    routers = [\n"
            "        auth_router,\n"
            "        root_router,\n"
            "        health_router,\n"
            "        ...\n"
            "    ]\n"
            "    for router in routers:\n"
            "        app.include_router(router.router)"
        ),
        h.p(
            f"{h.c('health_router')} is included third &mdash; after auth and "
            f"root &mdash; but because it carries no prefix, the order does not "
            "affect routing. It is listed early as a signal that the probes "
            "are first-class."
        ),
        h.PageBreak(),
    ]

    # --------------------- 2. Handler internals -------------------------- #
    story += [
        h.p("2. Handler internals &mdash; what gets checked", h.H1),
        h.p(
            f"{h.c('readiness()')} is the only handler that does any work. "
            "It is small enough to read verbatim:"
        ),
        h.code(
            "@router.get(\"/health/ready\")\n"
            "async def readiness(response: Response) -> dict[str, Any]:\n"
            "    checks: dict[str, dict[str, Any]] = {}\n"
            "    overall_ok = True\n"
            "\n"
            "    # Neo4j reachability via existing connection factory\n"
            "    uri = os.environ.get(\"NEO4J_URI\", \"\")\n"
            "    if uri:\n"
            "        start = time.perf_counter()\n"
            "        try:\n"
            "            from graph.infra.db.graph_db_connection_factory import (\n"
            "                GraphDbConnectionFactory,\n"
            "            )\n"
            "\n"
            "            driver = GraphDbConnectionFactory.remote_neo4j_instance_from_env()\n"
            "            driver.verify_connectivity()\n"
            "            checks[\"neo4j\"] = {\n"
            "                \"ok\": True,\n"
            "                \"latency_ms\": int((time.perf_counter() - start) * 1000),\n"
            "            }\n"
            "        except Exception as exc:\n"
            "            checks[\"neo4j\"] = {\"ok\": False, \"error\": f\"{type(exc).__name__}: {exc}\"}\n"
            "        overall_ok &= checks[\"neo4j\"][\"ok\"]\n"
            "    else:\n"
            "        checks[\"neo4j\"] = {\"ok\": False, \"error\": \"NEO4J_URI not set\"}\n"
            "        overall_ok = False\n"
            "\n"
            "    if not overall_ok:\n"
            "        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE\n"
            "\n"
            "    return {\n"
            "        \"status\": \"OK\" if overall_ok else \"DEGRADED\",\n"
            "        \"service\": \"eugene-ws\",\n"
            "        \"checks\": checks,\n"
            "    }"
        ),
        h.p("What it actually verifies", h.H2),
        *h.bullets([
            f"<b>{h.c('NEO4J_URI')} env var presence.</b> An unset/empty URI "
            f"short-circuits to {h.c('ok: False, error: &quot;NEO4J_URI not set&quot;')} "
            "without attempting any IO. This catches the common &quot;forgot "
            "to mount docker.env&quot; failure mode immediately.",
            f"<b>Neo4j Bolt reachability.</b> "
            f"{h.c('GraphDbConnectionFactory.remote_neo4j_instance_from_env()')} "
            f"(at {h.c('src/graph/infra/db/graph_db_connection_factory.py:53')}) "
            f"also reads {h.c('NEO4J_USERNAME')} and {h.c('NEO4J_PASSWORD')} "
            f"from the environment &mdash; so a {h.c('KeyError')} there is "
            "caught by the same try/except and surfaced as the error string. "
            "The driver is cached on the factory, so repeated probes do not "
            "reopen pools.",
            f"<b>Connectivity round-trip.</b> {h.c('driver.verify_connectivity()')} "
            "is a synchronous Bolt handshake against the server. It validates "
            "credentials, routing, and TLS (if configured). Any neo4j-driver "
            f"exception class is caught by the broad {h.c('except Exception')} &mdash; "
            f"this is deliberate so a probe never 500s, only {h.c('503')}s.",
            f"<b>Latency capture.</b> {h.c('time.perf_counter()')} bookends the "
            f"call; the integer millisecond reading lands in "
            f"{h.c('checks.neo4j.latency_ms')} on the happy path. It is "
            "omitted on failure (the timer end-point is never reached).",
        ]),
        h.p(
            f"Note: {h.c('overall_ok &amp;= checks[&quot;neo4j&quot;][&quot;ok&quot;]')} "
            "uses a bitwise AND on booleans, which is equivalent to logical "
            "AND but evaluates both sides &mdash; intentional, so new checks "
            "added later cannot accidentally short-circuit and skip their "
            "diagnostics.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 3. Response model ----------------------------- #
    story += [
        h.p("3. Response model", h.H1),
        h.p(
            "There is no Pydantic model. Both handlers are typed "
            f"{h.c('-&gt; dict[str, Any]')} and FastAPI serializes the dict "
            "directly. Three concrete shapes occur in practice:"
        ),
        h.p("Liveness, healthy (always)", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{ \"status\": \"OK\", \"service\": \"eugene-ws\" }"
        ),
        h.p("Readiness, healthy", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"OK\",\n"
            "  \"service\": \"eugene-ws\",\n"
            "  \"checks\": {\n"
            "    \"neo4j\": { \"ok\": true, \"latency_ms\": 7 }\n"
            "  }\n"
            "}"
        ),
        h.p("Readiness, degraded (Neo4j unreachable)", h.H2),
        h.code(
            "HTTP/1.1 503 Service Unavailable\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"DEGRADED\",\n"
            "  \"service\": \"eugene-ws\",\n"
            "  \"checks\": {\n"
            "    \"neo4j\": {\n"
            "      \"ok\": false,\n"
            "      \"error\": \"ServiceUnavailable: Could not connect to bolt://neo4j:7687\"\n"
            "    }\n"
            "  }\n"
            "}"
        ),
        h.p("Readiness, misconfigured (URI unset)", h.H2),
        h.code(
            "HTTP/1.1 503 Service Unavailable\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"status\": \"DEGRADED\",\n"
            "  \"service\": \"eugene-ws\",\n"
            "  \"checks\": {\n"
            "    \"neo4j\": { \"ok\": false, \"error\": \"NEO4J_URI not set\" }\n"
            "  }\n"
            "}"
        ),
        *h.bullets([
            f"{h.c('status')}: literal {h.c('OK')} or {h.c('DEGRADED')} &mdash; "
            "the only two values. Easy to grep, easy to alert on.",
            f"{h.c('service')}: the constant {h.c('&quot;eugene-ws&quot;')} &mdash; "
            "lets downstream aggregators distinguish this probe from the "
            "sibling agent / MCP services when scraping mixed logs.",
            f"{h.c('checks.&lt;name&gt;.error')} is a free-form "
            f"{h.c('&quot;ExceptionClass: message&quot;')} string &mdash; useful "
            "for humans, not for machines. Programmatic gating should key off "
            "the HTTP status code, not the error text.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 4. Use in k8s / docker-compose ---------------- #
    story += [
        h.p("4. Use in k8s / docker-compose", h.H1),
        h.p("docker-compose (docker-compose.yml:92-97)", h.H2),
        h.code(
            "eugene_ws:\n"
            "  ...\n"
            "  depends_on:\n"
            "    neo4j:\n"
            "      condition: service_healthy\n"
            "  healthcheck:\n"
            "    test: [\"CMD-SHELL\",\n"
            "      \"python -c \\\"import urllib.request; \"\n"
            "      \"urllib.request.urlopen('http://localhost:8000/health')\\\"\"]\n"
            "    interval: 10s\n"
            "    timeout: 5s\n"
            "    retries: 5\n"
            "    start_period: 15s"
        ),
        *h.bullets([
            f"Compose hits {h.c('/health')} (liveness), not "
            f"{h.c('/health/ready')}. The reason: in local-stack mode the "
            f"compose file already gates eugene_ws on "
            f"{h.c('neo4j: condition: service_healthy')}, so by the time "
            "Python starts, Neo4j is up. Liveness is enough to know the "
            "uvicorn process bound the port.",
            f"Downstream services ({h.c('eugene_mcp')}, "
            f"{h.c('eugene_agent_ws')}) then chain "
            f"{h.c('depends_on: eugene_ws: condition: service_healthy')} &mdash; "
            "this is how the agent tier waits for the API tier without "
            "polling.",
            f"{h.c('start_period: 15s')} gives the Python interpreter and "
            "FastAPI router-import block (which is non-trivial &mdash; see "
            f"{h.c('eugene_ws.py:31-78')}) time to come up before failed "
            "probes start counting against the retry budget.",
        ]),
        h.p("Kubernetes (recommended pattern)", h.H2),
        h.p(
            "There is no checked-in k8s manifest yet, but the route is shaped "
            f"for the canonical liveness/readiness split. {h.c('/health')} maps "
            f"to {h.c('livenessProbe')}; {h.c('/health/ready')} maps to "
            f"{h.c('readinessProbe')}:"
        ),
        h.code(
            "livenessProbe:\n"
            "  httpGet: { path: /health,       port: 8000 }\n"
            "  initialDelaySeconds: 15\n"
            "  periodSeconds: 10\n"
            "  failureThreshold: 3      # -&gt; restart pod\n"
            "readinessProbe:\n"
            "  httpGet: { path: /health/ready, port: 8000 }\n"
            "  initialDelaySeconds: 5\n"
            "  periodSeconds: 5\n"
            "  failureThreshold: 2      # -&gt; remove from Service endpoints"
        ),
        *h.bullets([
            "Readiness gating: a 503 from "
            f"{h.c('/health/ready')} causes the kubelet to drop the pod from "
            "Service endpoints, so kube-proxy / ingress stop sending it user "
            "traffic. The pod keeps running &mdash; no restart &mdash; and the "
            "next successful probe re-adds it to the rotation. This is the "
            "right behaviour when Neo4j is briefly unreachable: do not "
            "restart-storm the API tier.",
            "Liveness gating: a sustained failure on "
            f"{h.c('/health')} (which only fails if the Python event loop is "
            "wedged) triggers a pod restart. The endpoint is intentionally "
            "trivial so this signal is unambiguous.",
            f"Probes are exempt from auth because the router carries no auth "
            f"dependency &mdash; do not put them behind the global "
            f"{h.c('get_current_user')} dependency or the kubelet will see "
            "401 and consider the pod unhealthy.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 5. Debugging walk ----------------------------- #
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Bring the stack up: "
            f"{h.c('docker-compose up eugene_neo4j eugene_ws')}. Hit "
            f"{h.c('curl -i http://localhost:18000/health')} &mdash; expect a 200 "
            "within ~15s of the container starting.",
            f"Verify readiness: "
            f"{h.c('curl -sS http://localhost:18000/health/ready | jq .')}. "
            f"Expect {h.c('status: OK')} with a "
            f"{h.c('latency_ms')} field on the neo4j check &mdash; that confirms "
            "the Bolt round-trip actually happened.",
            f"Simulate Neo4j outage: "
            f"{h.c('docker-compose stop eugene_neo4j')}, then re-hit "
            f"{h.c('/health/ready')}. Expect HTTP 503 and a "
            f"{h.c('checks.neo4j.error')} like "
            f"{h.c('&quot;ServiceUnavailable: ...&quot;')}. Liveness "
            "({h.c('/health')}) should still be 200 &mdash; confirms the split.",
            f"Simulate misconfiguration: unset {h.c('NEO4J_URI')} in "
            f"{h.c('docker.env')} and restart eugene_ws. "
            f"{h.c('/health/ready')} should return 503 with "
            f"{h.c('error: &quot;NEO4J_URI not set&quot;')} immediately (no "
            "Bolt attempt).",
            f"Trace the driver path: breakpoint at "
            f"{h.c('src/router/health_router.py:34')} "
            f"({h.c('driver.verify_connectivity()')}). Step into the factory "
            f"at {h.c('graph_db_connection_factory.py:53')} to confirm the "
            "process-wide driver is reused (it is &mdash; the factory caches "
            f"in {h.c('cls._NEO4J_DRIVER')}, so repeated probes do not leak "
            "Bolt connections).",
        ]),
        h.Spacer(1, 10),

        # ----------------- 6. Reference index ---------------------------- #
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP entry\n"
            "  src/router/health_router.py                              # GET /health (L14), GET /health/ready (L19)\n"
            "  src/eugene_ws.py                                          # add_routers() L31, registered L58\n\n"
            "Dependencies pinged\n"
            "  src/graph/infra/db/graph_db_connection_factory.py        # remote_neo4j_instance_from_env (L53)\n"
            "                                                            # caches driver in cls._NEO4J_DRIVER (L49)\n"
            "  env vars: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD       # read by the factory\n\n"
            "Probe consumers\n"
            "  docker-compose.yml                                        # eugene_ws healthcheck L92-97 (uses /health)\n"
            "                                                            # eugene_mcp depends_on service_healthy L117-119\n"
            "  (no k8s manifest checked in yet; pattern in section 4)\n\n"
            "Related routers (for contrast)\n"
            "  src/router/root_router.py                                 # GET / -- service banner\n"
            "  src/router/release_notes_router.py                        # GET /release-notes\n"
        ),
    ]

    return story
