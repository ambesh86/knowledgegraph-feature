from __future__ import annotations

import logging
import os
from time import perf_counter
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp
import httpx

from .gateway import EugeneAgentGateway, EugeneAgentGatewayError

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
    endpoint = os.environ.get("EUGENE_AGENT_QUERY_URL", "").strip()
    if not endpoint:
        raise EugeneAgentGatewayError("EUGENE_AGENT_QUERY_URL is not configured.")
    timeout_seconds = _timeout_seconds()
    request_id = _request_id(context)
    started_at = perf_counter()
    logger.info("agentcore.invoke.start request_id=%s", request_id)

    timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 10.0))
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        gateway = EugeneAgentGateway(endpoint=endpoint, client=client)
        try:
            result = gateway.forward(payload, context=context, request_id=request_id)
            logger.info(
                "agentcore.invoke.complete request_id=%s elapsed_ms=%.0f",
                request_id,
                (perf_counter() - started_at) * 1000,
            )
            return result
        except EugeneAgentGatewayError as exc:
            logger.error(
                "agentcore.invoke.failed request_id=%s status=%s cause_type=%s elapsed_ms=%.0f reason=%s",
                request_id,
                exc.status_code,
                type(exc.__cause__).__name__ if exc.__cause__ else "none",
                (perf_counter() - started_at) * 1000,
                exc,
            )
            raise


def _timeout_seconds() -> float:
    try:
        timeout_seconds = float(os.environ.get("EUGENE_AGENT_TIMEOUT_SECONDS", "120"))
    except ValueError as exc:
        raise EugeneAgentGatewayError(
            "EUGENE_AGENT_TIMEOUT_SECONDS must be a positive number."
        ) from exc
    if timeout_seconds <= 0:
        raise EugeneAgentGatewayError(
            "EUGENE_AGENT_TIMEOUT_SECONDS must be a positive number."
        )
    return timeout_seconds


def _request_id(context: Any) -> str:
    if isinstance(context, dict):
        value = context.get("request_id")
    else:
        value = getattr(context, "request_id", None)
    return str(value)[:128] if value else "unavailable"


if __name__ == "__main__":
    if not os.environ.get("EUGENE_AGENT_QUERY_URL", "").strip():
        logger.error("EUGENE_AGENT_QUERY_URL is required to start the gateway.")
        raise SystemExit(2)
    try:
        _timeout_seconds()
    except EugeneAgentGatewayError as exc:
        logger.error("Invalid runtime configuration: %s", exc)
        raise SystemExit(2) from exc
    logger.info("Starting AgentCore local server on port 8080.")
    app.run(port=8080, log_level="info", access_log=True)