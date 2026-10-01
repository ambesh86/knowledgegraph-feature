import logging
from pathlib import Path
import unittest

import pytest

from organization.mapper.organization_name_verifier_mapper import (
    OrganizationNameVerifierMapper,
)

logger = logging.getLogger(__name__)


class OrganizationNameVerifierMapperTest(unittest.TestCase):

    def setUp(self):
        self.organization_test_data_dir = "tests/data/organization/request"
        self.organization_fail_json_0 = Path(
            f"{self.organization_test_data_dir}/org_name_verification_fail_0.json"
        ).read_text()

    @pytest.fixture(autouse=True)
    def _organization_name_verifier_mapper(
        self, organization_name_verifier_mapper: OrganizationNameVerifierMapper
    ) -> None:
        self.organization_name_verifier_mapper = organization_name_verifier_mapper

    def test_sanity(self):
        assert self.organization_name_verifier_mapper is not None
        assert self.organization_fail_json_0 is not None

    def test_when_bad_name_and_map_then_false(self):
        validation = self.organization_name_verifier_mapper.map(
            json_payload=self.organization_fail_json_0
        )
        assert validation is not None
        assert (
            validation[0]
            == "BRISTOL-MYERS SQUIBB COMPANY AND ONO PHARMACEUTICAL CO., LTD."
        )
        assert not validation[1]

    def test_when_bad_response_and_map_then_false(self):
        validation = self.organization_name_verifier_mapper.map(
            json_payload="""
Here is the output in JSON format:

```
{
    "input": "0966452 B.C. LTD.",
    "valid_organization_name": true
}
```"""
        )
        assert validation is not None
        assert validation[0] == "0966452 B.C. LTD."
        assert validation[1]
