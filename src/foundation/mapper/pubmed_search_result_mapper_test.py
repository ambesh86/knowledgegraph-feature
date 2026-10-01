import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.pubmed_search_result_mapper import PubmedSearchResultMapper


logger = logging.getLogger(__name__)


class PubmedSearchResultMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _pubmed_search_result_mapper(
        self, pubmed_search_result_mapper: PubmedSearchResultMapper
    ) -> None:
        self.pubmed_search_result_mapper = pubmed_search_result_mapper

    @pytest.fixture(autouse=True)
    def _sample_clinicaltrial_to_pubmed_response_0(
        self, sample_clinicaltrial_to_pubmed_response_0: DataFrame
    ) -> None:
        self.sample_clinicaltrial_to_pubmed_response_0 = (
            sample_clinicaltrial_to_pubmed_response_0
        )

    @pytest.fixture(autouse=True)
    def _sample_drug_to_pubmed_response_0(
        self, sample_drug_to_pubmed_response_0: DataFrame
    ) -> None:
        self.sample_drug_to_pubmed_response_0 = sample_drug_to_pubmed_response_0

    @pytest.fixture(autouse=True)
    def _sample_geneprotein_to_pubmed_response_0(
        self, sample_geneprotein_to_pubmed_response_0: DataFrame
    ) -> None:
        self.sample_geneprotein_to_pubmed_response_0 = (
            sample_geneprotein_to_pubmed_response_0
        )

    def test_sanity(self):
        assert self.pubmed_search_result_mapper is not None
        assert self.sample_clinicaltrial_to_pubmed_response_0 is not None
        assert self.sample_drug_to_pubmed_response_0 is not None
        assert self.sample_geneprotein_to_pubmed_response_0 is not None

    def test_when_map_gene_response_and_empty_dataframe_then_return(self):
        response = self.pubmed_search_result_mapper.map_gene_response(
            gene_protein="PDE3A", dataframe=None
        )
        assert response is not None

        assert response.count == 0
        assert response.results == []

    def test_when_map_drug_response_and_empty_dataframe_then_return(self):
        response = self.pubmed_search_result_mapper.map_drug_response(
            search_id="drugid1", dataframe=None
        )
        assert response is not None

        assert response.count == 0
        assert response.results == []

    def test_when_map_clinicaltrail_response_and_empty_dataframe_then_return(self):
        response = self.pubmed_search_result_mapper.map_clinicaltrail_response(
            search_id="nct00011", dataframe=None
        )
        assert response is not None

        assert response.count == 0
        assert response.results == []

    def test_when_map_clinicaltrail_response_then_return(self):
        response = self.pubmed_search_result_mapper.map_clinicaltrail_response(
            search_id="nct00011",
            dataframe=self.sample_clinicaltrial_to_pubmed_response_0,
        )
        assert response is not None

        assert response.count == 4
        assert response.search_id == "nct00011"
        assert len(response.results) == 4
        assert response.results[0].pmid == "28371676"
        assert response.results[1].pmid == "28395218"
        assert response.results[2].pmid == "28400235"
        assert response.results[3].pmid == "28400238"

    def test_when_map_drug_response_then_return(self):
        response = self.pubmed_search_result_mapper.map_drug_response(
            search_id="DB0001",
            dataframe=self.sample_drug_to_pubmed_response_0,
        )
        assert response is not None

        assert response.count == 3
        assert response.search_id == "DB0001"
        assert len(response.results) == 3
        assert response.results[0].pmid == "37549850"
        assert response.results[1].pmid == "36577220"
        assert response.results[2].pmid == "35797898"

    def test_when_map_gene_response_then_return(self):
        response = self.pubmed_search_result_mapper.map_gene_response(
            gene_protein="PDE3A",
            dataframe=self.sample_geneprotein_to_pubmed_response_0,
        )
        assert response is not None

        assert response.count == 3
        assert response.gene_protein == "PDE3A"
        assert len(response.results) == 3
        assert response.results[0].pmid == "34141080"
        assert response.results[1].pmid == "33933754"
        assert response.results[2].pmid == "32503691"
