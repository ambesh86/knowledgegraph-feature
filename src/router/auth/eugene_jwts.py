from datetime import datetime, timedelta, timezone
import logging
import os

from fastapi import HTTPException
from jose import jwt, JWTError, ExpiredSignatureError

from router.auth.const import (
    EUGENE_CLIENT_SECRET,
    EUGENE_TENANT_ID,
    EUGENE_TOKEN_ALGORITHM,
    EUGENE_TOKEN_AUDIENCE,
    EUGENE_TOKEN_ISSUER,
    EUGENE_TOKEN_TTL_SECS,
)
from router.auth.roles import load_roles_for_local_development, load_roles_for_user
from router.auth.entra_id_jwts import decode_entra_access_token


logger = logging.getLogger(__name__)


def validate_eugene_access_token(token: str) -> dict:
    if not token:
        logger.warning("Token validation failed: No token provided")
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        claims = jwt.decode(
            token=token,
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

    except ExpiredSignatureError:
        logger.warning("Token validation failed: Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError as e:
        logger.warning(f"Token validation failed: {type(e).__name__}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Authentication error")


def entra_token_to_eugene_token(entra_token: dict) -> str:
    if "access_token" not in entra_token:
        raise ValueError("Missing access_token entra payload")

    access_token = decode_entra_access_token(entra_token["access_token"])
    NAME = "name"
    PREFERRED_USERNAME = "preferred_username"
    UPN = "upn"
    OID = "oid"
    SUB = "sub"
    # id_token_claims is a dict of standardized OIDC claims (sub, name, preferred_username, email, etc.)
    # see, https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
    tenant_id = access_token.get("tid")
    subject = access_token.get(SUB)
    upn = access_token.get(UPN)

    if not tenant_id or not subject or not upn:
        raise ValueError("Missing tid, sub, or upn from oidc token!")

    user = {
        NAME: access_token.get(NAME) or "",
        PREFERRED_USERNAME: access_token.get(PREFERRED_USERNAME) or upn,
        UPN: upn,
        OID: access_token.get(OID) or "",
        SUB: subject,
    }
    logger.info(f"entra id returned user claims: {user}")

    return _issue_eugene_token_with_roles(
        tenant_id=tenant_id, upn=upn, user_profile=user
    )


def issue_local_development_eugene_token_with_roles() -> str:
    # Allow override via env so deployments hitting a prod backend can mint
    # tokens whose UPN is in the prod allowlist (otherwise the prod agent
    # rejects the JWT and returns 500).
    preferred_username = os.environ.get(
        "EUGENE_DEV_UPN", "eugene.test@cslhering.com"
    )
    user = os.environ.get("EUGENE_DEV_USER") or preferred_username.split("@", 1)[0]
    roles = load_roles_for_local_development()
    return _issue_internal_eugene_token(
        claims={
            "tid": EUGENE_TENANT_ID,
            "sub": user,
            "roles": roles,
            "name": user,
            "preferred_username": preferred_username,
            "upn": preferred_username,
            "oid": "",
        }
    )


def _issue_eugene_token_with_roles(
    tenant_id: str, upn: str, user_profile: dict[str, str]
) -> str:
    roles = load_roles_for_user(upn=upn)
    logger.info(f"tenant: {tenant_id} upn: {upn} roles: {roles}")
    token = _issue_internal_eugene_token(
        claims={"tid": tenant_id, "upn": upn, "roles": roles, **user_profile}
    )
    return token


def _issue_internal_eugene_token(claims: dict[str, str | list[str]]) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "iss": EUGENE_TOKEN_ISSUER,
        "aud": EUGENE_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=EUGENE_TOKEN_TTL_SECS),
        **claims,
    }

    logger.info(f"creating access token for payload: {payload}")

    return jwt.encode(
        claims=payload,
        key=EUGENE_CLIENT_SECRET,
        algorithm=EUGENE_TOKEN_ALGORITHM,
    )
