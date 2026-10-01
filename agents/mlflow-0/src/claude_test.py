import logging

from langchain_core.language_models import LanguageModelInput
from infra.llm.llm_chat_factory import LlmChatFactory

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    # model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
    logger.info(f"model test {model_id}")
    # https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock#global-vs-regional-endpoints
    is_global = True
    routing = "global" if is_global else "us"
    model = LlmChatFactory.bedrock_instance(model=f"{routing}.{model_id}")
    questions = [
        "Why do parrots have colorful feathers?",
        "How do airplanes fly?",
        "What is quantum computing?",
    ]
    responses = model.batch(inputs=_as_msgs(questions))
    for response in responses:
        logger.info("---")
        logger.info(response.content)

    exit(0)


def _as_msgs(arr: list[str]) -> list[LanguageModelInput]:
    msgs = []
    for msg in arr:
        msgs.append(msg)
    return msgs


if __name__ == "__main__":
    main()
