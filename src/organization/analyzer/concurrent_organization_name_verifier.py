import logging

from langchain_core.language_models import BaseChatModel

from infra.llm.analyzer.concurrent_goal_analyzer import ConcurrentGoalAnalyzer
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse
from organization.infra.llm.prompt.generate import (
    generate_organization_name_verification_input_params,
)
from organization.model.organization_resolution import OrganizationResolution
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
)

logger = logging.getLogger(__name__)


class ConcurrentOrganizationNameVerifier(ConcurrentGoalAnalyzer):
    """
    Analyze an organization name and verify the name appear as a valid organization name
    """

    def __init__(
        self,
        model: BaseChatModel,
        max_workers: int = 4,
    ):
        super().__init__(
            model=model,
            max_workers=max_workers,
            input_params=generate_organization_name_verification_input_params(),
        )

    def verify_names(self, names: set[str]) -> list[GoalPromptResponse]:
        logger.info(f"{names}")
        return self.analyze_data(
            data=names, param_key=PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY
        )

    def verify_resolutions(
        self, resolutions: list[OrganizationResolution]
    ) -> list[GoalPromptResponse]:
        data = {resolution.official_name for resolution in resolutions}
        return self.verify_names(names=data)
