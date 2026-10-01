#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\agents\eugene-agent-ws\src\query\infra\llm
import logging
import os
from typing import Any, AsyncGenerator, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from strands.models.model import Model
from strands.models.openai import OpenAIModel
from strands.types.content import Messages, SystemContentBlock
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LlmFactory:

    @staticmethod
    def bedrock_model(
        model_id: str = "amazon.nova-lite-v1:0",
        max_tokens: int = 4096,
        temp: float = 0.7,
    ):
        """AWS Bedrock model — reached privately via the bedrock-runtime VPC
        endpoint, authenticated by the ECS task role (no API key needed).

        model_id examples:
          amazon.nova-lite-v1:0, amazon.nova-pro-v1:0
          us.anthropic.claude-3-5-sonnet-20241022-v2:0  (cross-region profile)
        Region comes from the default boto3 session (AWS_REGION).
        """
        from strands.models import BedrockModel

        logger.info(f"using bedrock model={model_id}")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        return BedrockModel(
            model_id=model_id,
            region_name=region,
            temperature=temp,
            max_tokens=max_tokens,
        )

    @staticmethod
    def fallback_model(primary: Model, fallback: Model, primary_name: str, fallback_name: str) -> Model:
        return _FallbackModel(primary, fallback, primary_name, fallback_name)

    @staticmethod
    def openai_model(
        openai_key: str,
        model_id: str = "gpt-4.1-mini",
        max_completion_tokens: int = 4096,
        temp: float = 0.7,
        top_p: float = 1.0,
    ) -> OpenAIModel:
        """
        models:
        gpt-4.1, gpt-4o, gpt-4o-mini, gpt-4.1-mini, gpt-3.5-turbo
        """

        logger.info("using OpenAI model=%s", model_id)
        model = OpenAIModel(
            client_args={
                "api_key": openai_key,
                "max_retries": 3,
                "timeout": 60.0,
            },
            model_id=model_id,
            params={
                "max_completion_tokens": max_completion_tokens,
                "temperature": temp,
                "top_p": top_p,
            },
        )
        return model

    @staticmethod
    def anthropic_model(
        anthropic_key: str,
        model_id: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024 * 16,
        temp: float = 0.7,
    ):
        """
        models:
        claude-sonnet-4-20250514
        claude-haiku-4-5-20251001
        claude-opus-4-20250514
        """
        from strands.models.anthropic import AnthropicModel

        logger.info("using Anthropic model=%s", model_id)
        model = AnthropicModel(
            client_args={
                "api_key": anthropic_key,
                "timeout": 60.0,
                "max_retries": 3,
            },
            model_id=model_id,
            max_tokens=max_tokens,
            params={
                "temperature": temp,
            },
        )
        return model


class _FallbackModel(Model):
    """Retry a failed provider with a configured secondary, without leaking partial output."""

    def __init__(self, primary: Model, fallback: Model, primary_name: str, fallback_name: str) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name

    def update_config(self, **model_config: Any) -> None:
        self.primary.update_config(**model_config)
        self.fallback.update_config(**model_config)

    def get_config(self) -> Any:
        return self.primary.get_config()

    async def stream(
        self,
        messages: Messages,
        tool_specs: Optional[list[ToolSpec]] = None,
        system_prompt: Optional[str] = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        try:
            events = [
                event
                async for event in self.primary.stream(
                    messages,
                    tool_specs,
                    system_prompt,
                    tool_choice=tool_choice,
                    system_prompt_content=system_prompt_content,
                    **kwargs,
                )
            ]
        except Exception as exc:
            logger.warning(
                "LLM primary provider failed; retrying with fallback provider=%s exception=%s",
                self.fallback_name,
                type(exc).__name__,
            )
            events = [
                event
                async for event in self.fallback.stream(
                    messages,
                    tool_specs,
                    system_prompt,
                    tool_choice=tool_choice,
                    system_prompt_content=system_prompt_content,
                    **kwargs,
                )
            ]
        for event in events:
            yield event

    async def structured_output(
        self,
        output_model: Type[T],
        prompt: Messages,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Union[T, Any]], None]:
        try:
            events = [
                event
                async for event in self.primary.structured_output(
                    output_model, prompt, system_prompt, **kwargs
                )
            ]
        except Exception as exc:
            logger.warning(
                "LLM primary provider failed; retrying structured output with fallback provider=%s exception=%s",
                self.fallback_name,
                type(exc).__name__,
            )
            events = [
                event
                async for event in self.fallback.structured_output(
                    output_model, prompt, system_prompt, **kwargs
                )
            ]
        for event in events:
            yield event

