"""Per-route flow guide for Eugene's root_router.

Endpoint: GET /

The bare service root. A trivial, auth-gated hello-world used as a
liveness / smoke endpoint. Walks an engineer from the FastAPI boundary
through the JWT dependency into the JSON shape returned to the caller.
Every reference is in path/to/file.py:line form so it can be opened
directly in an IDE.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_ROOT_FLOW_GUIDE.pdf"
TITLE = "Eugene Root Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---------- cover -------------------------------------------------------
    welcome_msg = h.c("&quot;Welcome to the euGENE API (+Microsoft Entra ID)!&quot;")
    bearer_dep = h.c("Depends(get_current_user)")
    story += [
        h.p("Eugene Root Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP boundary &rarr; bearer auth dependency &rarr; "
            "static welcome payload",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who "
            f"need a single, file-referenced trace of {h.c('GET /')} &mdash; the "
            "thinnest route in the service. There is no database call, no "
            f"adapter, and no mapper: the handler is three lines and returns a "
            f"two-key dict. The only moving part is the {bearer_dep} "
            "dependency, which validates the caller&#39;s JWT before the body is "
            "produced. Every reference uses the form "
            f"{h.c('path/to/file.py:line')} so you can open it directly in your "
            "IDE.",
        ),
        h.p("Reference endpoint", h.H2),
        h.p(
            f"{h.c('GET /')} &mdash; no path params, no query params, no body. "
            f"Requires a valid bearer token. Response is a plain JSON object "
            f"with two keys, {h.c('message')} and {h.c('user')}.",
        ),
        h.p("Sample call"),
        h.code(
            "curl -s 'http://localhost:8080/' \\\n"
            "  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5...' | jq .\n"
        ),
        h.p(
            f"Declared in {h.c('src/router/root_router.py:11-13')}. Router "
            f"prefix {h.c('&quot;&quot;')} (empty), tag {h.c('root')}.",
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
            "<b>Liveness signal</b> &mdash; load balancers, container probes, "
            "and curl-from-laptop sanity checks need a cheap endpoint that "
            "returns 200 when the process is up. The dedicated "
            f"{h.c('/health/*')} routes live on the health router; this root "
            "route serves the additional purpose of confirming that auth and "
            "routing are wired correctly end-to-end.",
            "<b>Auth smoke test</b> &mdash; because the handler depends on "
            f"{bearer_dep}, a 200 from {h.c('GET /')} proves that (a) your "
            "bearer token parses, (b) the Entra ID / JWT validator is "
            "reachable, and (c) the resulting user claims are being injected "
            "into handler arguments. A 401 here narrows the problem to auth.",
            "<b>Service banner</b> &mdash; the literal welcome string "
            f"({welcome_msg}) acknowledges the Microsoft Entra ID identity "
            "provider in front of Eugene, so an operator hitting the root "
            "with a working token sees confirmation of which auth backend is "
            "wired in.",
        ]),
        h.p("What it deliberately is not", h.H2),
        *h.bullets([
            f"<b>Not a health check.</b> Real health probes go to "
            f"{h.c('/health')} (see {h.c('src/router/health_router.py')}). "
            "Container orchestrators should target that path because it does "
            "not require a bearer token.",
            "<b>Not an OpenAPI landing page.</b> FastAPI&#39;s generated docs "
            f"live at {h.c('/docs')} and {h.c('/redoc')}; the root route does "
            "not redirect there.",
            "<b>Not a version endpoint.</b> Build / release metadata is served "
            f"by {h.c('release_notes_router')} ({h.c('src/router/')}). The "
            "root route returns a fixed string only.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 1. HTTP entry -----------------------------------------------
    include_line = h.c("app.include_router(router.router)")
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:33')} &mdash; "
            f"{h.c('from router import root_router, health_router, release_notes_router')}. "
            f"{h.c('src/eugene_ws.py:57')} appends {h.c('root_router')} to the "
            f"{h.c('routers')} list (immediately after the auth router so it is "
            "registered very early). The loop at the bottom of "
            f"{h.c('add_routers')} calls {include_line} on each, which is how "
            f"the bare {h.c('/')} path gets mounted on the FastAPI app.",
        ),
        h.p("Router file (verbatim)", h.H2),
        h.p(f"{h.c('src/router/root_router.py')}", h.PATH),
        h.code(
            "from fastapi import APIRouter, Depends\n"
            "\n"
            "from router.auth.auth import get_current_user\n"
            "\n"
            "router = APIRouter(\n"
            "    prefix=\"\",\n"
            "    tags=[\"root\"],\n"
            ")\n"
            "\n"
            "\n"
            "@router.get(\"/\")\n"
            "async def app_root(user: dict = Depends(get_current_user)):\n"
            "    return {\"message\": \"Welcome to the euGENE API (+Microsoft Entra ID)!\", \"user\": user}\n"
        ),
        h.p("Things to notice", h.H2),
        *h.bullets([
            f"<b>Empty prefix.</b> {h.c('prefix=&quot;&quot;')} means the route "
            f"binds at the literal {h.c('/')} of the app. Most other Eugene "
            f"routers use a path prefix ({h.c('/labels')}, {h.c('/drugs/aliases')}, "
            "etc.); this is the only one without.",
            f"<b>Tag.</b> {h.c('tags=[&quot;root&quot;]')} groups the operation "
            f"under a {h.c('root')} section in the auto-generated OpenAPI / "
            f"Swagger UI at {h.c('/docs')}.",
            f"<b>No {h.c('response_model')}.</b> Unlike most Eugene routes the "
            f"handler does not declare a Pydantic response model &mdash; the "
            f"returned dict is serialized as-is by FastAPI&#39;s default "
            f"{h.c('jsonable_encoder')}. See Section 3 for what this means in "
            "practice.",
            f"<b>{h.c('async def')} but no I/O.</b> The handler awaits nothing. "
            "The dependency itself is synchronous (see Section 2); FastAPI "
            "still happily resolves it.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 2. handler internals ----------------------------------------
    sec = h.c("SECURITY")
    cred = h.c("HTTPAuthorizationCredentials")
    validate = h.c("validate_eugene_access_token(token)")
    story += [
        h.p("2. Handler internals &mdash; the auth dependency", h.H1),
        h.p(
            f"The handler body itself is a single {h.c('return')} statement. "
            f"All non-trivial work happens before the body runs, inside "
            f"FastAPI&#39;s dependency-injection step that resolves "
            f"{bearer_dep}.",
        ),
        h.p("Dependency definition", h.H2),
        h.p(f"{h.c('src/router/auth/auth.py')}", h.PATH),
        h.code(
            "from fastapi import Depends\n"
            "from fastapi.security import HTTPAuthorizationCredentials\n"
            "\n"
            "from router.auth.eugene_jwts import validate_eugene_access_token\n"
            "from router.auth.conf import SECURITY\n"
            "\n"
            "\n"
            "def get_current_user(\n"
            "    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),\n"
            "):\n"
            "    token = credentials.credentials\n"
            "    return validate_eugene_access_token(token)\n"
        ),
        h.p("Resolution order", h.H2),
        *h.bullets([
            f"FastAPI sees the handler signature {h.c('user: dict = Depends(get_current_user)')} "
            f"and walks {h.c('get_current_user')} first.",
            f"{h.c('get_current_user')} itself depends on {sec} &mdash; an "
            f"{h.c('HTTPBearer')} (or equivalent) instance from "
            f"{h.c('src/router/auth/conf.py')}. FastAPI parses the "
            f"{h.c('Authorization')} header and produces an "
            f"{cred} dataclass whose {h.c('.credentials')} attribute holds the "
            "raw bearer token string.",
            f"{validate} performs the actual signature / claims check. On "
            "success it returns a dict of user claims; on failure it raises an "
            "HTTPException that short-circuits the request with 401.",
            f"The returned dict is bound to the handler&#39;s {h.c('user')} "
            "parameter and embedded directly in the response body.",
        ]),
        h.p("What happens if the header is missing", h.H2),
        *h.bullets([
            f"{sec} ({h.c('HTTPBearer(...)')}) rejects requests with no "
            f"{h.c('Authorization')} header before {h.c('get_current_user')} "
            "even runs. The status code (401 vs 403) depends on the "
            f"{h.c('auto_error')} flag used to construct it &mdash; see "
            f"{h.c('src/router/auth/conf.py')}.",
            f"If the header is present but malformed, {sec} raises directly. "
            f"If the header is well-formed but the token is invalid, "
            f"{validate} raises. Either way the handler body never executes "
            "and the client sees a 4xx.",
        ]),
        h.p("Set your first breakpoint", h.H2),
        h.p(
            f"At {h.c('src/router/root_router.py:13')} (the {h.c('return')} "
            f"line). Inspect:",
        ),
        *h.bullets([
            f"{h.c('user')} &mdash; the dict produced by "
            f"{validate}. The shape is whatever the JWT validator returns "
            f"(claims map &mdash; typically {h.c('sub')}, {h.c('email')}, "
            f"{h.c('name')}, {h.c('roles')}, etc.).",
        ]),
        h.PageBreak(),
    ]

    # ---------- 3. response model -------------------------------------------
    msg_key = h.c("message")
    user_key = h.c("user")
    story += [
        h.p("3. Response model", h.H1),
        h.p(
            f"The handler returns a Python {h.c('dict')} literal. FastAPI "
            f"serializes it through the default {h.c('jsonable_encoder')} "
            f"and the route has no {h.c('response_model')}, so what you see on "
            "the wire is exactly the dict structure, with the user claims "
            f"nested under {user_key}.",
        ),
        h.p("Response shape (verbatim from the handler)", h.H2),
        h.code(
            "{\n"
            "  \"message\": \"Welcome to the euGENE API (+Microsoft Entra ID)!\",\n"
            "  \"user\":    { ... claims from validate_eugene_access_token ... }\n"
            "}\n"
        ),
        h.p("Example response with concrete claims", h.H2),
        h.code(
            "{\n"
            "  \"message\": \"Welcome to the euGENE API (+Microsoft Entra ID)!\",\n"
            "  \"user\": {\n"
            "    \"sub\":   \"a3b8...\",\n"
            "    \"email\": \"engineer@example.com\",\n"
            "    \"name\":  \"Engineer Eugene\",\n"
            "    \"roles\": [\"eugene.reader\"],\n"
            "    \"iss\":   \"https://login.microsoftonline.com/&lt;tenant&gt;/v2.0\",\n"
            "    \"aud\":   \"&lt;client-id&gt;\",\n"
            "    \"exp\":   1747700000\n"
            "  }\n"
            "}\n"
        ),
        h.p("Implications of having no response_model", h.H2),
        *h.bullets([
            f"<b>Claim shape is uncontracted.</b> Whatever {validate} returns "
            f"is what the client gets. If the validator starts including new "
            f"claim fields, the response widens silently. There is no Pydantic "
            "schema to break a downstream consumer.",
            f"<b>No {h.c('response_model_exclude_none')} filter.</b> Any "
            f"{h.c('None')} values in the claims dict are serialized as JSON "
            f"{h.c('null')}.",
            f"<b>OpenAPI shows {h.c('200')} with no schema.</b> Swagger UI at "
            f"{h.c('/docs')} will document the operation but cannot show a "
            "response example. Clients should treat this body as opaque except "
            f"for the {msg_key} key.",
        ]),
        h.p("Status codes", h.H2),
        *h.bullets([
            f"{h.c('200 OK')} &mdash; valid bearer token, claims returned.",
            f"{h.c('401 Unauthorized')} &mdash; missing / malformed header, or "
            f"invalid token (raised inside {validate}).",
            f"{h.c('403 Forbidden')} &mdash; possible depending on how "
            f"{sec} ({h.c('HTTPBearer')}) is configured.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 4. use in production ----------------------------------------
    story += [
        h.p("4. Use in production &mdash; heartbeat and smoke", h.H1),
        h.p(
            "Because the route does no I/O beyond JWT validation, it is "
            "cheap enough to call repeatedly. It is best thought of as an "
            "auth-aware heartbeat rather than a feature endpoint.",
        ),
        h.p("Recommended uses", h.H2),
        *h.bullets([
            f"<b>Post-deploy smoke test.</b> CI/CD pipelines hit {h.c('GET /')} "
            f"with a service-principal token to confirm a freshly deployed "
            f"container has come up <i>and</i> is wired to the correct "
            "Entra ID tenant. A 200 here is stronger evidence than an "
            "unauthenticated /health ping.",
            "<b>Token validation harness.</b> When a client team reports "
            f"&quot;my token isn&#39;t working,&quot; ask them to curl "
            f"{h.c('GET /')} first. A 401 isolates the problem to the token; "
            "a 200 isolates it to a downstream route.",
            "<b>Banner / hello-world.</b> Operators logging in to a new "
            "environment via Swagger UI see the welcome string and confirmed "
            "claims, which orients them quickly.",
        ]),
        h.p("Anti-patterns", h.H2),
        *h.bullets([
            f"<b>Don&#39;t use it as a Kubernetes liveness probe.</b> Probes "
            f"shouldn&#39;t require a bearer token; use {h.c('/health')} "
            "instead.",
            f"<b>Don&#39;t parse {user_key} as a stable contract.</b> The "
            f"claims dict shape is whatever {validate} returns; a real client "
            f"should call a dedicated user-info endpoint if one exists, not "
            "scrape this route&#39;s response.",
            f"<b>Don&#39;t poll at high frequency without caching the token.</b> "
            "Each call hits the JWT validator; under heavy polling that "
            f"becomes the bottleneck rather than {h.c('app_root')} itself.",
        ]),
        h.p("Observability tips", h.H2),
        *h.bullets([
            f"Successful calls log nothing handler-side &mdash; the handler is "
            "three lines. Any log line you see for this route comes from the "
            "FastAPI access log or the JWT validator.",
            f"If you need to confirm a particular caller hit the root, "
            "instrument the access log to include the JWT subject claim "
            f"({h.c('sub')}) for {h.c('GET /')} responses.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 5. debugging walk -------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Bring the service up: {h.c('docker-compose up eugene_ws')}. Hit "
            f"{h.c('curl -s -i http://localhost:8080/')} with no header &mdash; "
            f"expect a 401/403 from {sec}. This confirms the route is "
            "registered and auth is active.",
            f"Now hit it with a valid token: "
            f"{h.c('curl -s -H &#39;Authorization: Bearer &lt;jwt&gt;&#39; http://localhost:8080/ | jq .')}. "
            f"Expect 200 with the welcome string and a populated "
            f"{user_key} object. Set a breakpoint at "
            f"{h.c('src/router/root_router.py:13')} and inspect "
            f"{h.c('user')} to confirm the claim set you expect (sub, email, "
            "roles).",
            f"If 401 with a token you believe is valid: step into "
            f"{h.c('src/router/auth/auth.py:11')} to inspect "
            f"{h.c('credentials.credentials')}, then into "
            f"{h.c('validate_eugene_access_token')} "
            f"({h.c('src/router/auth/eugene_jwts.py')}) to see which check "
            "fails (signature, issuer, audience, expiry).",
        ]),
        h.PageBreak(),
    ]

    # ---------- 6. reference index ------------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Router\n"
            "  src/router/root_router.py                         (entire file, 13 lines)\n"
            "\n"
            "Wiring\n"
            "  src/eugene_ws.py                                  (line 33 import, line 57 list)\n"
            "\n"
            "Auth dependency\n"
            "  src/router/auth/auth.py                           (get_current_user)\n"
            "  src/router/auth/conf.py                           (SECURITY = HTTPBearer(...))\n"
            "  src/router/auth/eugene_jwts.py                    (validate_eugene_access_token)\n"
            "\n"
            "Related operational routes\n"
            "  src/router/health_router.py                       (unauthenticated liveness)\n"
            "  src/router/release_notes_router.py                (build / version metadata)\n"
        ),
        h.p("Key takeaways", h.H2),
        *h.bullets([
            f"{h.c('GET /')} is a three-line, auth-gated hello-world. No DB, "
            "no adapter, no mapper, no response model.",
            f"Its job is operational: confirm the service is up <i>and</i> "
            "the Entra ID JWT path is healthy. For pure liveness, use "
            f"{h.c('/health')} instead because it doesn&#39;t require a token.",
            f"The {user_key} field in the response is whatever "
            f"{validate} returns &mdash; treat it as opaque, do not contract "
            "on individual claim keys.",
            "It is the only Eugene router that mounts at an empty prefix; "
            "everything else is namespaced under a path segment.",
        ]),
    ]

    return story
