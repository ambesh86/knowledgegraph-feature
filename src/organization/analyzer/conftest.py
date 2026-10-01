from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from organization.analyzer.concurrent_organization_analyzer import (
    ConcurrentOrganizationAnalyzer,
)
from organization.infra.llm.prompt.const import (
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
    PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY,
)
from infra.llm.prompt.goal_prompt_title import GoalPromptTitle
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse

ORGANIZATION_TEST_DATA_DIR = "tests/data/organization"
ORGANIZATION_RESPONSE_TEST_DATA = f"{ORGANIZATION_TEST_DATA_DIR}/response"
ORGANIZATION_RESPONSE_0 = f"{ORGANIZATION_RESPONSE_TEST_DATA}/response0.json"
ORGANIZATION_RESPONSE_1 = f"{ORGANIZATION_RESPONSE_TEST_DATA}/response1.json"

ORGANIZATION_NAME_VERIFICATION_RESPONSE_AS_FALSE = (
    f"{ORGANIZATION_RESPONSE_TEST_DATA}/name_verification_false.json"
)
ORGANIZATION_NAME_VERIFICATION_RESPONSE_AS_TRUE = (
    f"{ORGANIZATION_RESPONSE_TEST_DATA}/name_verification_true.json"
)

ORGANIZATION_REQUEST_TEST_DATA = f"{ORGANIZATION_TEST_DATA_DIR}/request"
ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_FAIL_0 = (
    f"{ORGANIZATION_REQUEST_TEST_DATA}/org_acquisition_verification_fail_0.json"
)
ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_SUCCESS_0 = (
    f"{ORGANIZATION_REQUEST_TEST_DATA}/org_acquisition_verification_success_0.json"
)


@pytest.fixture(scope="class", autouse=True)
def organization_resolution_analyzer_mock(
    analyze_organizations_response: list[GoalPromptResponse],
) -> ConcurrentOrganizationAnalyzer:
    analyzer = ConcurrentOrganizationAnalyzer(
        model=Mock(),
    )
    analyzer.analyze_data = MagicMock(return_value=analyze_organizations_response)
    return analyzer


@pytest.fixture(scope="class", autouse=True)
def analyze_organizations_response(
    organization_resolution_response0: GoalPromptResponse,
    organization_resolution_response1: GoalPromptResponse,
) -> list[GoalPromptResponse]:
    return [organization_resolution_response0, organization_resolution_response1]


@pytest.fixture(scope="class", autouse=True)
def organization_resolution_response0() -> GoalPromptResponse:
    response = _load_response(ORGANIZATION_RESPONSE_0)
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "Vifor Inc"},
        llm_response=response,
    )


@pytest.fixture(scope="class", autouse=True)
def organization_resolution_response1() -> GoalPromptResponse:
    response = _load_response(ORGANIZATION_RESPONSE_1)
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "CSL Behring"},
        llm_response=response,
    )


@pytest.fixture(scope="class", autouse=True)
def organization_name_verification_response_as_false() -> GoalPromptResponse:
    response = _load_response(ORGANIZATION_NAME_VERIFICATION_RESPONSE_AS_FALSE)
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={
            PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "BRISTOL-MYERS SQUIBB COMPANY AND ONO PHARMACEUTICAL CO., LTD."
        },
        llm_response=response,
    )


@pytest.fixture(scope="class", autouse=True)
def organization_name_verification_response_as_true() -> GoalPromptResponse:
    response = _load_response(ORGANIZATION_NAME_VERIFICATION_RESPONSE_AS_TRUE)
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={
            PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "BOEHRINGER INGELHEIM PHARMACEUTICALS, INC."
        },
        llm_response=response,
    )


@pytest.fixture(scope="class", autouse=True)
def organization_acquisition_verification_response_as_fail_0() -> GoalPromptResponse:
    input_data = _load_response(
        ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_FAIL_0
    )
    response = _load_response(ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_FAIL_0)
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={
            PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "BOEHRINGER INGELHEIM INTERNATIONAL GMBH",
            PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY: input_data,
        },
        llm_response=response,
    )


@pytest.fixture(scope="class", autouse=True)
def organization_acquisition_verification_response_as_success_0() -> GoalPromptResponse:
    input_data = _load_response(
        ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_SUCCESS_0
    )
    response = _load_response(
        ORGANIZATION_ACQUISITION_VERIFICATION_RESPONSE_AS_SUCCESS_0
    )
    return GoalPromptResponse(
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
        input={
            PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: "BAYER PHARMACEUTICALS CORPORATION",
            PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY: input_data,
        },
        llm_response=response,
    )


def _load_response(file_name: str) -> str:
    json = Path(file_name).read_text()
    return json if json is not None else ""
