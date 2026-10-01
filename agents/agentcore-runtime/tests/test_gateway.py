from __future__ import annotations

import httpx
import pytest

from supervisor_agent.gateway import (
    EugeneAgentGateway,
    EugeneAgentGatewayError,
    build_eugene_request,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_forwards_eugene_payload_and_returns_response_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EUGENE_AGENT_AUTH_TOKEN", "service-token")
    expected = {
        "prompt": "Find trial evidence",
        "conversation_id": "9951c5a8-585e-40ac-9f57-c09a369539ec",
        "include_tools": ["all_sources"],
    }
    upstream = {
        "prompt": expected["prompt"],
        "message": "A sourced answer",
        "conversation_id": expected["conversation_id"],
        "is_complete": True,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://eugene-agent/query"
        assert request.headers["authorization"] == "Bearer service-token"
        assert request.read() == httpx.Request(
            "POST", "http://eugene-agent/query", json=expected
        ).read()
        return httpx.Response(200, json=upstream)

    client = _client(handler)
    try:
        result = EugeneAgentGateway(
            "http://eugene-agent/query", client=client
        ).forward(expected)
    finally:
        client.close()

    assert result == upstream


def test_caller_bearer_token_takes_precedence_over_service_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EUGENE_AGENT_AUTH_TOKEN", "service-token")
    observed: list[str] = []
    client = _client(
        lambda request: (
            observed.append(request.headers["authorization"])
            or httpx.Response(200, json={"ok": True})
        )
    )
    try:
        result = EugeneAgentGateway(
            "http://eugene-agent/query", client=client
        ).forward(
            {"prompt": "hello"},
            context={"request_headers": {"Authorization": "Bearer caller-token"}},
        )
    finally:
        client.close()

    assert observed == ["Bearer caller-token"]
    assert result == {"ok": True}


def test_session_id_maps_to_a_stable_eugene_conversation_uuid() -> None:
    first = build_eugene_request({"prompt": "hello", "session_id": "session-1"})
    second = build_eugene_request({"prompt": "again", "session_id": "session-1"})

    assert first["conversation_id"] == second["conversation_id"]
    assert len(first["conversation_id"]) == 36


def test_auth_token_is_never_read_from_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EUGENE_AGENT_AUTH_TOKEN", raising=False)
    client = _client(lambda request: httpx.Response(200, json={"ok": True}))
    try:
        with pytest.raises(EugeneAgentGatewayError, match="No caller bearer token"):
            EugeneAgentGateway(
                "http://eugene-agent/query", client=client
            ).forward({"prompt": "hello", "access_token": "untrusted-token"})
    finally:
        client.close()


def test_upstream_error_does_not_leak_response_body() -> None:
    client = _client(
        lambda request: httpx.Response(401, json={"detail": "sensitive upstream data"})
    )
    try:
        with pytest.raises(EugeneAgentGatewayError) as exc_info:
            EugeneAgentGateway(
                "http://eugene-agent/query", client=client
            ).forward(
                {"prompt": "hello"},
                context={"headers": {"authorization": "Bearer test-token"}},
            )
    finally:
        client.close()

    assert exc_info.value.status_code == 401
    assert "sensitive upstream data" not in str(exc_info.value)


def test_invalid_request_is_rejected_before_forwarding() -> None:
    with pytest.raises(ValueError, match="prompt must be"):
        build_eugene_request({"prompt": "  "})
    with pytest.raises(ValueError, match="include_tools"):
        build_eugene_request({"prompt": "hello", "include_tools": "pubmed"})