import logging
from pathlib import Path
import unittest

import pytest

from organization.load.organization_resolution_loader import (
    OrganizationResolutionLoader,
)

logger = logging.getLogger(__name__)


class OrganizationResoutionLoaderTest(unittest.TestCase):

    def setUp(self):
        self.company_test_data_dir = "tests/data/organization/checkpoint"

    @pytest.fixture(autouse=True)
    def _organization_resolution_loader(
        self, organization_resolution_loader: OrganizationResolutionLoader
    ) -> None:
        self.organization_resolution_loader = organization_resolution_loader

    def test_sanity(self):
        assert self.organization_resolution_loader is not None

    def test_when_load_organizations_then_resolution(self):
        resolutions = self.organization_resolution_loader.load(
            data_dirs=[Path(self.company_test_data_dir)]
        )
        assert resolutions is not None
        assert len(resolutions) == 13

        orgs = {"Vifor (International) Inc.", "CSL Behring"}
        response_values = {e.official_name for e in resolutions}
        for expected in orgs:
            assert expected.upper() in response_values

        vifor = "Vifor (International) Inc.".upper()
        vifor_resolution = next(
            (el for el in resolutions if el.official_name == vifor),
            None,
        )
        assert vifor_resolution is not None
        assert vifor_resolution.parent == "CSL Limited".upper()
        assert vifor_resolution.organization_type == "COMPANY"
        assert len(vifor_resolution.acquisitions) == 1
        assert len(vifor_resolution.spelling_variations) == 4
        assert len(vifor_resolution.subsidiaries) == 7
        assert len(vifor_resolution.mergers) == 0
        assert len(vifor_resolution.demergers) == 0
        assert vifor_resolution.query_term == ""
