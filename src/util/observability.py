"""Shared observability + middleware utilities (OBS-01, OBS-04, SEC-03).

Mirror of agents/eugene-agent-ws/src/util/observability.py — the two services
ship independently so we duplicate rather than share via a package.
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
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

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
    except Exception:  # pragma: no cover
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    root.addHandler(handler)
    logging.getLogger(__name__).info(
        f"structured logging enabled for service={service_name} level={level}"
    )


def make_limiter() -> Limiter:
    def key_fn(request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return f"tok:{auth[-16:]}"
        return get_remote_address(request)

    default_limits = os.environ.get("EUGENE_RATE_LIMIT_DEFAULT", "300/minute")
    return Limiter(key_func=key_fn, default_limits=[default_limits])


async def request_id_middleware(request: Request, call_next: Callable):
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
