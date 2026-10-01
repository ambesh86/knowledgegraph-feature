import logging
import unittest

import pytest

from organization.provider.organization_id_generator import OrganizationIdGenerator

logger = logging.getLogger(__name__)


class OrganizationIdGeneratorTest(unittest.TestCase):
    ORGANIZATION = "ORGANIZATION"
    COMPANY = "COMPANY"
    HOSPITAL = "HOSPITAL"
    UNIVERSITY = "UNIVERSITY"
    NONPROFIT = "NONPROFIT"
    FOUNDATION = "FOUNDATION"
    GOVERNMENT = "GOVERNMENT"

    @pytest.fixture(autouse=True)
    def _organization_id_generator(
        self, organization_id_generator: OrganizationIdGenerator
    ) -> None:
        self.organization_id_generator = organization_id_generator

    def test_sanity(self):
        assert self.organization_id_generator is not None

    def test_when_company_then_id(self):
        id0 = self.organization_id_generator.generate_id(
            OrganizationIdGeneratorTest.COMPANY
        )
        assert id0 is not None
        assert id0 == "C000000"

    def test_when_unknown_type_then_id(self):
        organization_id_generator = OrganizationIdGenerator()
        with pytest.raises(KeyError):
            organization_id_generator.generate_id("COUNTRY CLUB")

    def test_when_empty_type_then_id(self):
        organization_id_generator = OrganizationIdGenerator()
        with pytest.raises(ValueError):
            organization_id_generator.generate_id("")

    def test_when_empty_type_then_id2(self):
        organization_id_generator = OrganizationIdGenerator()
        with pytest.raises(ValueError):
            organization_id_generator.generate_id("         ")

    def test_when_company_then_many_ids(self):
        organization_id_generator = OrganizationIdGenerator()
        ids = [
            organization_id_generator.generate_id(OrganizationIdGeneratorTest.COMPANY)
            for idx in range(0, 11)
        ]
        assert ids is not None
        assert len(ids) == 11
        assert ids[0] == "C000000"
        assert ids[1] == "C000001"
        assert ids[-1] == "C000010"

    def test_when_organization_then_many_ids(self):
        organization_id_generator = OrganizationIdGenerator()
        ids = [
            organization_id_generator.generate_id(
                OrganizationIdGeneratorTest.ORGANIZATION
            )
            for idx in range(0, 11)
        ]
        assert ids is not None
        assert len(ids) == 11
        assert ids[0] == "O000000"
        assert ids[1] == "O000001"
        assert ids[-1] == "O000010"

    def test_when_hospital_then_many_ids(self):
        organization_id_generator = OrganizationIdGenerator()
        ids = [
            organization_id_generator.generate_id(OrganizationIdGeneratorTest.HOSPITAL)
            for idx in range(0, 11)
        ]
        assert ids is not None
        assert len(ids) == 11
        assert ids[0] == "H000000"
        assert ids[1] == "H000001"
        assert ids[-1] == "H000010"

    def test_when_government_then_many_ids(self):
        organization_id_generator = OrganizationIdGenerator()
        ids = [
            organization_id_generator.generate_id(
                OrganizationIdGeneratorTest.GOVERNMENT
            )
            for idx in range(0, 11)
        ]
        assert ids is not None
        assert len(ids) == 11
        assert ids[0] == "G000000"
        assert ids[1] == "G000001"
        assert ids[-1] == "G000010"

    def test_when_multiple_types_then_many_ids(self):
        organization_id_generator = OrganizationIdGenerator()
        batch_size = 4
        batch0 = [
            organization_id_generator.generate_id(
                OrganizationIdGeneratorTest.GOVERNMENT
            )
            for idx in range(0, batch_size)
        ]
        batch1 = [
            organization_id_generator.generate_id(
                OrganizationIdGeneratorTest.ORGANIZATION
            )
            for idx in range(0, batch_size)
        ]
        batch2 = [
            organization_id_generator.generate_id(
                OrganizationIdGeneratorTest.GOVERNMENT
            )
            for idx in range(0, batch_size)
        ]

        ids = [*batch0, *batch1, *batch2]
        assert ids is not None
        assert len(ids) == batch_size * 3
        assert ids[0] == "G000000"
        assert ids[1] == "G000001"
        assert ids[2] == "G000002"
        assert ids[3] == "G000003"
        assert ids[4] == "O000000"
        assert ids[5] == "O000001"
        assert ids[6] == "O000002"
        assert ids[7] == "O000003"
        assert ids[-1] == "G000007"
