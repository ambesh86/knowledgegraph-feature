import logging
import unittest
from unittest.mock import MagicMock, Mock

import pytest

from organization.analyzer.concurrent_organization_name_verifier import (
    ConcurrentOrganizationNameVerifier,
)
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
)
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse

logger = logging.getLogger(__name__)


class ConcurrentOrganizationNameVerifierTest(unittest.TestCase):

    def setUp(self):
        self.name_verifier = ConcurrentOrganizationNameVerifier(model=Mock())
        self.mocked_analyze_task = MagicMock()
        self.mocked_analyze_task.side_effect = [
            self.response_as_false,
            self.response_as_true,
        ]
        self.name_verifier._analyze_task = self.mocked_analyze_task

    @pytest.fixture(autouse=True)
    def _organization_name_verification_response_as_false(
        self, organization_name_verification_response_as_false: GoalPromptResponse
    ) -> None:
        self.response_as_false = organization_name_verification_response_as_false

    @pytest.fixture(autouse=True)
    def _organization_resolution_as_true(
        self, organization_name_verification_response_as_true: GoalPromptResponse
    ) -> None:
        self.response_as_true = organization_name_verification_response_as_true

    def test_ready(self):
        assert self.name_verifier is not None

    def test_when_verify_org_names_then_response(self):
        orgs = {
            "BRISTOL-MYERS SQUIBB COMPANY AND ONO PHARMACEUTICAL CO., LTD.",
            "BOEHRINGER INGELHEIM PHARMACEUTICALS, INC.",
        }
        responses = self.name_verifier.analyze_data(
            data=orgs, param_key=PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY
        )
        assert responses is not None
        logger.info(responses)

        assert self.mocked_analyze_task.call_count == 2
        response_values = set(
            [e.input[PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY] for e in responses]
        )
        for expected in orgs:
            assert expected in response_values
