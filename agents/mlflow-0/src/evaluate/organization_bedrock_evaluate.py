import logging

import mlflow

from mlflow.genai.datasets.evaluation_dataset import EvaluationDataset

from conf.conf import organization_agent
from evaluate.evaluate import evaluate_organization_resolution_prompt
from infra.llm.llm_chat_factory import LlmChatFactory

logger = logging.getLogger(__name__)

agent = organization_agent()


def bedrock_evaluate_organization_resolution_prompt(dataset: EvaluationDataset):
    evaluate_organization_resolution_prompt(dataset, agent_predict_fn)


@mlflow.trace
def agent_predict_fn(organization_name: str) -> str:
    logger.info(f"agent predict organization_name: {organization_name}")
    response = agent.resolve_organization(organization_name)
    return response.to_dict()["message"]["content"][0]["text"]


def _model():
    model_name = "anthropic.claude-sonnet-4-5-20250929-v1:0"
    # https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock#global-vs-regional-endpoints
    is_global = True
    routing = "global" if is_global else "us"
    model_id = f"{routing}.{model_name}"
    logger.info(f"{model_id}")
    model = LlmChatFactory.bedrock_instance(model=model_id)
    logger.info(f"model test {model}")
    return model
