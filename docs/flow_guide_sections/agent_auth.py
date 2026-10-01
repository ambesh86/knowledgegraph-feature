"""ReportLab section: Eugene agent-ws auth route end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 6-8 PDF pages.

Covers the agent-ws auth surface at
agents/eugene-agent-ws/src/router/auth/auth_router.py plus the dependencies
in router/auth/auth.py, router/auth/eugene_jwts.py, and the bearer-token
forwarding from the agent service down to eugene-mcp.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_AGENT_AUTH_FLOW_GUIDE.pdf"
TITLE = "Eugene Agent Auth - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # --------------------------- title page ------------------------------- #
    courier_path = h.c("/agent/api/auth/whoami")
    story += [
        h.p("Eugene Agent Auth &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: UI MS Entra access token &rarr; "
            "<font face='Courier'>HTTPBearer</font> dependency &rarr; "
            "PyJWT HS256 validation &rarr; allowlist check &rarr; "
            "downstream bearer forwarding to eugene-mcp",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers working on the <b>eugene-agent-ws</b> FastAPI service "
            "(the Strands ReAct agent behind the Next.js chat UI). This guide "
            "walks the auth surface exposed at " + courier_path + " plus the "
            "two reusable dependencies &mdash; "
            + h.c("get_current_user")
            + " and "
            + h.c("get_current_token")
            + " &mdash; that every protected query route declares. Each "
            "reference uses the form "
            + h.c("path/to/file.py:line")
            + "."
        ),
        h.p("Two auth surfaces, one service", h.H2),
        h.p(
            "Eugene has two FastAPI services and they do <i>not</i> share an "
            "auth router. The <b>main service</b> "
            + h.c("src/foundation/router/auth_router.py")
            + " runs the MS Entra ID Authorization Code login + JWT mint "
            "(documented separately). The <b>agent-ws</b> service covered "
            "here is a <i>pure resource server</i>: it never mints tokens. "
            "It accepts a bearer token already issued by the main service "
            "(or directly by Entra in some dev setups), validates it locally "
            "with PyJWT, and propagates the same raw token downstream to "
            "the MCP server when the agent invokes tools."
        ),
        h.p("Caveat", h.H2),
        h.p(
            "The router only exposes one endpoint ("
            + h.c("GET /auth/whoami")
            + "); the heavy lifting is in the FastAPI dependencies that "
            "every query route shares. Read sections 2 and 4 together to "
            "see how a single inbound token authorises the request and "
            "then propagates into the MCP HTTP client."
        ),
        h.PageBreak(),
    ]

    # ------------------------ 0. auth model ------------------------------- #
    story += [
        h.p("0. Auth model (read this first)", h.H1),
        h.p(
            "The agent-ws service treats every inbound HTTP request as "
            "authenticated <i>only</i> if it carries a valid Eugene access "
            "token in an "
            + h.c("Authorization: Bearer &lt;jwt&gt;")
            + " header. The expected token shape is fixed by "
            + h.c("router/auth/const.py")
            + ":"
        ),
        h.code(
            "EUGENE_TENANT_ID    = eugene_tenant_id()\n"
            "EUGENE_CLIENT_ID    = eugene_client_id()\n"
            "EUGENE_CLIENT_SECRET = eugene_client_secret()\n"
            "EUGENE_TOKEN_ISSUER   = f\"https://eugene.ai.cslg1.cslg.net/{EUGENE_TENANT_ID}\"\n"
            "EUGENE_TOKEN_ALGORITHM = \"HS256\"\n"
            "EUGENE_TOKEN_AUDIENCE  = f\"api://eugene/{EUGENE_CLIENT_ID}\"\n"
            "EUGENE_AGENT_ALLOWLIST = eugene_agent_allowlist()"
        ),
        *h.bullets([
            "<b>Issuer (iss)</b>: "
            + h.c("https://eugene.ai.cslg1.cslg.net/&lt;tenant&gt;")
            + " &mdash; the main Eugene service when it mints a token after "
            "the Entra OIDC exchange.",
            "<b>Audience (aud)</b>: "
            + h.c("api://eugene/&lt;client_id&gt;")
            + " &mdash; both <b>eugene-ws</b> and <b>eugene-agent-ws</b> "
            "accept the same audience because they share "
            + h.c("EUGENE_CLIENT_ID")
            + ".",
            "<b>Algorithm</b>: " + h.c("HS256") + " (symmetric, signed with "
            + h.c("EUGENE_CLIENT_SECRET") + "). The agent-ws process must be "
            "started with the same secret as the issuing main service.",
            "<b>Required claims</b>: " + h.c("exp, iat, aud, iss, tid, sub, "
            "roles, upn") + ". The first four are checked by PyJWT options; "
            "the last four are checked explicitly in "
            + h.c("validate_eugene_access_token") + ".",
            "<b>Allowlist</b>: " + h.c("EUGENE_AGENT_ALLOWLIST") + " is a "
            "pipe-delimited set of " + h.c("upn") + " values. An empty set "
            "means &lsquo;allow any authenticated user&rsquo; (dev default); "
            "a populated set acts as a hard ACL on top of the JWT check.",
        ]),
        h.p("Note on Entra ID", h.H2),
        h.p(
            "The UI (<b>eugene-agent-ui-next</b>) acquires a Microsoft Entra "
            "ID access token via MSAL and posts it as the bearer. The agent "
            "service does <i>not</i> call Microsoft directly &mdash; it "
            "trusts the symmetric signature, which is valid because the main "
            "Eugene service re-mints an HS256 token in front of the raw "
            "Entra token. The plumbing on the UI side is "
            + h.c("agents/eugene-agent-ui-next/app/api/auth/token/route.ts")
            + "; this guide treats it as a black box producing a Eugene JWT."
        ),
        h.PageBreak(),
    ]

    # ------------------------ 1. HTTP entry ------------------------------- #
    story += [
        h.p("1. HTTP entry &mdash; the router", h.H1),
        h.p(h.c("agents/eugene-agent-ws/src/router/auth/auth_router.py"), h.PATH),
        h.p(
            "The router itself is intentionally tiny &mdash; nine lines of "
            "logic. Only one endpoint is exposed; everything protected lives "
            "under other routers (query, health, root) that reuse the same "
            "dependencies."
        ),
        h.code(
            "router = APIRouter(\n"
            "    prefix=\"\",\n"
            "    tags=[\"auth\"],\n"
            ")\n\n"
            "@router.get(\"/auth/whoami\")\n"
            "def protected(user: dict = Depends(get_current_user)):\n"
            "    return {\"user\": user}"
        ),
        *h.bullets([
            "Mount point: " + h.c("eugene_chat_ws.py:30-37")
            + " calls " + h.c("add_routers(app)") + " which imports "
            + h.c("router.auth.auth_router") + " and registers it.",
            "FastAPI app declares " + h.c("root_path=\"/agent/api\"")
            + " in " + h.c("eugene_chat_ws.py:53-57") + ", so the deployed "
            "URL is " + h.c("GET /agent/api/auth/whoami") + " (behind "
            "ALB + Cognito on AWS, plain on localhost:18001).",
            "Rate limiting via slowapi is applied app-wide ("
            + h.c("eugene_chat_ws.py:60-63") + ") &mdash; the auth endpoint "
            "inherits the default limiter.",
            "No path or query params. The single &lsquo;input&rsquo; is the "
            + h.c("Authorization") + " header consumed by " + h.c("HTTPBearer") + ".",
            "Returns " + h.c("{\"user\": &lt;claims dict&gt;}") + " on 200; "
            "401 on missing/invalid token; 403 on allowlist denial.",
        ]),
        h.p("Endpoint reference", h.H2),
        h.code(
            "GET /agent/api/auth/whoami\n"
            "    Headers : Authorization: Bearer <eugene-jwt>\n"
            "    200     : { \"user\": { \"tid\": ..., \"sub\": ..., \"upn\": ..., \"roles\": [...] } }\n"
            "    401     : { \"detail\": \"Invalid or expired token\" }\n"
            "    403     : { \"detail\": \"Access denied\" }"
        ),
        h.PageBreak(),
    ]

    # -------------------- 2. token validation internals ------------------- #
    story += [
        h.p("2. Token validation internals", h.H1),
        h.p(h.c("agents/eugene-agent-ws/src/router/auth/auth.py"), h.PATH),
        h.p(
            "Two dependencies live here. Every protected route picks one or "
            "both. They both source the bearer credential from "
            + h.c("SECURITY = HTTPBearer(...)") + " defined in "
            + h.c("router/auth/conf.py:6") + "."
        ),
        h.p("get_current_user (auth.py:13)", h.H2),
        h.code(
            "def get_current_user(\n"
            "    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),\n"
            "):\n"
            "    try:\n"
            "        token = credentials.credentials\n"
            "        user = validate_eugene_access_token(token)\n"
            "    except HTTPException:\n"
            "        raise\n"
            "    except Exception as exc:\n"
            "        # SEC-02 fix: invalid tokens must surface as 401, not 500\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
            "            detail=\"Invalid or expired token\",\n"
            "            headers={\"WWW-Authenticate\": \"Bearer\"},\n"
            "        ) from exc\n\n"
            "    user_name = user.get(\"upn\", \"\") if isinstance(user, dict) else \"\"\n"
            "    if not EUGENE_AGENT_ALLOWLIST or user_name in EUGENE_AGENT_ALLOWLIST:\n"
            "        return user\n\n"
            "    raise HTTPException(\n"
            "        status_code=status.HTTP_403_FORBIDDEN,\n"
            "        detail=\"Access denied\",\n"
            "    )"
        ),
        *h.bullets([
            "Order of operations: <i>(a)</i> extract bearer string, "
            "<i>(b)</i> validate via PyJWT, <i>(c)</i> normalise exceptions "
            "to a 401, <i>(d)</i> apply allowlist &rarr; 403 if denied.",
            "The bare " + h.c("except HTTPException: raise") + " preserves "
            "any 401/403 raised inside " + h.c("validate_eugene_access_token")
            + " (e.g. " + h.c("\"Invalid token structure\"") + ").",
            "The " + h.c("SEC-02") + " fix is load-bearing: before it, a "
            "malformed JWT would bubble out as a 500. The catch-all rewrites "
            "anything non-HTTPException as a 401 with the proper "
            + h.c("WWW-Authenticate: Bearer") + " header.",
        ]),
        h.p("get_current_token (auth.py:43)", h.H2),
        h.code(
            "async def get_current_token(\n"
            "    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),\n"
            "):\n"
            "    return credentials.credentials"
        ),
        h.p(
            "Pure pass-through: returns the raw bearer string. This is the "
            "dependency used by " + h.c("/query") + " and "
            + h.c("/query/stream") + " in "
            + h.c("query/router/chat_query_agent_router.py:38,86")
            + " so the same token can be forwarded to MCP (see section 4). "
            "It does <b>not</b> re-validate &mdash; routes that need both "
            "validation <i>and</i> raw forwarding declare both deps:"
        ),
        h.code(
            "token: str  = Depends(get_current_token)\n"
            "user:  dict = Depends(get_current_user)"
        ),
        h.PageBreak(),
    ]

    # -------------------- 2b. PyJWT decode internals ---------------------- #
    story += [
        h.p("2b. PyJWT decode &mdash; the actual signature check", h.H1),
        h.p(h.c("agents/eugene-agent-ws/src/router/auth/eugene_jwts.py"), h.PATH),
        h.p(
            "JWT library: <b>PyJWT</b> (" + h.c("import jwt") + " at line 4). "
            "No JWKS, no async, no caching &mdash; HS256 symmetric verify only."
        ),
        h.code(
            "def validate_eugene_access_token(token: str) -> dict:\n"
            "    if not token:\n"
            "        raise HTTPException(status_code=401, detail=\"Authentication required\")\n\n"
            "    try:\n"
            "        claims = jwt.decode(\n"
            "            jwt=token,\n"
            "            key=EUGENE_CLIENT_SECRET,\n"
            "            algorithms=[EUGENE_TOKEN_ALGORITHM],   # [\"HS256\"]\n"
            "            audience=EUGENE_TOKEN_AUDIENCE,\n"
            "            issuer=EUGENE_TOKEN_ISSUER,\n"
            "            options={\n"
            "                \"require_exp\": True,\n"
            "                \"require_iat\": True,\n"
            "                \"verify_aud\": True,\n"
            "                \"verify_iss\": True,\n"
            "            },\n"
            "        )\n\n"
            "        required_claims = [\"tid\", \"sub\", \"roles\", \"upn\"]\n"
            "        missing_claims = [c for c in required_claims if c not in claims]\n"
            "        if missing_claims:\n"
            "            raise HTTPException(status_code=401, detail=\"Invalid token structure\")\n\n"
            "        return claims\n"
            "    except Exception as e:\n"
            "        raise HTTPException(status_code=401, detail=\"Authentication error\")"
        ),
        *h.bullets([
            "<b>Signature</b>: HS256 with the shared "
            + h.c("EUGENE_CLIENT_SECRET") + ". Any drift between the main "
            "service&rsquo;s secret and the agent service&rsquo;s secret "
            "manifests as a 401 here.",
            "<b>Time claims</b>: " + h.c("exp") + " and " + h.c("iat")
            + " are required (PyJWT raises " + h.c("ExpiredSignatureError")
            + " on expired " + h.c("exp") + "). " + h.c("nbf") + " is not "
            "enforced.",
            "<b>iss/aud</b>: enforced by PyJWT options; mismatch raises "
            + h.c("InvalidIssuerError") + " or " + h.c("InvalidAudienceError")
            + " &rarr; caught and surfaced as 401.",
            "<b>Custom claims</b>: " + h.c("tid, sub, roles, upn") + " checked "
            "explicitly. Missing any one of them &rarr; 401 with "
            + h.c("\"Invalid token structure\"") + ".",
            "<b>Broad except</b>: the final " + h.c("except Exception") + " "
            "is intentionally broad to keep error details out of responses; "
            "the only client-visible message is "
            + h.c("\"Authentication error\"") + ".",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 3. response model ------------------------------ #
    story += [
        h.p("3. Response model &mdash; user payload shape", h.H1),
        h.p(
            "There is no pydantic " + h.c("response_model") + " on the auth "
            "route &mdash; the handler returns a raw dict. The shape is "
            "whatever PyJWT decoded, wrapped in a "
            + h.c("\"user\"") + " key:"
        ),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n\n"
            "{\n"
            "  \"user\": {\n"
            "    \"iss\":   \"https://eugene.ai.cslg1.cslg.net/<tenant-id>\",\n"
            "    \"aud\":   \"api://eugene/<client-id>\",\n"
            "    \"iat\":   1737000000,\n"
            "    \"exp\":   1737003600,\n"
            "    \"tid\":   \"<entra-tenant-guid>\",\n"
            "    \"sub\":   \"<entra-object-id>\",\n"
            "    \"upn\":   \"jane.doe@example.com\",\n"
            "    \"roles\": [\"eugene.agent.user\"]\n"
            "  }\n"
            "}"
        ),
        *h.bullets([
            h.c("upn") + " is what the chat router logs ("
            + h.c("chat_query_agent_router.py:42") + ", "
            + h.c("chat_query_agent_router.py:90") + ") and what the "
            "allowlist filter compares against.",
            h.c("roles") + " is currently informational &mdash; no RBAC "
            "decisions are made on it inside agent-ws. The allowlist is the "
            "only authorisation gate.",
            "Because there is no " + h.c("response_model") + ", any extra "
            "claims your IdP includes (e.g. " + h.c("email") + ", "
            + h.c("name") + ") will pass through verbatim. Treat the response "
            "as informational, not as a stable contract.",
        ]),
        h.p("Failure shapes", h.H2),
        h.code(
            "401 (no header / bad signature / expired / bad iss/aud / missing claim)\n"
            "    { \"detail\": \"Invalid or expired token\" }\n"
            "    WWW-Authenticate: Bearer\n\n"
            "401 (claims missing tid/sub/roles/upn) - upstream message\n"
            "    { \"detail\": \"Invalid token structure\" }\n\n"
            "403 (signed token but upn not in EUGENE_AGENT_ALLOWLIST)\n"
            "    { \"detail\": \"Access denied\" }"
        ),
        h.PageBreak(),
    ]

    # --------------- 4. token forwarding to MCP --------------------------- #
    story += [
        h.p("4. Token forwarding to eugene-mcp", h.H1),
        h.p(
            "Every protected query route declares "
            + h.c("token: str = Depends(get_current_token)")
            + " and passes that token down into the Strands agent so the "
            "MCP HTTP client can re-attach it on every tool call. This is "
            "the &lsquo;trusted subsystem with on-behalf-of forwarding&rsquo; "
            "pattern &mdash; agent-ws does not re-mint, swap, or downgrade "
            "the token; the same JWT that authorised the inbound HTTP "
            "request authorises every outbound MCP call it triggers."
        ),
        h.p("Route &rarr; agent (chat_query_agent_router.py:51-56)", h.H2),
        h.code(
            "response = eugene_agent.execute(\n"
            "    token=token,                       # raw bearer from get_current_token\n"
            "    user_prompt=prompt,\n"
            "    conversation_id=chat_request.conversation_id,\n"
            "    include_tools=tools,\n"
            ")"
        ),
        h.p("Agent &rarr; MCP client (eugene_data_agent.py:283-295)", h.H2),
        h.code(
            "def _build_mcp_client(self, token: str) -> MCPClient:\n"
            "    # SEC-01 fix: default verify=True; dev can opt out via\n"
            "    # EUGENE_MCP_VERIFY_SSL=false\n"
            "    verify = _MCP_VERIFY_SSL\n"
            "    return MCPClient(\n"
            "        lambda: streamable_http_client(\n"
            "            url=self.eugene_mcp_server_url,\n"
            "            http_client=httpx.AsyncClient(\n"
            "                verify=verify,\n"
            "                headers={\"Authorization\": f\"Bearer {token}\"},\n"
            "                timeout=httpx.Timeout(\n"
            "                    connect=10.0, read=60.0, write=30.0, pool=10.0\n"
            "                ),\n"
            "            ),\n"
            "        )\n"
            "    )"
        ),
        *h.bullets([
            "The header is built once per request: each chat invocation "
            "constructs a fresh " + h.c("httpx.AsyncClient") + " with the "
            "current user&rsquo;s bearer baked into its default headers.",
            "MCP itself validates the same JWT independently &mdash; see the "
            "MCP auth router. A token that passes agent-ws but fails MCP "
            "(e.g. secret rotation skew between services) surfaces as a 401 "
            "from the MCP tool call, which Strands wraps as a tool error.",
            "SEC-01: TLS verify defaults to true. Override only in dev with "
            + h.c("EUGENE_MCP_VERIFY_SSL=false") + ".",
            "There is <b>no</b> token caching, no refresh, and no Entra "
            "OBO exchange in agent-ws &mdash; the inbound and outbound "
            "tokens are byte-identical for the lifetime of the chat call.",
            "If the chat call exceeds the JWT&rsquo;s "
            + h.c("exp") + ", subsequent MCP tool calls inside that ReAct "
            "loop will start 401&rsquo;ing. There is no automatic retry.",
        ]),
        h.PageBreak(),
    ]

    # ------------------- 5. debugging walk -------------------------------- #
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "Bring the stack up locally: "
            + h.c("docker-compose up eugene_neo4j eugene_ws eugene_mcp")
            + " then run the agent-ws on the host with "
            + h.c("python -m uvicorn eugene_chat_ws:app --reload --port 18001")
            + ".",
            "Mint a token by signing in through the Next.js UI and grabbing "
            "the bearer from the network tab (header on any "
            + h.c("/agent/api/...") + " request) &mdash; or call the main "
            "service&rsquo;s " + h.c("POST /auth/token") + " directly.",
            "Smoke test: "
            + h.c("curl -H \"Authorization: Bearer $TOKEN\" "
                  "http://localhost:18001/agent/api/auth/whoami")
            + " &rarr; expect 200 with the claims dict. Strip the header to "
            "confirm 401 with " + h.c("WWW-Authenticate: Bearer") + ".",
            "Breakpoint " + h.c("router/auth/eugene_jwts.py:22") + " (the "
            + h.c("jwt.decode") + " call) to inspect raw claims before the "
            "required-claims check. PyJWT will already have validated "
            + h.c("exp/iat/aud/iss") + " by the time you land on the next "
            "line.",
            "Breakpoint " + h.c("router/auth/auth.py:32") + " to watch the "
            "allowlist branch &mdash; if a user gets a surprise 403, this is "
            "almost always a stale " + h.c("EUGENE_AGENT_ALLOWLIST") + " env "
            "var.",
            "For MCP forwarding, breakpoint "
            + h.c("query/agent/eugene_data_agent.py:291") + " and confirm "
            "the bearer string matches the one you sent. Mismatches usually "
            "mean a dependency override is constructing the agent at module "
            "load time instead of per-request.",
        ]),
        h.Spacer(1, 10),

        # ------------------ 6. reference index ---------------------------- #
        h.p("6. Reference index", h.H1),
        h.code(
            "Auth model / config\n"
            "  agents/eugene-agent-ws/src/router/auth/conf.py        # HTTPBearer, env getters\n"
            "  agents/eugene-agent-ws/src/router/auth/const.py       # iss/aud/alg/allowlist\n\n"
            "HTTP entry\n"
            "  agents/eugene-agent-ws/src/router/auth/auth_router.py # GET /auth/whoami\n"
            "  agents/eugene-agent-ws/src/eugene_chat_ws.py          # add_routers, root_path=/agent/api\n\n"
            "Dependencies + validation\n"
            "  agents/eugene-agent-ws/src/router/auth/auth.py        # get_current_user, get_current_token\n"
            "  agents/eugene-agent-ws/src/router/auth/eugene_jwts.py # PyJWT decode + required-claims check\n\n"
            "Token forwarding\n"
            "  agents/eugene-agent-ws/src/query/router/chat_query_agent_router.py  # token=Depends(get_current_token)\n"
            "  agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py:283-295 # MCPClient bearer header\n\n"
            "UI side (out of scope for this guide)\n"
            "  agents/eugene-agent-ui-next/app/api/auth/token/route.ts            # MSAL token acquisition\n"
        ),
    ]

    return story
