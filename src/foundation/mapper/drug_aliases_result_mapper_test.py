import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.drug_aliases_result_mapper import DrugAliasesResultMapper


logger = logging.getLogger(__name__)


class DrugAliasesResultMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _drug_aliases_result_mapper(
        self, drug_aliases_result_mapper: DrugAliasesResultMapper
    ) -> None:
        self.drug_aliases_result_mapper = drug_aliases_result_mapper

    @pytest.fixture(autouse=True)
    def _sample_drug_alias_response_0(
        self, sample_drug_alias_response_0: DataFrame
    ) -> None:
        self.sample_drug_alias_response_0 = sample_drug_alias_response_0

    def test_sanity(self):
        assert self.drug_aliases_result_mapper is not None
        assert self.sample_drug_alias_response_0 is not None

    def test_when_map_drug_response_and_empty_dataframe_then_return(self):
        response = self.drug_aliases_result_mapper.map(drug_search="DB00182", df=None)
        assert response is None

    def test_when_map_drug_response_then_return(self):
        response = self.drug_aliases_result_mapper.map(
            drug_search="DB00182", df=self.sample_drug_alias_response_0
        )
        assert response is not None

        assert response.count == 4
        assert response.drug == "DB00182"
        assert len(response.results) == 4
        assert response.results[0].is_canonical == True
        assert response.results[0].id == "DB00182"
        assert response.results[0].name == "Amphetamine"
        assert response.results[1].is_canonical == False
        assert response.results[1].id == "drug_db00182_product_0"
        assert response.results[1].name == "Adderall"
