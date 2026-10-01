import json
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from infra.llm.analyzer.concurrent_goal_analyzer import ConcurrentGoalAnalyzer
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse
from organization.infra.llm.prompt.generate import (
    generate_organization_acquisition_verification_input_params,
)
from organization.model.organization_resolution import OrganizationResolution
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
    PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY,
)

logger = logging.getLogger(__name__)


class ConcurrentOrganizationAcquisitionVerifier(ConcurrentGoalAnalyzer):
    """
    Analyze an organization name and verify the realtionships and acquisitions appear as a valid
    """

    def __init__(
        self,
        model: BaseChatModel,
        max_workers: int = 4,
    ):
        super().__init__(
            model=model,
            max_workers=max_workers,
            input_params=generate_organization_acquisition_verification_input_params(),
        )

    def analyze_data(
        self, data: set[str], param_key: str = "data"
    ) -> list[GoalPromptResponse]:
        raise NotImplementedError("method not supported")

    def verify_acquisitions(
        self, resolutions: list[OrganizationResolution]
    ) -> list[GoalPromptResponse]:
        params = self._generate_as_tasks(resolutions=resolutions)
        return self._analyzed_all_tasks(params=params)

    def _generate_as_tasks(
        self, resolutions: list[OrganizationResolution]
    ) -> list[dict[str, str]]:
        tasks = []
        for resolution in resolutions:
            task_params = self.input_params.copy()
            task_params[PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY] = (
                resolution.official_name
            )
            task_params[PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY] = (
                json.dumps(resolution, indent=4)
            )
            tasks.append(task_params)
        return tasks
