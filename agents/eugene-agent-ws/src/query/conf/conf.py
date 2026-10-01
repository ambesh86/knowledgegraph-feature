#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\agents\eugene-agent-ws\src\query\conf
import logging
import os

from query.agent.eugene_data_agent import EugeneDataAgent
from query.infra.llm.llm_factory import LlmFactory

logger = logging.getLogger(__name__)


def openai_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY")


def anthropic_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY")


def llm_provider() -> str:
    """Return the configured provider, defaulting to Bedrock."""
    provider = os.environ.get("LLM_PROVIDER", "bedrock").strip().lower()
    aliases = {
        "bedrock": "bedrock",
        "aws": "bedrock",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "openai": "openai",
        "gpt": "openai",
    }
    try:
        return aliases[provider]
    except KeyError as exc:
        raise ValueError(
            "LLM_PROVIDER must be one of: bedrock, anthropic, openai"
        ) from exc


def eugene_mcp_server_url() -> str:
    return os.environ["EUGENE_MCP_SERVER_URL"]


def llm_model():
    """Create the selected LLM model and optional runtime fallback."""
    provider = llm_provider()
    primary = _provider_model(provider)
    fallback_provider = os.environ.get("LLM_FALLBACK_PROVIDER", "").strip().lower()
    if not fallback_provider:
        return primary

    aliases = {"aws": "bedrock", "claude": "anthropic", "gpt": "openai"}
    fallback_provider = aliases.get(fallback_provider, fallback_provider)
    if fallback_provider not in {"bedrock", "anthropic", "openai"}:
        raise ValueError(
            "LLM_FALLBACK_PROVIDER must be one of: bedrock, anthropic, openai"
        )
    if fallback_provider == provider:
        raise ValueError("LLM_FALLBACK_PROVIDER must differ from LLM_PROVIDER")

    fallback = _provider_model(fallback_provider)
    logger.warning(
        "LLM fallback enabled: primary=%s fallback=%s; prompts may be sent to both providers",
        provider,
        fallback_provider,
    )
    return LlmFactory.fallback_model(primary, fallback, provider, fallback_provider)


def _provider_model(provider: str):
    if provider == "bedrock":
        model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
        logger.info("LLM provider: Bedrock (%s)", model_id)
        return LlmFactory.bedrock_model(model_id=model_id)
    if provider == "anthropic":
        key = anthropic_api_key()
        if not key or not key.strip():
            raise ValueError("ANTHROPIC_API_KEY is required when Anthropic is selected")
        model_id = os.environ.get("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514")
        logger.info("LLM provider: Anthropic (%s)", model_id)
        return LlmFactory.anthropic_model(anthropic_key=key, model_id=model_id)
    key = openai_api_key()
    if not key or not key.strip():
        raise ValueError("OPENAI_API_KEY is required when OpenAI is selected")
    model_id = os.environ.get("OPENAI_MODEL_ID", "gpt-4.1-mini")
    logger.info("LLM provider: OpenAI (%s)", model_id)
    return LlmFactory.openai_model(openai_key=key, model_id=model_id)


def eugene_data_agent() -> EugeneDataAgent:
    return EugeneDataAgent(
        eugene_mcp_server_url=eugene_mcp_server_url(), model=llm_model()
    )
