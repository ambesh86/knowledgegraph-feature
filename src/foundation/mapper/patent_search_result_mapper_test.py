import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.patent_search_result_mapper import PatentSearchResultMapper


logger = logging.getLogger(__name__)


class PatentSearchResultMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _patent_search_result_mapper(
        self, patent_search_result_mapper: PatentSearchResultMapper
    ) -> None:
        self.patent_search_result_mapper = patent_search_result_mapper

    @pytest.fixture(autouse=True)
    def _sample_clinicaltrial_response_0(
        self, sample_clinicaltrial_response_0: DataFrame
    ) -> None:
        self.sample_clinicaltrial_response_0 = sample_clinicaltrial_response_0

    def test_sanity(self):
        assert self.sample_clinicaltrial_response_0 is not None
        assert self.patent_search_result_mapper is not None

    def test_when_map_drug_response_and_empty_dataframe_then_return(self):
        response = self.patent_search_result_mapper.map_drug_response(
            search_id="drugid1", dataframe=None
        )
        assert response is not None

        assert response.count == 0
        assert response.results == []

    def test_when_map_clinicaltrail_response_and_empty_dataframe_then_return(self):
        response = self.patent_search_result_mapper.map_clinicaltrail_response(
            search_id="nct00011", dataframe=None
        )
        assert response is not None

        assert response.count == 0
        assert response.results == []

    def test_when_map_clinicaltrail_response_then_return(self):
        response = self.patent_search_result_mapper.map_clinicaltrail_response(
            search_id="nct00011", dataframe=self.sample_clinicaltrial_response_0
        )
        assert response is not None

        assert response.count == 4
        assert response.search_id == "nct00011"
        assert len(response.results) == 4
        assert response.results[0].patent_id == "20250241930"
        assert response.results[1].patent_id == "20250235425"
