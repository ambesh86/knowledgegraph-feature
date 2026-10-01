from pathlib import Path

import pytest

from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)
from organization.model.organization_resolution import OrganizationResolution
from organization.mapper.organization_name_verifier_mapper import (
    OrganizationNameVerifierMapper,
)

ORGANIZATION_TEST_DATA_DIR = "tests/data/organization"
ORGANIZATION_JSON_0 = (
    f"{ORGANIZATION_TEST_DATA_DIR}/checkpoint/23dc4eb6d41f48878d433a3181145954.json"
)


@pytest.fixture(scope="class", autouse=False)
def organization_resolution_mapper() -> OrganizationResolutionMapper:
    return OrganizationResolutionMapper()


@pytest.fixture(scope="class", autouse=False)
def organization_name_verifier_mapper() -> OrganizationNameVerifierMapper:
    return OrganizationNameVerifierMapper()


@pytest.fixture(scope="class", autouse=True)
def sample_organization_resolution_0() -> OrganizationResolution | None:
    return _load_resolution(ORGANIZATION_JSON_0)


def _load_resolution(file_name: str) -> OrganizationResolution | None:
    mapper = OrganizationResolutionMapper()
    json = Path(file_name).read_text()
    resolution = mapper.map(json)
    return resolution
