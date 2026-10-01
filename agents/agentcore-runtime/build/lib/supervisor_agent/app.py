from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp

from .shared import configure_shared_agent_imports

configure_shared_agent_imports()

from .workflow import invoke_supervisor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()


def _request_token(payload: dict[str, Any], context: Any) -> str | None:
    headers = getattr(context, "request_headers", None)
    if isinstance(context, dict):
        headers = context.get("request_headers", headers)
    if isinstance(headers, dict):
        authorization = headers.get("authorization") or headers.get("Authorization")
        if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
    return payload.get("access_token")


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any) -> dict[str, Any]:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("payload.prompt must be a non-empty string")
    requested_sources = payload.get("include_tools", payload.get("sources", []))
    if isinstance(requested_sources, str):
        requested_sources = [requested_sources]
    if not isinstance(requested_sources, list) or not all(
        isinstance(source, str) for source in requested_sources
    ):
        raise ValueError("include_tools/sources must be a list of source names")

    conversation_id = payload.get("conversation_id") or str(uuid4())
    logger.info("AgentCore invocation started: %s", conversation_id)
    result = invoke_supervisor(
        prompt=prompt,
        requested_sources=requested_sources,
        access_token=_request_token(payload, context),
        conversation_id=conversation_id,
    )
    return result


if __name__ == "__main__":
    app.run()