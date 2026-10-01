import logging
import unittest
from unittest.mock import MagicMock, Mock

import pytest

from organization.analyzer.concurrent_organization_acquisition_verifier import (
    ConcurrentOrganizationAcquisitionVerifier,
)
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
)
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse

logger = logging.getLogger(__name__)


class ConcurrentOrganizationAcquisitionVerifierTest(unittest.TestCase):

    def setUp(self):
        self.name_verifier = ConcurrentOrganizationAcquisitionVerifier(model=Mock())
        self.mocked_analyze_task = MagicMock()
        self.mocked_analyze_task.side_effect = [
            self.response_as_fail_0,
            self.response_as_success_0,
        ]
        self.name_verifier._analyze_task = self.mocked_analyze_task

    @pytest.fixture(autouse=True)
    def _organization_acquisition_verification_response_as_fail_0(
        self,
        organization_acquisition_verification_response_as_fail_0: GoalPromptResponse,
    ) -> None:
        self.response_as_fail_0 = (
            organization_acquisition_verification_response_as_fail_0
        )

    @pytest.fixture(autouse=True)
    def _organization_acquisition_verification_response_as_success_0(
        self,
        organization_acquisition_verification_response_as_success_0: GoalPromptResponse,
    ) -> None:
        self.response_as_success_0 = (
            organization_acquisition_verification_response_as_success_0
        )

    def test_ready(self):
        assert self.name_verifier is not None

    def test_when_verify_org_acquisitions_then_response(self):
        pass
        # orgs = {
        #     "BRISTOL-MYERS SQUIBB COMPANY AND ONO PHARMACEUTICAL CO., LTD.",
        #     "BOEHRINGER INGELHEIM PHARMACEUTICALS, INC.",
        # }
        # responses = self.name_verifier.analyze_data(
        #     data=orgs, param_key=PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY
        # )
        # assert responses is not None
        # logger.info(responses)

        # assert self.mocked_analyze_task.call_count == 2
        # response_values = set(
        #     [e.input[PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY] for e in responses]
        # )
        # for expected in orgs:
        #     assert expected in response_values
