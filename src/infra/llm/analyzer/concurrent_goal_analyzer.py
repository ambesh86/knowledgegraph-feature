import concurrent.futures
import logging

from langchain_core.language_models import BaseChatModel

from infra.llm.prompt.generate import of_prompt
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse
from infra.llm.prompt.goal_prompt_title import GoalPromptTitle
from organization.infra.llm.prompt.generate import PROMPT_GOAL, PROMPT_TITLE


logger = logging.getLogger(__name__)


class ConcurrentGoalAnalyzer:
    """
    Class main purpose is to stream and collect many llm prompt responses in parallel across threads
    """

    def __init__(
        self,
        model: BaseChatModel,
        input_params: dict[str, str],
        max_workers: int = 4,
    ):
        self.model = model
        self.input_params = input_params
        self.goal_based_prompt = input_params[PROMPT_GOAL]
        self.max_workers = max_workers

    def analyze_data(
        self, data: set[str], param_key: str = "data"
    ) -> list[GoalPromptResponse]:
        return self._analyzed_all_tasks(
            params=self._generate_tasks(self.input_params, data, param_key)
        )

    def _analyzed_all_tasks(
        self, params: list[dict[str, str]]
    ) -> list[GoalPromptResponse]:
        """
        analyze data with the given goals
        thread workers split across given data. e.g. one llm call per element in data list
        """
        responses = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures_to_responses = {
                executor.submit(self._analyze_task, input_param): input_param
                for input_param in params
            }
            logger.info(
                f"created {len(futures_to_responses)} futures for {self.max_workers} max workers"
            )
            responses = self._collect_responses(futures_to_responses)

        return responses

    def _analyze_task(self, input_params: dict[str, str]) -> GoalPromptResponse:
        prompt = of_prompt(self.goal_based_prompt)
        chain = prompt | self.model
        response = chain.stream(input_params)
        output = []
        logger.debug(
            f"listening for streaming response to goal: {input_params[PROMPT_GOAL]}"
        )
        for chunk in response:
            output.append(chunk.content)
        return GoalPromptResponse(
            GoalPromptTitle[input_params[PROMPT_TITLE]], input_params, "".join(output)
        )

    def _generate_tasks(
        self, input_params: dict[str, str], data: set[str], param_key: str
    ) -> list[dict[str, str]]:
        all_params = []
        for el in data:
            param = input_params.copy()
            param[param_key] = el
            all_params.append(param)

        return all_params

    def _collect_responses(
        self,
        futures_to_responses: dict[
            concurrent.futures.Future[GoalPromptResponse], dict[str, str]
        ],
    ) -> list[GoalPromptResponse]:
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
