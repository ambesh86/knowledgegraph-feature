import os
from typing import Any

from fastapi.security import HTTPBearer
import requests

from msal import ConfidentialClientApplication


SECURITY = HTTPBearer(description="Paste a Eugene API access token here")


# entra id params
def msal_app(
    client_id: str, authority: str, client_secret: str
) -> ConfidentialClientApplication:
    # MSAL Confidential Client for server-side code
    msal_app = ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    return msal_app


def environment() -> str | None:
    key = "ENVIRONMENT"
    return os.environ[key] if key in os.environ else None


def client_id() -> str:
    return _env_value("ENTRA_CLIENT_ID")


def client_secret() -> str:
    return _env_value("ENTRA_CLIENT_SECRET")


def tenant_id() -> str:
    return _env_value("ENTRA_TENANT_ID")


def redirect_path() -> str:
    return _env_value("REDIRECT_PATH")


def redirect_uri() -> str:
    return _env_value("REDIRECT_URI")


def authority() -> str:
    return _env_value("ENTRA_AUTHORITY")


def scope() -> list[str]:
    scopes = _env_value("ENTRA_SCOPE")
    return scopes.split(",")


# JWKS / OIDC endpoints
def entra_openid_config(issuer: str) -> dict[str, Any]:
    openid_config_url = f"{issuer}/.well-known/openid-configuration"
    return requests.get(openid_config_url).json()


def entra_jwks_uri(issuer: str) -> str:
    config = entra_openid_config(issuer)
    return config["jwks_uri"]


# eugene token params
def eugene_client_id() -> str:
    return _env_value("EUGENE_CLIENT_ID")


def eugene_client_secret() -> str:
    return _env_value("EUGENE_CLIENT_SECRET")


def eugene_tenant_id() -> str:
    return _env_value("EUGENE_TENANT_ID")


def _env_value(key: str) -> str:
    if key in os.environ:
        return os.environ[key]
    else:
        raise ValueError(f"Please supply an environment value for {key}")
