import logging
from pathlib import Path
import pytest

from organization.model.organization_resolution import OrganizationResolution
from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)
from organization.provider.organization_id_generator import OrganizationIdGenerator
from organization.provider.organization_id_provider import OrganizationIdProvider
from organization.provider.organization_resolution_merge_by_key_provider import (
    OrganizationResolutionMergeByKeyProvider,
)
from organization.provider.organization_resolution_merge_by_spelling_provider import (
    OrganizationResolutionMergeBySpellingProvider,
)

logger = logging.getLogger(__name__)

ORGANIZATION_TEST_DATA_DIR = "tests/data/organization/checkpoint"
ORGANIZATION_JSON_0 = f"{ORGANIZATION_TEST_DATA_DIR}/univ_00.json"
ORGANIZATION_JSON_1 = f"{ORGANIZATION_TEST_DATA_DIR}/univ_01.json"
ORGANIZATION_JSON_2 = (
    f"{ORGANIZATION_TEST_DATA_DIR}/23dc4eb6d41f48878d433a3181145954.json"
)
ORGANIZATION_JSON_3 = (
    f"{ORGANIZATION_TEST_DATA_DIR}/09d5c4639ead9f9a37f0e6d6472b943b.json"
)
ORGANIZATION_BAD_ORG_TYPE_JSON_0 = f"{ORGANIZATION_TEST_DATA_DIR}/univ_bad_type_00.json"
ORGANIZATION_BAD_ORG_TYPE_JSON_1 = f"{ORGANIZATION_TEST_DATA_DIR}/univ_bad_type_01.json"
ORGANIZATION_WITH_PARENT_JSON_0 = f"{ORGANIZATION_TEST_DATA_DIR}/parent0.json"
ORGANIZATION_WITH_PARENT_JSON_1 = f"{ORGANIZATION_TEST_DATA_DIR}/parent1.json"
ORGANIZATION_WITH_PARENT_JSON_2 = f"{ORGANIZATION_TEST_DATA_DIR}/parent2.json"

ORGANIZATION_WITH_SPELLING_JSON_0 = f"{ORGANIZATION_TEST_DATA_DIR}/aaipharm_00.json"
ORGANIZATION_WITH_SPELLING_JSON_1 = f"{ORGANIZATION_TEST_DATA_DIR}/aaipharm_01.json"
ORGANIZATION_WITH_SPELLING_JSON_2 = f"{ORGANIZATION_TEST_DATA_DIR}/aaipharm_02.json"
ORGANIZATION_WITH_SPELLING_JSON_3 = f"{ORGANIZATION_TEST_DATA_DIR}/aaipharm_03.json"


@pytest.fixture(scope="class", autouse=True)
def organization_resolution_merge_by_key_provider() -> (
    OrganizationResolutionMergeByKeyProvider
):
    return OrganizationResolutionMergeByKeyProvider()


@pytest.fixture(scope="class", autouse=True)
def organization_resolution_merge_by_spelling_provider() -> (
    OrganizationResolutionMergeBySpellingProvider
):
    return OrganizationResolutionMergeBySpellingProvider()


@pytest.fixture(scope="class", autouse=False)
def organization_resolution_mapper() -> OrganizationResolutionMapper:
    return OrganizationResolutionMapper()


@pytest.fixture(scope="class", autouse=True)
def organization_id_generator() -> OrganizationIdGenerator:
    return OrganizationIdGenerator()


@pytest.fixture(scope="class", autouse=True)
def organization_id_provider(
    organization_id_generator: OrganizationIdGenerator,
) -> OrganizationIdProvider:
    return OrganizationIdProvider(organization_id_generator)


@pytest.fixture(scope="class", autouse=True)
def sample_organization_resolutions_with_bad_org_types(
    organization_resolution_mapper: OrganizationResolutionMapper,
) -> list[OrganizationResolution]:
    resolutions = [
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_BAD_ORG_TYPE_JSON_0
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_BAD_ORG_TYPE_JSON_1
        ),
    ]
    return [el for el in resolutions if el is not None]


@pytest.fixture(scope="class", autouse=True)
def sample_organization_resolutions(
    organization_resolution_mapper: OrganizationResolutionMapper,
) -> list[OrganizationResolution]:
    resolutions = [
        _load_resolution(organization_resolution_mapper, ORGANIZATION_JSON_0),
        _load_resolution(organization_resolution_mapper, ORGANIZATION_JSON_1),
        _load_resolution(organization_resolution_mapper, ORGANIZATION_JSON_2),
        _load_resolution(organization_resolution_mapper, ORGANIZATION_JSON_3),
    ]
    return [el for el in resolutions if el is not None]


@pytest.fixture(scope="class", autouse=True)
def sample_organization_resolutions_with_parent(
    organization_resolution_mapper: OrganizationResolutionMapper,
) -> list[OrganizationResolution]:
    resolutions = [
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_PARENT_JSON_0
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_PARENT_JSON_1
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_PARENT_JSON_2
        ),
    ]
    return [el for el in resolutions if el is not None]


@pytest.fixture(scope="class", autouse=True)
def sample_organization_resolutions_with_spellings(
    organization_resolution_mapper: OrganizationResolutionMapper,
) -> list[OrganizationResolution]:
    resolutions = [
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_SPELLING_JSON_0
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_SPELLING_JSON_1
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_SPELLING_JSON_2
        ),
        _load_resolution(
            organization_resolution_mapper, ORGANIZATION_WITH_SPELLING_JSON_3
        ),
    ]
    return [el for el in resolutions if el is not None]


def _load_resolution(
    organization_resolution_mapper: OrganizationResolutionMapper, file_name: str
) -> OrganizationResolution | None:
    json = Path(file_name).read_text()
    return organization_resolution_mapper.map(json)
