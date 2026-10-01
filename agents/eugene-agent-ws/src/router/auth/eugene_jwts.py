import logging

from fastapi import HTTPException
import jwt

from router.auth.const import (
    EUGENE_CLIENT_SECRET,
    EUGENE_TOKEN_ALGORITHM,
    EUGENE_TOKEN_AUDIENCE,
    EUGENE_TOKEN_ISSUER,
)

logger = logging.getLogger(__name__)


def validate_eugene_access_token(token: str) -> dict:
    if not token:
        logger.warning("Token validation failed: No token provided")
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        claims = jwt.decode(
            jwt=token,
            key=EUGENE_CLIENT_SECRET,
            algorithms=[EUGENE_TOKEN_ALGORITHM],
            audience=EUGENE_TOKEN_AUDIENCE,
            issuer=EUGENE_TOKEN_ISSUER,
            options={
                "require_exp": True,
                "require_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        # Validate required custom claims
        required_claims = ["tid", "sub", "roles", "upn"]
        missing_claims = [claim for claim in required_claims if claim not in claims]
        if missing_claims:
            logger.warning(f"Token missing required claims: {missing_claims}")
            raise HTTPException(status_code=401, detail="Invalid token structure")

        logger.info(f"Token validated for upn: {claims.get('upn')}")
        return claims

    except Exception as e:
        logger.error(f"Unexpected error during token validation: {type(e).__name__}")
        raise HTTPException(status_code=401, detail="Authentication error")
