import logging

from langchain_core.language_models import BaseLLM
from infra.llm.prompt.generate import (
    generate_business_value_input_params,
    generate_enrich_suggestions_input_params,
    generate_industry_input_params,
    generate_monetary_value_input_params,
    generate_prompt,
    generate_questions_input_params,
)

logger = logging.getLogger(__name__)


class SimpleDocumentAnalyzer:
    """
    Class main purpose is to execute several prompts in a batch
    This may be slow and hit the context window limit
    """

    def __init__(
        self, model: BaseLLM, input_params: list[dict[str, str]], max_workers: int = 4
    ):
        self.model = model
        self.max_workers = max_workers
        self.input_params = [
            generate_industry_input_params(""),
            generate_business_value_input_params(""),
            generate_monetary_value_input_params(""),
            generate_questions_input_params(""),
            generate_enrich_suggestions_input_params(""),
        ]

    def analyze_document(self, pages: list[str]) -> list[str]:
        logger.info(f"analyzing {len(pages)} page(s)")
        all_pages = "\n".join(pages)
        logger.debug(all_pages)
        prompt = generate_prompt()
        logger.debug(f"prompt = {prompt}")
        chain = prompt | self.model
        params = self.apply_contents(self.input_params, all_pages)
        response = chain.batch(params)
        return response

    def apply_contents(
        self, input_params: list[dict[str, str]], contents: str
    ) -> list[dict[str, str]]:
        for input_param in input_params:
            input_param["document"] = contents

        return input_params
