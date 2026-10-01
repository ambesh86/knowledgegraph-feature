import logging
from pathlib import Path
import unittest

import pytest

from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)

logger = logging.getLogger(__name__)


class OrganizationResoutionMapperTest(unittest.TestCase):

    def setUp(self):
        self.organization_test_data_dir = "tests/data/organization/checkpoint"
        self.organization_json_0 = Path(
            f"{self.organization_test_data_dir}/23dc4eb6d41f48878d433a3181145954.json"
        ).read_text()

    @pytest.fixture(autouse=True)
    def _organization_resolution_mapper(
        self, organization_resolution_mapper: OrganizationResolutionMapper
    ) -> None:
        self.organization_resolution_mapper = organization_resolution_mapper

    def test_sanity(self):
        assert self.organization_resolution_mapper is not None
        assert self.organization_json_0 is not None

    def test_when_map_companies_then_resolution(self):
        resolution = self.organization_resolution_mapper.map(
            json_payload=self.organization_json_0
        )
        assert resolution is not None

        vifor_resolution = resolution
        assert vifor_resolution.official_name == "Vifor (International) Inc.".upper()
        assert vifor_resolution.parent == "CSL Limited".upper()
        assert vifor_resolution.organization_type == "COMPANY"
        assert len(vifor_resolution.acquisitions) == 1
        assert len(vifor_resolution.spelling_variations) == 4
        assert len(vifor_resolution.subsidiaries) == 7
        assert len(vifor_resolution.mergers) == 0
        assert len(vifor_resolution.demergers) == 0
        assert vifor_resolution.query_term == ""

    def test_when_map_companies_and_query_override_then_resolution(self):
        query_term_override = "VIFOR INCORPORATED"
        resolution = self.organization_resolution_mapper.map(
            json_payload=self.organization_json_0,
            query_term_override=query_term_override,
        )
        assert resolution is not None

        vifor_resolution = resolution
        assert vifor_resolution.official_name == "Vifor (International) Inc.".upper()
        assert vifor_resolution.parent == "CSL Limited".upper()
        assert vifor_resolution.organization_type == "COMPANY"
        assert len(vifor_resolution.acquisitions) == 1
        assert len(vifor_resolution.spelling_variations) == 5
        assert len(vifor_resolution.subsidiaries) == 7
        assert len(vifor_resolution.mergers) == 0
        assert len(vifor_resolution.demergers) == 0
        assert vifor_resolution.query_term == query_term_override
