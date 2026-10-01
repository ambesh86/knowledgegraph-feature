from langchain_aws import BedrockLLM
from langchain_core.language_models import BaseLLM
from langchain_ollama import OllamaLLM
from langchain_openai import OpenAI


class LlmFactory:
    _LOCAL_INSTANCE = None
    _BEDROCK_INSTANCE = None
    _OPENAI_INSTANCE = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    @classmethod
    def instance(cls) -> BaseLLM:
        return LlmFactory.openai_instance()

    @classmethod
    def local_instance(
        cls, model: str = "llama3.1", base_url: str = "http://localhost:11434"
    ) -> BaseLLM:
        """
        Run ollama pull <model name>

        Where model names could include "mistral, llama3.1, llama3.1:70b
        """
        if cls._LOCAL_INSTANCE is None:
            cls._LOCAL_INSTANCE = OllamaLLM(model=model, base_url=base_url)
        return cls._LOCAL_INSTANCE

    @classmethod
    def bedrock_instance(
        cls, provider: str = "meta", model_id: str = "meta.llama3-1-70b-instruct-v1:0"
    ) -> BaseLLM:
        """
        Where provider are listed here;
        https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
        and model ids are listed here;
        https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html

        meta.llama3-8b-instruct-v1:0
        meta.llama3-70b-instruct-v1:0
        anthropic.claude-3-5-sonnet-20240620-v1:0
        """
        if cls._BEDROCK_INSTANCE is None:
            cls._BEDROCK_INSTANCE = BedrockLLM(
                provider=provider,
                model_id=model_id,  # ARN like 'arn:aws:bedrock:...' obtained via provisioning the custom model
                model_kwargs={"temperature": 0.1},
                streaming=True,
            )
        return cls._BEDROCK_INSTANCE

    @classmethod
    def openai_instance(cls, model_name: str = "chatgpt-4o-latest") -> BaseLLM:
        if cls._OPENAI_INSTANCE is None:
            cls._OPENAI_INSTANCE = OpenAI(
                model=model_name,
                temperature=0.1,
                max_retries=2,
            )
        return cls._OPENAI_INSTANCE
