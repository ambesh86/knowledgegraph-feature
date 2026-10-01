import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from router.auth.eugene_jwts import validate_eugene_access_token
from router.auth.conf import SECURITY
from router.auth.const import EUGENE_AGENT_ALLOWLIST

logger = logging.getLogger(__name__)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),
):
    try:
        token = credentials.credentials
        user = validate_eugene_access_token(token)
    except HTTPException:
        raise
    except Exception as exc:
        # SEC-02 fix: invalid tokens must surface as 401, not 500
        logger.info(f"token validation failed: {type(exc).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_name = user.get("upn", "") if isinstance(user, dict) else ""
    # Empty allowlist = allow any authenticated user (dev/local default)
    if not EUGENE_AGENT_ALLOWLIST or user_name in EUGENE_AGENT_ALLOWLIST:
        return user

    # SEC-02 fix: return proper 403 Forbidden instead of bare Exception -> 500
    logger.info(f"access denied for upn (not in allowlist)")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied",
    )


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(SECURITY),
):
    return credentials.credentials
