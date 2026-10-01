#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\agents\eugene-agent-ws\tests
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from query.conf import conf
from query.infra.llm.llm_factory import LlmFactory, _FallbackModel


class StubModel:
    def __init__(self, events: list[dict[str, Any]], fail_after: int | None = None) -> None:
        self.events = events
        self.fail_after = fail_after

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> dict[str, Any]:
        return {}

    async def stream(self, *args: Any, **kwargs: Any):
        for index, event in enumerate(self.events):
            yield event
            if self.fail_after == index + 1:
                raise RuntimeError("provider failed mid-stream")

    async def structured_output(self, *args: Any, **kwargs: Any):
        for event in self.events:
            yield event


def test_bedrock_nova_is_the_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls: list[str] = []
    monkeypatch.setattr(
        LlmFactory,
        "bedrock_model",
        lambda **kwargs: calls.append(kwargs["model_id"]) or "bedrock-model",
    )

    assert conf.llm_provider() == "bedrock"
    assert conf.llm_model() == "bedrock-model"
    assert calls == ["amazon.nova-lite-v1:0"]


def test_fallback_is_created_only_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(LlmFactory, "bedrock_model", lambda **kwargs: "primary")
    monkeypatch.setattr(
        LlmFactory,
        "openai_model",
        lambda **kwargs: "fallback",
    )
    monkeypatch.setattr(
        LlmFactory,
        "fallback_model",
        lambda primary, fallback, primary_name, fallback_name: (
            primary,
            fallback,
            primary_name,
            fallback_name,
        ),
    )

    assert conf.llm_model() == ("primary", "fallback", "bedrock", "openai")


def test_unknown_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="LLM_PROVIDER must be"):
        conf.llm_provider()


def test_partial_primary_stream_is_discarded_before_fallback() -> None:
    primary = StubModel([{"provider": "primary-partial"}], fail_after=1)
    fallback = StubModel([{"provider": "fallback-complete"}])
    model = _FallbackModel(primary, fallback, "bedrock", "openai")

    async def collect() -> list[dict[str, Any]]:
        return [event async for event in model.stream([])]

    assert asyncio.run(collect()) == [{"provider": "fallback-complete"}]
