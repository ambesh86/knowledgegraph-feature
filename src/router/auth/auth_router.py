import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from router.auth.auth import get_current_user
from router.auth.const import (
    ENVIRONMENT,
    MASL_APP,
    REDIRECT_PATH,
    REDIRECT_URI,
    ENTRA_SCOPE,
)
from router.auth.eugene_jwts import (
    entra_token_to_eugene_token,
    issue_local_development_eugene_token_with_roles,
)
from router.auth.entra_id_jwts import decode_entra_id_token

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    tags=["auth"],
)


@router.get("/login")
def login():
    if ENVIRONMENT and ENVIRONMENT == "local" or not MASL_APP:
        logger.info("test local auth")
        token = issue_local_development_eugene_token_with_roles()
        return HTMLResponse(
            _generate_token_html(
                eugene_access_token=token,
                entra_access_token="NO ID TOKEN FOR LOCAL DEVELOPMENT",
            )
        )

    logger.info(f"/login, redirecting to MASL. Scopes: {ENTRA_SCOPE}")
    # create auth URL for Authorization Code flow
    auth_url = MASL_APP.get_authorization_request_url(
        scopes=ENTRA_SCOPE,
        redirect_uri=REDIRECT_URI,
        response_mode="query",
        # optional state / nonce can be added to session when using in production
    )
    # this login flow should be outside swagger and the API
    # ideally we would redirect to a webapp
    return RedirectResponse(auth_url)


@router.get("/auth/whoami")
def protected(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.post("/auth/token")
def issue_local_token():
    """JSON token endpoint for programmatic/SPA clients (Next.js UI).

    Only usable in local mode — production must go through the Entra ID flow.
    Returns { access_token, token_type, expires_in }.
    """
    if ENVIRONMENT != "local":
        raise HTTPException(
            status_code=403,
            detail="Local token endpoint disabled; use /login (Entra ID flow).",
        )
    token = issue_local_development_eugene_token_with_roles()
    from router.auth.const import EUGENE_TOKEN_TTL_SECS

    return JSONResponse(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": EUGENE_TOKEN_TTL_SECS,
        }
    )


@router.get(REDIRECT_PATH)
async def auth_callback(request: Request):
    logger.info(f"{REDIRECT_PATH} called")
    if not MASL_APP:
        logger.warning(f"This endpoint requires MASL to be instantiated!")

    # Microsoft will redirect here with ?code=...
    params = dict(request.query_params)
    if "error" in params:
        return JSONResponse({"error": params}, status_code=401)

    code = params.get("code")
    if not code:
        raise HTTPException(status_code=401, detail="Missing code in callback")

    entra_token = MASL_APP.acquire_token_by_authorization_code(
        code=code,
        scopes=ENTRA_SCOPE,
        redirect_uri=REDIRECT_URI,
    )
    logger.debug(f"{entra_token}")
    _validate_or_raise(entra_token=entra_token)
    # id_token_claims is a dict of standardized OIDC claims (sub, name, preferred_username, email, etc.)
    # see, https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference

    eugene_access_token = entra_token_to_eugene_token(entra_token)
    logger.debug(f"{eugene_access_token}")
    # return RedirectResponse("/")

    return HTMLResponse(
        _generate_token_html(
            eugene_access_token=eugene_access_token,
            entra_access_token=entra_token["access_token"],
        )
    )


def _validate_or_raise(entra_token: dict) -> None:
    # result may have 'access_token', 'id_token', 'id_token_claims', or 'error'
    if "error" in entra_token:
        raise HTTPException(status_code=401, detail=entra_token)

    if "id_token" in entra_token:
        try:
            # Validate the ID token
            validated_token = decode_entra_id_token(entra_token["id_token"])
            logger.info(f"Validated token claims: {validated_token}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid ID token: {str(e)}")
    else:
        raise HTTPException(status_code=401, detail=entra_token)


def _generate_token_html(eugene_access_token: str, entra_access_token: str) -> str:
    return f"""
        <h3>Authn/Authz Tokens</h3>
        <div>
        <p>In <a href="/docs" target="_blank">Swagger</a>, click the authorize lock icon and paste the EUGENE access token to be used as a <code>Bearer ...</code> request</p>
        <p>EUGENE API ACCESS TOKEN (authz):</p>
        <textarea rows="20" cols="100">{eugene_access_token}</textarea>
        <p>ENTRA ID TOKEN (authn):</p>
        <textarea rows="20" cols="100">{entra_access_token}</textarea>
        <p>To view either token, paste them into <a href="https://jwt.ms" target="_blank">https://jwt.ms</a>, a Microsoft JWT debugging tool.</p>
        </div>
        """
