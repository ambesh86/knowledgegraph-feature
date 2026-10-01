import logging
import unittest

import pytest

from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_by_key_provider import (
    OrganizationResolutionMergeByKeyProvider,
)

logger = logging.getLogger(__name__)


class OrganizationResoutionMergeByKeyProviderTest(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def _organizations_with_bad_types(
        self,
        sample_organization_resolutions_with_bad_org_types: list[
            OrganizationResolution
        ],
    ) -> None:
        self.sample_organization_resolutions_with_bad_org_types = (
            sample_organization_resolutions_with_bad_org_types
        )

    @pytest.fixture(autouse=True)
    def _sample_organizations_with_parent(
        self, sample_organization_resolutions_with_parent: list[OrganizationResolution]
    ) -> None:
        self.sample_organization_resolutions_with_parent = (
            sample_organization_resolutions_with_parent
        )

    @pytest.fixture(autouse=True)
    def _sample_organizations(
        self, sample_organization_resolutions: list[OrganizationResolution]
    ) -> None:
        self.sample_organization_resolutions = sample_organization_resolutions

    @pytest.fixture(autouse=True)
    def _organization_resolution_merge_by_key_provider(
        self,
        organization_resolution_merge_by_key_provider: OrganizationResolutionMergeByKeyProvider,
    ) -> None:
        self.organization_resolution_merge_provider = (
            organization_resolution_merge_by_key_provider
        )

    def test_sanity(self):
        assert self.organization_resolution_merge_provider is not None
        assert self.sample_organization_resolutions is not None
        assert len(self.sample_organization_resolutions) == 4
        assert self.sample_organization_resolutions_with_bad_org_types is not None
        assert self.sample_organization_resolutions_with_parent is not None
        assert len(self.sample_organization_resolutions_with_parent) == 3

    def test_when_organizations_then_merge(self):
        resolutions = self.organization_resolution_merge_provider.merge(
            resolutions=self.sample_organization_resolutions
        )

        assert resolutions is not None
        assert len(resolutions) == 3

        resolution = resolutions[0]
        assert resolution.organization_type == "UNIVERSITY"
        assert resolution.official_name == "RIJKSUNIVERSITEIT GRONINGEN"
        assert resolution.query_term == "RIJKSUNIVERSITEIT GRONINGEN"
        assert len(resolution.spelling_variations) == 4
        assert len(resolution.acquisitions) == 0
        assert len(resolution.subsidiaries) == 0
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0

        resolution = resolutions[1]
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "VIFOR (INTERNATIONAL) INC."
        assert resolution.parent == "CSL LIMITED"
        assert resolution.query_term == "VIFOR (INTERNATIONAL) INC."
        assert len(resolution.spelling_variations) == 4
        assert len(resolution.acquisitions) == 1
        assert len(resolution.subsidiaries) == 7
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0

        resolution = resolutions[2]
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "CSL BEHRING"
        assert resolution.parent == "CSL LIMITED"
        assert resolution.query_term == "CSL BEHRING"
        assert len(resolution.spelling_variations) == 1
        assert len(resolution.acquisitions) == 1
        assert len(resolution.subsidiaries) == 10
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0

    def test_when_organization_and_bad_org_then_merge(self):
        resolutions = self.organization_resolution_merge_provider.merge(
            resolutions=self.sample_organization_resolutions_with_bad_org_types
        )

        assert resolutions is not None
        assert len(resolutions) == 1

        resolution = resolutions[0]
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "ESPERION THERAPEUTICS, INC."
        assert resolution.query_term == "ESPERION THERAPEUTICS, INC."
        assert len(resolution.spelling_variations) == 2
        assert len(resolution.acquisitions) == 0
        assert len(resolution.subsidiaries) == 0
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0

    def test_when_resolution_with_same_parent_then_merge(self):
        resolutions = self.organization_resolution_merge_provider.merge(
            resolutions=self.sample_organization_resolutions_with_parent
        )

        assert resolutions is not None
        assert len(resolutions) == 3

        resolution = resolutions[0]
        assert resolution.parent == "GILEAD SCIENCES, INC."
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "CV THERAPEUTICS, INC."
        assert resolution.query_term == "CV THERAPEUTICS, INC."
        assert len(resolution.spelling_variations) == 2
        assert len(resolution.acquisitions) == 0
        assert len(resolution.subsidiaries) == 0
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0

        res2 = resolutions[1]
        assert res2.parent == "GILEAD SCIENCES, INC"
        assert res2.organization_type == "COMPANY"
        assert res2.official_name == "GILEAD BIOLOGICS INC"
        assert res2.query_term == "GILEAD BIOLOGICS INC"

        resolution = resolutions[2]
        assert resolution.parent == "GILEAD SCIENCES, INC."
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "IMMUNOMEDICS, INC."
        assert resolution.query_term == "IMMUNOMEDICS, INC."
        assert len(resolution.spelling_variations) == 4
        assert len(resolution.acquisitions) == 0
        assert len(resolution.subsidiaries) == 0
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 0
