import logging

from langchain_core.language_models import BaseChatModel

from infra.llm.analyzer.concurrent_goal_analyzer import ConcurrentGoalAnalyzer
from organization.infra.llm.prompt.generate import (
    generate_organization_name_analysis_input_params,
)

logger = logging.getLogger(__name__)


class ConcurrentOrganizationAnalyzer(ConcurrentGoalAnalyzer):
    """
    Analyze an organization name and resolve its multiple and related names
    """

    def __init__(
        self,
        model: BaseChatModel,
        max_workers: int = 4,
    ):
        super().__init__(
            model=model,
            max_workers=max_workers,
            input_params=generate_organization_name_analysis_input_params(),
        )
