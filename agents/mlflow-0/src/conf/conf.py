import logging
import os

import mlflow

from agent.organization_agent import OrganizationAgent
from conf.env_loader import load_env

from strands.models import BedrockModel

logger = logging.getLogger(__name__)


load_env()


def organization_agent() -> OrganizationAgent:
    prompt = mlflow.genai.load_prompt("prompts:/organization_resolution_prompt@latest")
    return OrganizationAgent(agent_model=agent_model(), prompt=prompt)


def agent_model() -> BedrockModel:
    logger.info(f"creating agent model: {model_id()}")
    # https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock#global-vs-regional-endpoints
    is_global = is_global_model_routing
    routing = "global" if is_global else "us"
    return BedrockModel(
        model_id=f"{routing}.{model_id()}",
        temperature=model_temp(),
        max_tokens=model_max_tokens(),
    )


def model_id() -> str:
    return _env_value("MODEL_ID")


def model_temp() -> float:
    return float(_env_value("MODEL_TEMP"))


def is_global_model_routing() -> bool:
    return _str_to_bool(_env_value("IS_GLOBAL_MODEL_ROUTING"))


def model_max_tokens() -> int:
    return int(_env_value("MODEL_MAX_TOKENS"))


def _env_value(key: str) -> str:
    if key in os.environ:
        return os.environ[key]
    else:
        raise ValueError(f"Please supply an environment value for {key}")


def _str_to_bool(value: str) -> bool:
    if value.lower() in ("true", "yes", "1", "t", "y"):
        return True
    elif value.lower() in ("false", "no", "0", "f", "n"):
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}")
