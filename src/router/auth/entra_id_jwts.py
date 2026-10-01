import logging
import time

import jwt
import requests
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from jwt.algorithms import RSAAlgorithm


from router.auth.const import ENTRA_CLIENT_ID, ENTRA_JWKS_URI, ENTRA_ISSUER

logger = logging.getLogger(__name__)


# Cache for JWKS keys with TTL
_jwks_cache_ttl_secs = 60 * 60 * 8
_jwks_cache: dict[str, tuple[float, dict]] = {}


def fetch_entra_jwks() -> dict:
    """Get JWKS keys from the JWKS URI with caching."""
    current_time = time.time()

    # Check cache first
    if ENTRA_JWKS_URI in _jwks_cache:
        cached_time, cached_keys = _jwks_cache[ENTRA_JWKS_URI]
        if current_time - cached_time < _jwks_cache_ttl_secs:
            return cached_keys

    # Fetch fresh keys if cache is expired or empty
    try:
        response = requests.get(ENTRA_JWKS_URI)
        response.raise_for_status()
        jwks = response.json()

        # Update cache
        _jwks_cache[ENTRA_JWKS_URI] = (current_time, jwks)
        return jwks
    except requests.RequestException as e:
        # If we can't fetch new keys, try to use cached ones if available
        if ENTRA_JWKS_URI in _jwks_cache:
            _, cached_keys = _jwks_cache[ENTRA_JWKS_URI]
            return cached_keys
        raise Exception(f"Failed to fetch JWKS: {str(e)}")


def fetch_entra_signing_key(token: str):
    """Get the signing key for the given token."""
    jwks = fetch_entra_jwks()
    unverified_header = jwt.get_unverified_header(token)

    logger.debug(f"unverified kid: {unverified_header['kid']}")
    jwks_kids = [key["kid"] for key in jwks["keys"]]
    logger.debug(f"comparing against known jwks kids: {jwks_kids}")

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            return RSAAlgorithm.from_jwk(key)

    raise Exception("No matching key found for the token's kid")


def decode_entra_id_token(token: str) -> dict:
    try:
        logger.debug(f"{token}")
        signing_key = fetch_entra_signing_key(token)

        payload = jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            audience=ENTRA_CLIENT_ID,
            issuer=ENTRA_ISSUER,
        )

        return payload
    except ExpiredSignatureError:
        raise Exception("Token has expired")
    except JWTClaimsError as e:
        raise Exception(f"Invalid token claims: {str(e)}")
    except JWTError as e:
        raise Exception(f"Invalid token: {str(e)}")
    except Exception as e:
        raise Exception(f"Token decode failed: {str(e)}")


def decode_entra_access_token(token: str) -> dict:
    try:
        # NOTE: the upn field is only in the access token and not the token_claims or id_token
        # NOTE: The CSL auth team advised to use the upn field
        # See fields in, https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
        # NOTE: MS Entra ID Access tokens do not need, cannot be verified locally because they are already verified on the MS side?
        logger.debug(f"{token}")
        # Base64 decode the payload (middle part)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        raise Exception(f"Token decode failed: {str(e)}")
