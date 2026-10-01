import concurrent.futures
import logging

from langchain_core.language_models import BaseChatModel
from infra.llm.prompt.generate import generate_prompt
from infra.llm.prompt.prompt_response import PromptResponse

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """
    Class main purpose is to chain together the prompt and execute them in parallel across threads
    """

    def __init__(
        self,
        model: BaseChatModel,
        input_params: list[dict[str, str]],
        max_workers: int = 4,
    ):
        self.model = model
        self.max_workers = max_workers
        self.input_params = input_params

    def analyze_document_tasks(self, pages: list[str]) -> list[PromptResponse]:
        """
        thread workers split across prompts
        """
        all_pages = "\n".join(pages)
        params = self._apply_contents(self.input_params, all_pages)
        responses = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures_to_responses = {
                executor.submit(self._analyze_document_task, input_param): input_param
                for input_param in params
            }
            logger.info(
                f"created {len(futures_to_responses)} futures for {self.max_workers} max workers"
            )
            responses = self._collect_responses(futures_to_responses)

        return responses

    def analyze_document_pages(self, pages: list[str]) -> list[PromptResponse]:
        """
        thread workers split across pages
        """
        params = self._generate_page_tasks(self.input_params, pages)
        responses = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures_to_responses = {
                executor.submit(self._analyze_document_task, input_param): input_param
                for input_param in params
            }
            logger.info(
                f"created {len(futures_to_responses)} futures for {self.max_workers} max workers"
            )
            responses = self._collect_responses(futures_to_responses)

        return responses

    def _analyze_document_task(self, input_params: dict[str, str]) -> PromptResponse:
        prompt = generate_prompt()
        chain = prompt | self.model
        response = chain.stream(input_params)
        output = []
        # logger.debug(
        #     f"listening for streaming response to question: {input_params["question"]}"
        # )
        # chunks are coming over as words
        chunk_count = 0
        for chunk in response:
            chunk_count += 1
            if chunk_count % 100 == 0:
                logger.debug(f"chunk_count {chunk_count}")
                logger.debug(f"chunk={chunk.content}")
            output.append(chunk.content)
        return PromptResponse(
            input_params["title"], input_params["question"], "".join(output)
        )

    def _generate_page_tasks(
        self, input_params: list[dict[str, str]], pages: list[str]
    ) -> list[dict[str, str]]:
        all_input_params = []
        for input_param in input_params:
            for page in pages:
                param = input_param.copy()
                param["document"] = page
                all_input_params.append(param)

        return all_input_params

    def _apply_contents(
        self, input_params: list[dict[str, str]], contents: str
    ) -> list[dict[str, str]]:
        for input_param in input_params:
            input_param["document"] = contents

        return input_params

    def _collect_responses(
        self,
        futures_to_responses: dict[
            concurrent.futures.Future[PromptResponse], dict[str, str]
        ],
    ):
        responses = []
        for future in concurrent.futures.as_completed(futures_to_responses):
            try:
                response = future.result()
            except Exception as exc:
                input_param = futures_to_responses[future]
                logger.warning(f"{input_param} generated an exception: {exc}")
            else:
                responses.append(response)

        return responses
