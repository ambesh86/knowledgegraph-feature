from langchain_aws import ChatBedrock
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


class LlmChatFactory:
    _LOCAL_INSTANCE = None
    _BEDROCK_INSTANCE = None
    _OPENAI_INSTANCE = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    @classmethod
    def instance(cls) -> BaseChatModel:
        return LlmChatFactory.bedrock_instance()

    @classmethod
    def local_instance(
        cls, model: str = "llama3.1", base_url: str = "http://localhost:11434"
    ) -> BaseChatModel:
        """
        Run ollama pull <model name>

        Where model names could include "mistral, llama3.1, llama3.1:70b
        """
        if cls._LOCAL_INSTANCE is None:
            cls._LOCAL_INSTANCE = ChatOllama(
                model=model, temperature=0.9, base_url=base_url
            )
        return cls._LOCAL_INSTANCE

    @classmethod
    def bedrock_instance(
        cls, provider: str = "meta", model: str = "meta.llama3-70b-instruct-v1:0"
    ) -> BaseChatModel:
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
            # bedrock_client = boto3.client(
            #     service_name="bedrock-runtime", region_name="us-east-1"
            # )
            model_args = {
                "temperature": 0.8,
            }
            # model_args = {
            #     "temperature": 0.1,
            #     "top_k": 250,
            #     "top_p": 1,
            #     "stop_sequences": ["\n\nHuman"],
            # }
            cls._BEDROCK_INSTANCE = ChatBedrock(
                provider=provider,
                model_id=model,  # ARN like 'arn:aws:bedrock:...' obtained via provisioning the custom model
                model_kwargs=model_args,
                streaming=True,
            )
        return cls._BEDROCK_INSTANCE

    @classmethod
    def openai_instance(cls, model: str = "chatgpt-4o-latest") -> BaseChatModel:
        if cls._OPENAI_INSTANCE is None:
            cls._OPENAI_INSTANCE = ChatOpenAI(
                model=model,
                temperature=1,
                max_retries=2,
                streaming=False,
            )
        return cls._OPENAI_INSTANCE
