from router.auth.conf import (
    environment,
    eugene_client_id,
    eugene_client_secret,
    eugene_tenant_id,
    eugene_agent_allowlist,
)


ENVIRONMENT = environment()

# CSL EUGENE PARAMETERS
EUGENE_TENANT_ID = eugene_tenant_id()
EUGENE_CLIENT_ID = eugene_client_id()
EUGENE_CLIENT_SECRET = eugene_client_secret()
EUGENE_TOKEN_ISSUER = f"https://eugene.ai.cslg1.cslg.net/{EUGENE_TENANT_ID}"
# https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/
EUGENE_TOKEN_ALGORITHM = "HS256"
EUGENE_TOKEN_AUDIENCE = f"api://eugene/{EUGENE_CLIENT_ID}"
EUGENE_AGENT_ALLOWLIST = eugene_agent_allowlist()
