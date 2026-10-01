"""API authentication.

The scanner had none. It was published on `0.0.0.0:18300`, which meant anyone who
could reach the host could read the entire intelligence corpus, rewrite the scoring
weights, dismiss signals, and trigger scans — the last of which burns a rate-limited
USPTO quota and hammers four public APIs that have asked us not to. Verified during a
production-readiness audit by changing `notify_min_score` from an unauthenticated
curl.

Two independent controls now close that, because either alone leaves a gap:

  1. **A bearer token on every endpoint except `/health`.** `/health` stays open
     because Docker's healthcheck calls it before any secret is available, and it
     exposes nothing beyond liveness and whether S3 is reachable.
  2. **The published port binds to 127.0.0.1 in docker-compose**, so the service is
     no longer reachable from the LAN at all. The UI talks to it over the compose
     network, where the port is not published.

When `SCOUT_API_TOKEN` is unset the service logs a prominent warning at startup and
reports `auth: "disabled"` from `/health` and `/status`, but keeps serving. That is a
deliberate choice rather than an oversight: failing closed would break every local
dev run and the entire test suite, and a service that refuses to boot without a secret
tends to acquire a hard-coded default secret. The shipped docker-compose sets a token,
so the deployed configuration is authenticated; the unset case is visible rather than
silent.

Comparison is constant-time. A token check that short-circuits on the first wrong byte
leaks the token's prefix to anyone willing to time the responses.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Endpoints reachable without a token. Deliberately minimal: liveness only.
#
# The docs routes are NOT listed, because FastAPI registers them outside the
# app-level dependency chain — listing them here would have no effect anyway. They
# are switched off entirely instead when auth is enabled; see `docs_enabled()`.
_OPEN_PATHS = frozenset({"/health"})


def docs_enabled() -> bool:
    """Whether to serve /docs, /redoc and /openapi.json.

    FastAPI mounts these bypassing app-level dependencies, so they cannot be
    protected by the token check — an authenticated deployment would still publish
    its full API surface to anyone who asked. That is not a data leak (the schema
    contains no signals) but it is free reconnaissance, so the schema is simply not
    served once a token is configured.

    `SCOUT_ENABLE_DOCS=true` puts them back for a deployment that wants the
    interactive docs behind its own network controls.
    """
    if os.environ.get("SCOUT_ENABLE_DOCS", "").lower() == "true":
        return True
    return not auth_enabled()


def configured_token() -> str | None:
    return os.environ.get("SCOUT_API_TOKEN", "").strip() or None


def auth_enabled() -> bool:
    return configured_token() is not None


def auth_status() -> str:
    """Surfaced in /health and /status so an unauthenticated deployment is visible
    to whoever is looking at it, not just to whoever reads the env file."""
    return "enabled" if auth_enabled() else "disabled"


def _present_token(request: Request) -> str | None:
    """Accept either `Authorization: Bearer <t>` or `X-Scout-Token: <t>`.

    Two forms because the Authorization header is the convention while a distinct
    header is easier to route through proxies that already use Authorization for
    something else.
    """
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.headers.get("x-scout-token", "").strip() or None


async def require_token(request: Request) -> None:
    """FastAPI dependency applied to every route except `_OPEN_PATHS`."""
    expected = configured_token()
    if expected is None:
        return  # unauthenticated mode; warned about at startup, reported by /health

    path = request.url.path.rstrip("/") or "/"
    if path in _OPEN_PATHS:
        return

    presented = _present_token(request)
    if presented is None or not hmac.compare_digest(presented, expected):
        # No detail about which part failed — a specific message ("token expired",
        # "wrong prefix") is a hint to whoever is guessing.
        logger.warning(f"rejected unauthenticated request to {path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def warn_if_unauthenticated() -> None:
    """Called once at startup."""
    if not auth_enabled():
        logger.warning(
            "SCOUT_API_TOKEN is not set — the API is UNAUTHENTICATED. Any caller that "
            "can reach this port may read all signals, rewrite scoring configuration "
            "and trigger scans. Set SCOUT_API_TOKEN before exposing this service."
        )
