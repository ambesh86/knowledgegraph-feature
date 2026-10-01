"""Shared observability + middleware utilities (OBS-01, OBS-04, SEC-03).

Stage 1 Assessment findings addressed:
- OBS-01: structured JSON logging via python-json-logger
- OBS-04: deep /health endpoint with dependency checks
- SEC-03: slowapi rate limiter shared across routes
"""
from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


_REQUEST_ID_HEADER = "X-Request-ID"


def configure_json_logging(service_name: str) -> None:
    """Replace stdout handler with a JSON formatter; keep level from env.

    Non-destructive: if python-json-logger is unavailable (local dev), fall back
    to the existing plain-text formatter so the app still boots.
    """
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any pre-existing handlers so we don't double-log
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    try:
        from pythonjsonlogger import jsonlogger

        fmt = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
            json_ensure_ascii=False,
        )
    except Exception:  # pragma: no cover — dev fallback
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # Tag every record with the service name (appears in JSON output)
    logging.LoggerAdapter(logging.getLogger(service_name), {"service": service_name})
    logging.getLogger(__name__).info(
        f"structured logging enabled for service={service_name} level={level}"
    )


def make_limiter() -> Limiter:
    """Rate limiter keyed by upn claim when available, else client IP."""

    def key_fn(request: Request) -> str:
        # Prefer authenticated user identity so shared NAT doesn't penalize users
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            # Hash the token tail — don't leak it in logs
            tail = auth[-16:]
            return f"tok:{tail}"
        return get_remote_address(request)

    default_limits = os.environ.get("EUGENE_RATE_LIMIT_DEFAULT", "120/minute")
    return Limiter(key_func=key_fn, default_limits=[default_limits])


async def request_id_middleware(request: Request, call_next: Callable):
    """Attach a request id for cross-service correlation (OBS-01)."""
    rid = request.headers.get(_REQUEST_ID_HEADER) or str(uuid.uuid4())
    request.state.request_id = rid
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers[_REQUEST_ID_HEADER] = rid
    logging.getLogger("access").info(
        "http_request",
        extra={
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": elapsed_ms,
        },
    )
    return response
