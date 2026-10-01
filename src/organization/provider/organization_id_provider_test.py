import logging
import unittest

import pytest

from organization.provider.organization_id_provider import OrganizationIdProvider
from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_by_key_provider import (
    OrganizationResolutionMergeByKeyProvider,
)

logger = logging.getLogger(__name__)


class OrganizationIdProviderTest(unittest.TestCase):
    ORGANIZsATION = "ORGANIZATION"
    COMPANY = "COMPANY"
    HOSPITAL = "HOSPITAL"
    UNIVERSITY = "UNIVERSITY"
    NONPROFIT = "NONPROFIT"
    FOUNDATION = "FOUNDATION"
    GOVERNMENT = "GOVERNMENT"

    @pytest.fixture(autouse=True)
    def _organization_id_provider(
        self, organization_id_provider: OrganizationIdProvider
    ) -> None:
        self.organization_id_provider = organization_id_provider

    @pytest.fixture(autouse=True)
    def _organization_resolution_merge_by_key_provider(
        self,
        organization_resolution_merge_by_key_provider: OrganizationResolutionMergeByKeyProvider,
    ) -> None:
        self.organization_resolution_merge_provider = (
            organization_resolution_merge_by_key_provider
        )

    @pytest.fixture(autouse=True)
    def _sample_organization_resolutions(
        self, sample_organization_resolutions: list[OrganizationResolution]
    ) -> None:
        self.sample_organization_resolutions = sample_organization_resolutions

    def test_sanity(self):
        assert self.organization_resolution_merge_provider is not None
        assert self.organization_id_provider is not None
        assert self.sample_organization_resolutions is not None
        assert len(self.sample_organization_resolutions) > 0

    def test_when_companies_then_assign_ids(self):

        merged_resolutions = self.organization_resolution_merge_provider.merge(
            self.sample_organization_resolutions
        )
        resolutions = self.organization_id_provider.assign_canonical_ids(
            merged_resolutions
        )
        assert resolutions is not None
        assert len(resolutions) == 3

        expected = ["U000000", "C000000"]
        for index, expect in enumerate(expected):
            assert resolutions[index].id is not None
            key = resolutions[index].id
            assert key is not None and key.id == expect
