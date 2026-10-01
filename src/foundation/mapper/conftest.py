from pandas import DataFrame
import pytest

from foundation.model.graph.graph import Graph
from foundation.mapper.graph_mapper import GraphMapper
from foundation.mapper.node_id_lookup_mapper import NodeIdLookupMapper
from foundation.mapper.node_details_mapper import NodeDetailsMapper
from foundation.mapper.facts_mapper import FactsMapper
from foundation.mapper.patent_search_result_mapper import PatentSearchResultMapper
from foundation.mapper.drug_aliases_result_mapper import DrugAliasesResultMapper
from foundation.mapper.pubmed_search_result_mapper import PubmedSearchResultMapper


@pytest.fixture(scope="class", autouse=False)
def graph_mapper() -> GraphMapper:
    return GraphMapper()


@pytest.fixture(scope="class", autouse=False)
def facts_mapper() -> FactsMapper:
    return FactsMapper()


@pytest.fixture(scope="class", autouse=False)
def node_id_lookup_mapper() -> NodeIdLookupMapper:
    return NodeIdLookupMapper()


@pytest.fixture(scope="class", autouse=False)
def node_details_mapper() -> NodeDetailsMapper:
    return NodeDetailsMapper()


@pytest.fixture(scope="class", autouse=False)
def patent_search_result_mapper() -> PatentSearchResultMapper:
    return PatentSearchResultMapper()


@pytest.fixture(scope="class", autouse=False)
def pubmed_search_result_mapper() -> PubmedSearchResultMapper:
    return PubmedSearchResultMapper()


@pytest.fixture(scope="class", autouse=True)
def drug_aliases_result_mapper() -> DrugAliasesResultMapper:
    return DrugAliasesResultMapper()


@pytest.fixture(scope="class", autouse=True)
def sample_node_details_0() -> DataFrame:
    return _load_node_details_0()


@pytest.fixture(scope="class", autouse=True)
def sample_node_id_lookup_0() -> DataFrame:
    return _load_node_id_lookup_0()


@pytest.fixture(scope="class", autouse=True)
def sample_graph_0(graph_mapper: GraphMapper) -> Graph | None:
    return graph_mapper.map(_load_subgraph_0())


@pytest.fixture(scope="class", autouse=True)
def sample_subgraph_0() -> DataFrame:
    return _load_subgraph_0()


@pytest.fixture(scope="class", autouse=True)
def sample_clinicaltrial_response_0() -> DataFrame:
    return _sample_clinicaltrial_response_0()


@pytest.fixture(scope="class", autouse=True)
def sample_clinicaltrial_to_pubmed_response_0() -> DataFrame:
    return _sample_clinicaltrial_to_pubmed_response_0()


@pytest.fixture(scope="class", autouse=True)
def sample_drug_to_pubmed_response_0() -> DataFrame:
    return _sample_drug_to_pubmed_response_0()


@pytest.fixture(scope="class", autouse=True)
def sample_geneprotein_to_pubmed_response_0() -> DataFrame:
    return _sample_geneprotein_to_pubmed_response_0()


@pytest.fixture(scope="class", autouse=True)
def sample_drug_alias_response_0() -> DataFrame:
    return _sample_drug_alias_response_0()


def _load_subgraph_0() -> DataFrame:
    # Sample DataFrame creation (same as above)
    data = {
        "startId": ["DB00846", "DB00846", "DB00538", "DB00538"],
        "startName": [
            "Flurandrenolide",
            "Flurandrenolide",
            "Gadoversetamide",
            "Gadoversetamide",
        ],
        "startLabels": [["drug"], ["drug"], ["drug"], ["drug"]],
        "endId": ["989", "11123", "989", "11123"],
        "endName": [
            "Pruritus",
            "Inflammatory abnormality of the skin",
            "Pruritus",
            "Inflammatory abnormality of the skin",
        ],
        "endLabels": [
            ["effect_phenotype"],
            ["effect_phenotype"],
            ["effect_phenotype"],
            ["effect_phenotype"],
        ],
        "relType": ["drug_effect", "drug_effect", "drug_effect", "drug_effect"],
    }
    return DataFrame(data)


def _load_node_id_lookup_0() -> DataFrame:
    data = {
        "n.node_id": ["DB00846", "DB00538"],
        "n.node_name": [
            "Flurandrenolide",
            "Gadoversetamide",
        ],
    }
    return DataFrame(data)


def _load_node_details_0() -> DataFrame:
    data = {
        "labels": [["exposure"]],
        "id": ["C031180"],
        "value": [
            "chrysene",
        ],
        "source": ["CTD"],
        "description": [None],
    }
    return DataFrame(data)


def _sample_clinicaltrial_response_0() -> DataFrame:
    data = {
        "nct_id": ["NCT05648006", "NCT05648006", "NCT05648006", "NCT05648006"],
        "patent_id": [
            "20250241930",
            "20250235425",
            "20250231177",
            "20250230262",
        ],
    }
    return DataFrame(data)


def _sample_clinicaltrial_to_pubmed_response_0() -> DataFrame:
    data = {
        "nct_id": ["NCT05648006", "NCT05648006", "NCT05648006", "NCT05648006"],
        "target_id": [
            "DB00544",
            "DB00544",
            "DB00544",
            "DB00544",
        ],
        "pmid": [
            "28371676",
            "28395218",
            "28400235",
            "28400238",
        ],
    }
    return DataFrame(data)


def _sample_drug_to_pubmed_response_0() -> DataFrame:
    data = {
        "drug_id": ["DB00683", "DB00683", "DB00683"],
        "drug_name": [
            "Midazolam",
            "Midazolam",
            "Midazolam",
        ],
        "pmid": ["37549850", "36577220", "35797898"],
    }
    return DataFrame(data)


def _sample_geneprotein_to_pubmed_response_0() -> DataFrame:
    data = {
        "node_name": ["PDE3A", "PDE3A", "PDE3A"],
        "pmid": ["34141080", "33933754", "32503691"],
    }
    return DataFrame(data)


def _sample_drug_alias_response_0() -> DataFrame:
    data = {
        "name": [
            "Amphetamine",
            "Adderall",
            "β-aminopropylbenzene",
            "1-phenyl-2-aminopropane",
        ],
        "node_id": [
            "DB00182",
            "drug_db00182_product_0",
            "drug_db00182_synonym_1",
            "drug_db00182_synonym_2",
        ],
        "drug_bank_id": ["DB00182", "DB00182", "DB00182", "DB00182"],
        "is_canonical": [True, False, False, False],
    }
    return DataFrame(data)
