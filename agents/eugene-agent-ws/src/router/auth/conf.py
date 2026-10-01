import os

from fastapi.security import HTTPBearer


SECURITY = HTTPBearer(description="Paste a Eugene API access token here")


def environment() -> str | None:
    key = "ENVIRONMENT"
    return os.environ[key] if key in os.environ else None


def eugene_client_id() -> str:
    return _env_value("EUGENE_CLIENT_ID")


def eugene_client_secret() -> str:
    return _env_value("EUGENE_CLIENT_SECRET")


def eugene_tenant_id() -> str:
    return _env_value("EUGENE_TENANT_ID")


def eugene_agent_allowlist() -> set[str]:
    # Filter empties so an unset/blank env var yields an empty set
    # (which means "allow all" downstream), not {""}.
    raw = _env_value("EUGENE_AGENT_ALLOWLIST")
    return {p.strip() for p in raw.split("|") if p.strip()}


def _env_value(key: str) -> str:
    if key in os.environ:
        return os.environ[key]
    else:
        raise ValueError(f"Please supply an environment value for {key}")
