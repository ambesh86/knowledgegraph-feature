import logging
import os

from fastmcp.server.auth.providers.jwt import JWTVerifier
from dotenv import find_dotenv, load_dotenv

from auth.verifier import _generate_jwt_verifier

logger = logging.getLogger(__name__)


def load_env() -> None:
    # Attempt to find the .env file, but don't raise an error if it's not found
    dotenv_path = find_dotenv(raise_error_if_not_found=False)
    logger.info(f".env file {dotenv_path}")

    if dotenv_path:
        load_dotenv(dotenv_path, verbose=True)
    else:
        logger.warning(".env file not found")


def _read_env_or_raise(key: str) -> str:
    if key in os.environ:
        return os.environ[key]
    else:
        raise ValueError(f"missing env key {key}")


load_env()
EUGENE_TENANT_ID = _read_env_or_raise("EUGENE_TENANT_ID")
EUGENE_CLIENT_ID = _read_env_or_raise("EUGENE_CLIENT_ID")
EUGENE_CLIENT_SECRET = _read_env_or_raise("EUGENE_CLIENT_SECRET")
EUGENE_ISSUER = _read_env_or_raise("EUGENE_ISSUER")
EUGENE_AUDIENCE = _read_env_or_raise("EUGENE_AUDIENCE")
EUGENE_API_BASE = _read_env_or_raise("EUGENE_API_BASE")


def eugene_jwt_verifier() -> JWTVerifier:
    return _generate_jwt_verifier(
        secret_key=EUGENE_CLIENT_SECRET, iss=EUGENE_ISSUER, aud=EUGENE_AUDIENCE
    )
