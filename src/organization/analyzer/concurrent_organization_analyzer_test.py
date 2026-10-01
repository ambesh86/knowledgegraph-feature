import logging
import unittest
from unittest.mock import MagicMock, Mock

import pytest

from organization.analyzer.concurrent_organization_analyzer import (
    ConcurrentOrganizationAnalyzer,
)
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
)
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse

logger = logging.getLogger(__name__)


class ConcurrentOrganizationAnalyzerTest(unittest.TestCase):

    def setUp(self):
        self.organization_analyzer = ConcurrentOrganizationAnalyzer(model=Mock())
        self.mocked_analyze_task = MagicMock(return_value=self.response0)
        self.mocked_analyze_task.side_effect = [self.response0, self.response1]
        self.organization_analyzer._analyze_task = self.mocked_analyze_task

    @pytest.fixture(autouse=True)
    def _organization_resolution_response0(
        self, organization_resolution_response0: GoalPromptResponse
    ) -> None:
        self.response0 = organization_resolution_response0

    @pytest.fixture(autouse=True)
    def _organization_resolution_response1(
        self, organization_resolution_response1: GoalPromptResponse
    ) -> None:
        self.response1 = organization_resolution_response1

    def test_ready(self):
        assert self.organization_analyzer is not None

    def test_when_analyze_orgs_then_response(self):
        orgs = {"Vifor Inc", "CSL Behring"}
        responses = self.organization_analyzer.analyze_data(data=orgs)
        assert responses is not None
        logger.info(responses)

        assert self.mocked_analyze_task.call_count == 2
        response_values = set(
            [e.input[PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY] for e in responses]
        )
        for expected in orgs:
            assert expected in response_values
