"""Structured logging and request correlation.

`python-json-logger` was already a dependency and was never wired up, so the service
emitted plain text. That is fine when you are reading `docker logs` by eye and useless
the moment logs are shipped anywhere that queries them — you cannot filter a nightly
scan's failures by area, or count 429s by source, without parsing prose.

Every line is now JSON with stable field names. `SCOUT_LOG_FORMAT=text` restores the
human-readable form for local work, because JSON is genuinely worse to read in a
terminal and forcing it everywhere just means people stop reading logs.

Each HTTP request carries a correlation id, taken from an inbound `X-Request-Id` when
a proxy supplies one and generated otherwise, echoed on the response and attached to
every log line emitted while handling that request. Without it, concurrent scans and
page loads interleave into a single stream that cannot be untangled after the fact.
"""
from __future__ import annotations

import contextvars
import logging
import os
import sys
import time
import uuid
from typing import Any

from pythonjsonlogger import jsonlogger

# Set per request; read by the log filter. A ContextVar rather than a thread-local
# because the request path is async and hops threads via run_in_threadpool.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class ScoutJsonFormatter(jsonlogger.JsonFormatter):
    """Adds the fields an operator actually filters on."""

    def add_fields(
        self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = "eugene-scout"
        log_record.setdefault("request_id", getattr(record, "request_id", "-"))
        # Drop the duplicate that JsonFormatter carries alongside `timestamp`.
        log_record.pop("asctime", None)


def configure() -> None:
    """Install the handler. Idempotent — safe if uvicorn reloads the module."""
    level = os.environ.get("SCOUT_LOG_LEVEL", "INFO").upper()
    use_json = os.environ.get("SCOUT_LOG_FORMAT", "json").lower() != "text"

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if use_json:
        handler.setFormatter(
            ScoutJsonFormatter(
                "%(timestamp)s %(level)s %(logger)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn installs its own handlers; let them propagate to ours instead so every
    # line in the container has one shape.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    # Third-party chatter at INFO drowns the signal. botocore in particular logs
    # every request parameter.
    for noisy in ("botocore", "boto3", "urllib3", "s3transfer", "apscheduler.executors", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def request_context_middleware(request, call_next):  # noqa: ANN001, ANN201
    """Attach a correlation id and log one structured line per request."""
    incoming = request.headers.get("x-request-id", "").strip()
    rid = incoming or uuid.uuid4().hex[:12]
    token = request_id_var.set(rid)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logging.getLogger("scout.http").exception(
            "request failed",
            extra={"method": request.method, "path": request.url.path},
        )
        request_id_var.reset(token)
        raise

    duration_ms = int((time.monotonic() - started) * 1000)
    response.headers["X-Request-Id"] = rid

    # /health is polled every 30s by Docker; logging it buries everything else.
    if request.url.path != "/health":
        logging.getLogger("scout.http").info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
    request_id_var.reset(token)
    return response
