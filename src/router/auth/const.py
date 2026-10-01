from router.auth.conf import (
    authority,
    client_id,
    client_secret,
    entra_jwks_uri,
    environment,
    eugene_client_id,
    eugene_client_secret,
    eugene_tenant_id,
    msal_app,
    redirect_path,
    redirect_uri,
    scope,
    tenant_id,
)


# ENTRA ID PARAMETERS
ENVIRONMENT = environment()

ENTRA_CLIENT_ID = client_id()
ENTRA_CLIENT_SECRET = client_secret()
ENTRA_TENANT_ID = tenant_id()
REDIRECT_PATH = redirect_path()
REDIRECT_URI = redirect_uri()
ENTRA_AUTHORITY = authority()
ENTRA_SCOPE = scope()
ENTRA_ISSUER = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0"
ENTRA_JWKS_URI = (
    entra_jwks_uri(issuer=ENTRA_ISSUER)
    if ENVIRONMENT != "local"
    else None
)
MASL_APP = (
    msal_app(ENTRA_CLIENT_ID, ENTRA_AUTHORITY, ENTRA_CLIENT_SECRET)
    if ENVIRONMENT != "local"
    else None
)

# CSL EUGENE PARAMETERS
EUGENE_TENANT_ID = eugene_tenant_id()
EUGENE_CLIENT_ID = eugene_client_id()
EUGENE_CLIENT_SECRET = eugene_client_secret()
EUGENE_TOKEN_ISSUER = f"https://eugene.ai.cslg1.cslg.net/{EUGENE_TENANT_ID}"
EUGENE_TOKEN_TTL_SECS = 24 * 60 * 60
# https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/
EUGENE_TOKEN_ALGORITHM = "HS256"
EUGENE_TOKEN_AUDIENCE = f"api://eugene/{EUGENE_CLIENT_ID}"

# ROLES
EUGENE_USER_PUBLIC_READ_ROLE = "user.public.read"
EUGENE_USER_CONFIDENTIAL_READ_ROLE = "user.confidential.read"
