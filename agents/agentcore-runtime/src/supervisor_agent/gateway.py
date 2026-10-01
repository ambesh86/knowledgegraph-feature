from __future__ import annotations

import os
import logging
from collections.abc import Mapping
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx

logger = logging.getLogger(__name__)


class EugeneAgentGatewayError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _context_value(context: Any, key: str) -> Any:
    if isinstance(context, Mapping):
        return context.get(key)
    return getattr(context, key, None)


def _caller_bearer_token(context: Any) -> str | None:
    for container_name in ("request_headers", "headers"):
        headers = _context_value(context, container_name)
        if not isinstance(headers, Mapping):
            continue
        authorization = next(
            (
                str(value)
                for name, value in headers.items()
                if str(name).lower() == "authorization"
            ),
            "",
        )
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.lower() == "bearer" and token.strip():
            return token.strip()
    return None


def _conversation_id(payload: Mapping[str, Any], context: Any) -> str:
    supplied = payload.get("conversation_id")
    if supplied:
        if not isinstance(supplied, str):
            raise ValueError("conversation_id must be a UUID string")
        try:
            return str(UUID(supplied))
        except ValueError as exc:
            raise ValueError("conversation_id must be a UUID string") from exc

    session_id = payload.get("session_id") or _context_value(context, "session_id")
    if session_id:
        return str(uuid5(NAMESPACE_URL, f"eugene-agentcore-session:{session_id}"))
    return str(uuid4())


def build_eugene_request(
    payload: Mapping[str, Any], context: Any = None
) -> dict[str, Any]:
    """Build only the fields accepted by the existing Eugene query endpoint."""
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    request: dict[str, Any] = {
        "prompt": prompt,
        "conversation_id": _conversation_id(payload, context),
    }
    if "include_tools" in payload:
        sources = payload["include_tools"]
        if sources is not None and (
            not isinstance(sources, list)
            or not all(isinstance(source, str) for source in sources)
        ):
            raise ValueError("include_tools must be a list of source names or null")
        request["include_tools"] = sources
    return request


class EugeneAgentGateway:
    """Forwards one AgentCore invocation to Eugene's existing /query endpoint."""

    def __init__(self, endpoint: str, client: httpx.Client) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("EUGENE_AGENT_QUERY_URL must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise ValueError("EUGENE_AGENT_QUERY_URL must not include query or fragment")
        self.endpoint = endpoint
        self.client = client

    def forward(
        self,
        payload: Mapping[str, Any],
        context: Any = None,
        request_id: str = "unavailable",
    ) -> dict[str, Any]:
        request_body = build_eugene_request(payload, context)
        token = _caller_bearer_token(context) or os.environ.get(
            "EUGENE_AGENT_AUTH_TOKEN", ""
        ).strip()
        if not token:
            raise EugeneAgentGatewayError(
                "No caller bearer token or runtime-managed Eugene service token is configured."
            )

        started_at = perf_counter()
        logger.info(
            "eugene.http.start request_id=%s host=%s",
            request_id,
            urlsplit(self.endpoint).hostname,
        )
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Request-ID": request_id,
        }
        try:
            response = self.client.post(
                self.endpoint,
                json=request_body,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "eugene.http.timeout request_id=%s exception=%s elapsed_ms=%.0f",
                request_id,
                type(exc).__name__,
                (perf_counter() - started_at) * 1000,
            )
            raise EugeneAgentGatewayError(
                f"The Eugene Agent request timed out ({type(exc).__name__})."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "eugene.http.transport_error request_id=%s exception=%s elapsed_ms=%.0f",
                request_id,
                type(exc).__name__,
                (perf_counter() - started_at) * 1000,
            )
            raise EugeneAgentGatewayError(
                f"The Eugene Agent endpoint could not be reached ({type(exc).__name__})."
            ) from exc

        logger.info(
            "eugene.http.response request_id=%s status=%s elapsed_ms=%.0f",
            request_id,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )
        if not response.is_success:
            raise EugeneAgentGatewayError(
                f"The Eugene Agent returned HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        try:
            result = response.json()
        except ValueError as exc:
            raise EugeneAgentGatewayError(
                "The Eugene Agent returned an invalid JSON response.",
                status_code=502,
            ) from exc
        if not isinstance(result, dict):
            raise EugeneAgentGatewayError(
                "The Eugene Agent response must be a JSON object.", status_code=502
            )
        return result