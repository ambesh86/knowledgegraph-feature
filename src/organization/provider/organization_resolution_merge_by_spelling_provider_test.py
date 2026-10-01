import logging
import unittest

import pytest

from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_by_spelling_provider import (
    OrganizationResolutionMergeBySpellingProvider,
)

logger = logging.getLogger(__name__)


class OrganizationResoutionMergeBySpellingProviderTest(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def _sample_organization_resolutions_with_spellings(
        self,
        sample_organization_resolutions_with_spellings: list[OrganizationResolution],
    ) -> None:
        self.sample_organization_resolutions_with_spellings = (
            sample_organization_resolutions_with_spellings
        )

    @pytest.fixture(autouse=True)
    def _sample_organizations(
        self, sample_organization_resolutions: list[OrganizationResolution]
    ) -> None:
        self.sample_organization_resolutions = sample_organization_resolutions

    @pytest.fixture(autouse=True)
    def _organization_resolution_merge_by_spelling_provider(
        self,
        organization_resolution_merge_by_spelling_provider: OrganizationResolutionMergeBySpellingProvider,
    ) -> None:
        self.organization_resolution_merge_provider = (
            organization_resolution_merge_by_spelling_provider
        )

    def test_sanity(self):
        assert self.organization_resolution_merge_provider is not None
        assert len(self.sample_organization_resolutions) == 4
        assert len(self.sample_organization_resolutions_with_spellings) == 4

    def test_when_organizations_and_similar_spellings_then_merge(self):
        resolutions = self.organization_resolution_merge_provider.merge(
            resolutions=self.sample_organization_resolutions_with_spellings
        )

        # similar spelling lists do not merge
        assert resolutions is not None
        assert len(resolutions) == 1

        resolution = resolutions[0]
        assert resolution.organization_type == "COMPANY"
        assert resolution.official_name == "AAIPHARMA INC"
        assert resolution.query_term == "AAIPHARMA INC"
        assert len(resolution.spelling_variations) == 9
        assert len(resolution.acquisitions) == 0
        assert len(resolution.subsidiaries) == 0
        assert len(resolution.demergers) == 0
        assert len(resolution.mergers) == 1

    def test_when_organizations_and_nonsimilar_spellings_then_merge(self):
        resolutions = self.organization_resolution_merge_provider.merge(
            resolutions=self.sample_organization_resolutions
        )

        # non similar spelling lists do not merge
        assert resolutions is not None
        assert len(resolutions) == len(self.sample_organization_resolutions) - 1
