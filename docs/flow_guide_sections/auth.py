"""ReportLab section: Eugene auth router end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 6-8 PDF pages.

Covers the main service's auth endpoints under src/router/auth/auth_router.py
(NOT the agent-ws auth).
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_AUTH_FLOW_GUIDE.pdf"
TITLE = "Eugene Auth - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------- title --------------------------------- #
    story += [
        h.p("Eugene Auth &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: MS Entra ID Authorization Code flow &rarr; "
            "MSAL token exchange &rarr; Eugene HS256 JWT mint &rarr; "
            "<font face='Courier'>HTTPBearer</font> dependency &rarr; "
            "per-request claim validation",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how a Eugene API caller obtains an "
            "access token and how every protected route verifies that token. The "
            "auth router exposes four endpoints: an Entra ID login redirect, an "
            "OIDC callback that exchanges the authorization code for an Entra "
            "access token and mints a Eugene JWT, a JSON token endpoint for local "
            "SPA development, and a <font face='Courier'>/auth/whoami</font> debug "
            "probe. Every reference uses the form "
            "<font face='Courier'>path/to/file.py:line</font>.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            "<font face='Courier'>GET /login</font> &mdash; either redirects to Microsoft Entra ID (production) or short-circuits to a local-development token (when <font face='Courier'>ENVIRONMENT == 'local'</font>).",
            "<font face='Courier'>GET {REDIRECT_PATH}</font> &mdash; the OIDC redirect URI; Microsoft posts the authorization <font face='Courier'>code</font> here and Eugene exchanges it for tokens.",
            "<font face='Courier'>POST /auth/token</font> &mdash; JSON access token for programmatic / Next.js SPA clients. Local mode only.",
            "<font face='Courier'>GET /auth/whoami</font> &mdash; returns the decoded Eugene JWT claims; the canonical example of <font face='Courier'>Depends(get_current_user)</font>.",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "The Eugene token is <b>HS256</b>-signed with a shared secret "
            "(<font face='Courier'>EUGENE_CLIENT_SECRET</font>) &mdash; this is a "
            "first-party JWT used purely for authorization inside Eugene, not an "
            "Entra-issued token. The Entra access token never leaves the auth "
            "callback; it is decoded once to lift the user's "
            "<font face='Courier'>upn / tid / sub</font> claims and is then "
            "discarded in favor of the freshly minted Eugene token. See "
            "<a href='https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/'>RS256 vs HS256</a> "
            "&mdash; rotating the shared secret invalidates every live Eugene token.",
        ),
        h.PageBreak(),
    ]

    # 0. Auth model
    story += [
        h.p("0. Auth model (read this first)", h.H1),
        h.p("Two token types are in play:"),
        h.code(
            "Entra ID access token  (RS256, issued by Microsoft)\n"
            "  issuer:    https://login.microsoftonline.com/<tenant_id>/v2.0\n"
            "  audience:  ENTRA_CLIENT_ID\n"
            "  algorithm: RS256 (verified via JWKS for ID tokens)\n"
            "  lifetime:  controlled by Entra (~60-90 min)\n"
            "  scope:     ENTRA_SCOPE (env-driven, comma-separated)\n"
            "\n"
            "Eugene access token    (HS256, issued by this service)\n"
            "  issuer:    https://eugene.ai.cslg1.cslg.net/<EUGENE_TENANT_ID>\n"
            "  audience:  api://eugene/<EUGENE_CLIENT_ID>\n"
            "  algorithm: HS256 (shared secret: EUGENE_CLIENT_SECRET)\n"
            "  lifetime:  EUGENE_TOKEN_TTL_SECS = 24 * 60 * 60  (24h)\n"
            "  claims:    iss, aud, iat, exp, tid, sub, upn, oid, name,\n"
            "             preferred_username, roles\n"
        ),
        *h.bullets([
            "All values are pinned in <font face='Courier'>src/router/auth/const.py:44-48</font>.",
            "Two roles are defined in <font face='Courier'>const.py:51-52</font>: <font face='Courier'>user.public.read</font> and <font face='Courier'>user.confidential.read</font>.",
            "Role mapping is a static dict keyed by <font face='Courier'>tenant_id|upn</font> in <font face='Courier'>src/router/auth/roles.py:17-31</font>. Unknown users fall through to <font face='Courier'>DEFAULT_ROLES = {user.public.read}</font>.",
            "The Eugene token carries the Entra <font face='Courier'>tid / sub / upn / oid</font> claims verbatim so downstream services can trace requests back to the Entra principal.",
        ]),
        h.PageBreak(),
    ]

    # 1. HTTP entry
    story += [
        h.p("1. HTTP entry &mdash; the auth router", h.H1),
        h.p("<font face='Courier'>src/router/auth/auth_router.py</font>", h.PATH),
        *h.bullets([
            "Router is registered in <font face='Courier'>src/eugene_ws.py:32,56</font> via <font face='Courier'>from router.auth import auth_router</font> and an <font face='Courier'>app.include_router(auth_router, ...)</font>.",
            "Prefix is the empty string (<font face='Courier'>prefix=''</font>, line 24) so paths are mounted at the root.",
            "Tag <font face='Courier'>'auth'</font> groups the endpoints under one Swagger section (line 25).",
        ]),
        h.p("GET /login (line 29)", h.H2),
        h.p(
            "Branches on <font face='Courier'>ENVIRONMENT</font>: when it is "
            "<font face='Courier'>'local'</font> or <font face='Courier'>MASL_APP</font> "
            "is <font face='Courier'>None</font>, the handler mints a local "
            "development Eugene token and returns it embedded in an HTML page (so "
            "the developer can copy/paste it into Swagger). In production it asks "
            "MSAL for an authorization URL and 302s the browser to Microsoft.",
        ),
        h.code(
            "auth_url = MASL_APP.get_authorization_request_url(\n"
            "    scopes=ENTRA_SCOPE,\n"
            "    redirect_uri=REDIRECT_URI,\n"
            "    response_mode='query',\n"
            ")\n"
            "return RedirectResponse(auth_url)"
        ),
        h.p("GET {REDIRECT_PATH} &mdash; auth_callback (line 83)", h.H2),
        *h.bullets([
            "Reads <font face='Courier'>request.query_params</font>; returns 401 if Microsoft passed back an <font face='Courier'>error</font> or if <font face='Courier'>code</font> is missing.",
            "Calls <font face='Courier'>MASL_APP.acquire_token_by_authorization_code(code, scopes, redirect_uri)</font> to swap the code for an Entra payload.",
            "Hands the payload to <font face='Courier'>_validate_or_raise()</font> (line 120), which calls <font face='Courier'>decode_entra_id_token</font> for full JWKS-backed validation.",
            "Calls <font face='Courier'>entra_token_to_eugene_token(entra_token)</font> &mdash; this is where the Eugene JWT is minted.",
            "Returns an HTML page containing both tokens (lines 136-147); designed for developer copy/paste, not browser session use.",
        ]),
        h.p("POST /auth/token (line 59)", h.H2),
        h.p(
            "JSON endpoint for SPA / programmatic clients. Refuses with "
            "<font face='Courier'>HTTP 403</font> if "
            "<font face='Courier'>ENVIRONMENT != 'local'</font> &mdash; production "
            "must walk the redirect flow. The shape is the conventional OAuth-style "
            "envelope:",
        ),
        h.code(
            "{\n"
            "  \"access_token\": \"<eugene-jwt>\",\n"
            "  \"token_type\":   \"Bearer\",\n"
            "  \"expires_in\":   86400\n"
            "}"
        ),
        h.p("GET /auth/whoami (line 54)", h.H2),
        h.p(
            "The only protected endpoint in this router. Declares "
            "<font face='Courier'>user: dict = Depends(get_current_user)</font> &mdash; "
            "FastAPI resolves the dependency, which runs JWT validation, and the "
            "handler simply echoes the claims as JSON.",
        ),
        h.PageBreak(),
    ]

    # 2. Token validation internals
    story += [
        h.p("2. Token validation internals", h.H1),
        h.p("<font face='Courier'>src/router/auth/auth.py</font>", h.PATH),
        h.p(
            "<font face='Courier'>get_current_user</font> is a 5-line FastAPI "
            "dependency: it pulls "
            "<font face='Courier'>HTTPAuthorizationCredentials</font> from the "
            "<font face='Courier'>HTTPBearer</font> security scheme (declared as "
            "<font face='Courier'>SECURITY</font> in "
            "<font face='Courier'>conf.py:10</font>) and forwards the raw token to "
            "<font face='Courier'>validate_eugene_access_token</font>:",
        ),
        h.code(
            "def get_current_user(\n"
            "    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),\n"
            "):\n"
            "    token = credentials.credentials\n"
            "    return validate_eugene_access_token(token)"
        ),
        h.p("<font face='Courier'>src/router/auth/eugene_jwts.py</font>", h.PATH),
        h.p(
            "<font face='Courier'>validate_eugene_access_token</font> (line 22) is "
            "the workhorse. It uses "
            "<font face='Courier'>python-jose</font> (<font face='Courier'>from jose import jwt</font>) "
            "to decode and verify the HS256 signature, then enforces a small set of "
            "required claims:",
        ),
        h.code(
            "claims = jwt.decode(\n"
            "    token=token,\n"
            "    key=EUGENE_CLIENT_SECRET,\n"
            "    algorithms=[EUGENE_TOKEN_ALGORITHM],   # 'HS256'\n"
            "    audience=EUGENE_TOKEN_AUDIENCE,\n"
            "    issuer=EUGENE_TOKEN_ISSUER,\n"
            "    options={\n"
            "        'require_exp': True,\n"
            "        'require_iat': True,\n"
            "        'verify_aud': True,\n"
            "        'verify_iss': True,\n"
            "    },\n"
            ")\n"
            "\n"
            "required_claims = ['tid', 'sub', 'roles', 'upn']\n"
            "missing = [c for c in required_claims if c not in claims]\n"
            "if missing:\n"
            "    raise HTTPException(status_code=401,\n"
            "                        detail='Invalid token structure')"
        ),
        *h.bullets([
            "<font face='Courier'>ExpiredSignatureError</font> &rarr; 401 'Token expired'.",
            "<font face='Courier'>JWTError</font> (bad signature, wrong audience, wrong issuer, malformed) &rarr; 401 'Invalid token'.",
            "Any other exception &rarr; 500 'Authentication error' (logged as <font face='Courier'>logger.error</font>).",
            "On success the full claim dict is returned to the handler; FastAPI injects it as <font face='Courier'>user: dict</font>.",
        ]),
        h.p("Entra ID token validation", h.H2),
        h.p("<font face='Courier'>src/router/auth/entra_id_jwts.py</font>", h.PATH),
        h.p(
            "Used during the OIDC callback only. "
            "<font face='Courier'>decode_entra_id_token</font> (line 63) uses "
            "<font face='Courier'>PyJWT</font> (<font face='Courier'>import jwt</font> &mdash; "
            "note the name collision with python-jose) to verify the ID token with "
            "RS256 against the Microsoft JWKS. "
            "<font face='Courier'>decode_entra_access_token</font> (line 87) "
            "deliberately skips signature verification "
            "(<font face='Courier'>options={'verify_signature': False}</font>) &mdash; "
            "the comment notes Entra access tokens cannot be verified locally, only "
            "their claims are lifted.",
        ),
        h.PageBreak(),
    ]

    # 3. Response model
    story += [
        h.p("3. Response model &mdash; token / user payload", h.H1),
        h.p("Eugene token claims (the dict returned by <font face='Courier'>validate_eugene_access_token</font>)", h.H2),
        h.code(
            "{\n"
            "  \"iss\":  \"https://eugene.ai.cslg1.cslg.net/<EUGENE_TENANT_ID>\",\n"
            "  \"aud\":  \"api://eugene/<EUGENE_CLIENT_ID>\",\n"
            "  \"iat\":  1715900000,\n"
            "  \"exp\":  1715986400,\n"
            "  \"tid\":  \"<entra-tenant-id>\",\n"
            "  \"sub\":  \"<entra-subject-id>\",\n"
            "  \"upn\":  \"Damian.Knopp@cslbehring.com\",\n"
            "  \"oid\":  \"<entra-object-id>\",\n"
            "  \"name\": \"Damian Knopp\",\n"
            "  \"preferred_username\": \"Damian.Knopp@cslbehring.com\",\n"
            "  \"roles\": [\"user.public.read\", \"user.confidential.read\"]\n"
            "}"
        ),
        h.p("/auth/whoami response", h.H2),
        h.code(
            "{\n"
            "  \"user\": {\n"
            "    \"iss\":  \"...\",\n"
            "    \"aud\":  \"...\",\n"
            "    \"tid\":  \"...\",\n"
            "    \"sub\":  \"...\",\n"
            "    \"upn\":  \"Damian.Knopp@cslbehring.com\",\n"
            "    \"roles\": [\"user.public.read\"]\n"
            "  }\n"
            "}"
        ),
        h.p("/auth/token response", h.H2),
        h.code(
            "{\n"
            "  \"access_token\": \"eyJhbGciOiJIUzI1NiIs...<base64>...\",\n"
            "  \"token_type\":   \"Bearer\",\n"
            "  \"expires_in\":   86400\n"
            "}"
        ),
        h.p("Token minting (for completeness)", h.H2),
        h.p(
            "<font face='Courier'>_issue_internal_eugene_token</font> "
            "(<font face='Courier'>eugene_jwts.py:124</font>) is the only place Eugene "
            "tokens are signed:",
        ),
        h.code(
            "payload = {\n"
            "    'iss': EUGENE_TOKEN_ISSUER,\n"
            "    'aud': EUGENE_TOKEN_AUDIENCE,\n"
            "    'iat': now,\n"
            "    'exp': now + timedelta(seconds=EUGENE_TOKEN_TTL_SECS),\n"
            "    **claims,   # tid, sub, upn, oid, name, preferred_username, roles\n"
            "}\n"
            "return jwt.encode(\n"
            "    claims=payload,\n"
            "    key=EUGENE_CLIENT_SECRET,\n"
            "    algorithm=EUGENE_TOKEN_ALGORITHM,   # 'HS256'\n"
            ")"
        ),
        h.PageBreak(),
    ]

    # 4. Dependencies
    story += [
        h.p("4. Dependencies &mdash; env, MSAL, JWKS cache", h.H1),
        h.p("<font face='Courier'>src/router/auth/conf.py</font>", h.PATH),
        h.p(
            "Every parameter is loaded from <font face='Courier'>os.environ</font> "
            "via <font face='Courier'>_env_value()</font> (line 84) &mdash; missing "
            "values raise <font face='Courier'>ValueError</font> at import time, so "
            "the service fails fast on misconfiguration.",
        ),
        h.p("Required environment variables", h.H2),
        h.code(
            "ENVIRONMENT             # 'local' enables the dev shortcuts\n"
            "ENTRA_CLIENT_ID         # Entra application (client) id\n"
            "ENTRA_CLIENT_SECRET     # Entra application client secret\n"
            "ENTRA_TENANT_ID         # Entra directory (tenant) id\n"
            "ENTRA_AUTHORITY         # https://login.microsoftonline.com/<tenant>\n"
            "ENTRA_SCOPE             # comma-separated, split() in conf.py:55-57\n"
            "REDIRECT_PATH           # e.g. /auth/callback\n"
            "REDIRECT_URI            # full callback URL Microsoft posts back to\n"
            "EUGENE_CLIENT_ID        # used in audience: api://eugene/<id>\n"
            "EUGENE_CLIENT_SECRET    # HS256 signing key for Eugene tokens\n"
            "EUGENE_TENANT_ID        # used in issuer + role map key\n"
        ),
        h.p("Derived constants", h.H2),
        *h.bullets([
            "<font face='Courier'>ENTRA_ISSUER = f'https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0'</font> (<font face='Courier'>const.py:28</font>).",
            "<font face='Courier'>ENTRA_JWKS_URI</font> is fetched from <font face='Courier'>&lt;issuer&gt;/.well-known/openid-configuration</font> at import time (<font face='Courier'>conf.py:66-68</font>) &mdash; skipped in local mode.",
            "<font face='Courier'>MASL_APP</font> is a <font face='Courier'>ConfidentialClientApplication</font> from the <font face='Courier'>msal</font> Python library; <font face='Courier'>None</font> in local mode (<font face='Courier'>const.py:34-38</font>).",
            "<font face='Courier'>EUGENE_TOKEN_ISSUER = f'https://eugene.ai.cslg1.cslg.net/{EUGENE_TENANT_ID}'</font> and <font face='Courier'>EUGENE_TOKEN_AUDIENCE = f'api://eugene/{EUGENE_CLIENT_ID}'</font> (<font face='Courier'>const.py:44, 48</font>).",
        ]),
        h.p("JWKS key fetching and caching", h.H2),
        h.p(
            "<font face='Courier'>entra_id_jwts.py</font> keeps an in-process dict "
            "(<font face='Courier'>_jwks_cache</font>, line 17) keyed by JWKS URI "
            "with an <b>8 hour</b> TTL "
            "(<font face='Courier'>_jwks_cache_ttl_secs = 60 * 60 * 8</font>, line "
            "16). <font face='Courier'>fetch_entra_jwks()</font> (line 20) checks "
            "freshness, refreshes via <font face='Courier'>requests.get</font>, and "
            "falls back to the stale cache on network failure. "
            "<font face='Courier'>fetch_entra_signing_key()</font> (line 47) reads "
            "the unverified <font face='Courier'>kid</font> from the token header "
            "and matches it against the cached JWKS, materialising the public key "
            "via <font face='Courier'>RSAAlgorithm.from_jwk(key)</font>.",
        ),
        h.p("Libraries in play", h.H2),
        *h.bullets([
            "<font face='Courier'>python-jose</font> (<font face='Courier'>from jose import jwt</font>) &mdash; used for the Eugene HS256 token (mint &amp; verify) in <font face='Courier'>eugene_jwts.py</font>.",
            "<font face='Courier'>PyJWT</font> (<font face='Courier'>import jwt</font> in <font face='Courier'>entra_id_jwts.py</font>) &mdash; used for RS256 verification of Entra ID tokens and for unverified base64 decoding of Entra access tokens.",
            "<font face='Courier'>msal</font> &mdash; <font face='Courier'>ConfidentialClientApplication</font> for Authorization Code flow.",
            "<font face='Courier'>fastapi.security.HTTPBearer</font> &mdash; declared once as <font face='Courier'>SECURITY</font> in <font face='Courier'>conf.py:10</font> and reused by every protected route across the service.",
        ]),
        h.PageBreak(),
    ]

    # 5. Debugging walk
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "Set <font face='Courier'>ENVIRONMENT=local</font> in <font face='Courier'>.env</font> and bring the service up: <font face='Courier'>docker-compose up eugene_ws</font>. With <font face='Courier'>MASL_APP=None</font>, <font face='Courier'>/login</font> short-circuits to a local token &mdash; useful when Entra is not reachable from your laptop.",
            "Curl the JSON variant: <font face='Courier'>curl -X POST http://localhost:8000/auth/token</font>. Paste the <font face='Courier'>access_token</font> into <a href='https://jwt.ms'>https://jwt.ms</a> to inspect <font face='Courier'>iss / aud / exp / roles</font>.",
            "Hit <font face='Courier'>GET /auth/whoami</font> with <font face='Courier'>Authorization: Bearer &lt;token&gt;</font> and breakpoint at <font face='Courier'>src/router/auth/eugene_jwts.py:28</font> to watch <font face='Courier'>jwt.decode</font> verify the signature, audience, and issuer in one call.",
            "To force the production path, unset <font face='Courier'>ENVIRONMENT</font> (or set it to anything other than <font face='Courier'>'local'</font>) and ensure the Entra env vars are populated. Hit <font face='Courier'>/login</font> in a browser; you should be 302'd to <font face='Courier'>login.microsoftonline.com</font>. Microsoft then redirects to <font face='Courier'>REDIRECT_URI</font> with <font face='Courier'>?code=...</font>.",
            "Breakpoint at <font face='Courier'>auth_router.py:98</font> (the <font face='Courier'>acquire_token_by_authorization_code</font> call) to inspect Entra's response &mdash; you should see <font face='Courier'>access_token</font>, <font face='Courier'>id_token</font>, and <font face='Courier'>id_token_claims</font>. Step into <font face='Courier'>entra_token_to_eugene_token</font> (<font face='Courier'>eugene_jwts.py:63</font>) to watch the upn/tid/sub lift, the role lookup, and the HS256 mint.",
            "To exercise role mapping, add your <font face='Courier'>upn</font> to <font face='Courier'>USER_ROLE_MAP</font> in <font face='Courier'>src/router/auth/roles.py:17-31</font> and confirm the <font face='Courier'>roles</font> claim on the next token includes <font face='Courier'>user.confidential.read</font>. Unknown users get <font face='Courier'>DEFAULT_ROLES</font> only.",
        ]),
        h.PageBreak(),
    ]

    # 6. Reference index
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP entry\n"
            "  src/router/auth/auth_router.py\n"
            "    /login              line 29\n"
            "    /auth/whoami        line 54\n"
            "    /auth/token         line 59\n"
            "    {REDIRECT_PATH}     line 83  (auth_callback)\n"
            "    _validate_or_raise  line 120\n"
            "    _generate_token_html line 136\n"
            "\n"
            "Dependency (FastAPI Depends)\n"
            "  src/router/auth/auth.py            get_current_user\n"
            "  src/router/auth/conf.py:10         SECURITY = HTTPBearer(...)\n"
            "\n"
            "Token validation + mint\n"
            "  src/router/auth/eugene_jwts.py\n"
            "    validate_eugene_access_token            line 22\n"
            "    entra_token_to_eugene_token             line 63\n"
            "    issue_local_development_eugene_token_with_roles  line 96\n"
            "    _issue_eugene_token_with_roles          line 113\n"
            "    _issue_internal_eugene_token            line 124\n"
            "\n"
            "Entra ID JWKS / decode\n"
            "  src/router/auth/entra_id_jwts.py\n"
            "    fetch_entra_jwks            line 20  (8h TTL cache)\n"
            "    fetch_entra_signing_key     line 47\n"
            "    decode_entra_id_token       line 63  (RS256 + JWKS)\n"
            "    decode_entra_access_token   line 87  (no signature verify)\n"
            "\n"
            "Config + env\n"
            "  src/router/auth/conf.py\n"
            "  src/router/auth/const.py\n"
            "\n"
            "Roles\n"
            "  src/router/auth/roles.py\n"
            "    USER_ROLE_MAP        line 17\n"
            "    DEFAULT_ROLES        line 33\n"
            "    load_roles_for_user  line 36\n"
            "    load_roles_for_local_development  line 63\n"
            "\n"
            "Registration\n"
            "  src/eugene_ws.py:32,56   include_router(auth_router, ...)\n"
        ),
    ]

    return story
