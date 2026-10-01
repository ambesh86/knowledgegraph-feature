from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import BaseChatModel
from networkx import Graph

from document.analyze.document_analyzer import DocumentAnalyzer
from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import CommunitySummaryProvider
from graph.community.analyze.louvain_community_provider import (
    LouvainCommunityProvider,
)
from graph.community.analyze.summary_provider import SummaryProvider
from graph.community.mapper.community_report_parser import CommunityReportParser
from graph.community.mapper.csv_mapper import CsvMapper
from graph.mapper.graph_mapper import GraphMapper
from graph.mapper.triples_parser import TriplesParser
from graph.model.extraction import Extraction
from infra.llm.llm_chat_factory import LlmChatFactory
from infra.llm.prompt.generate import (
    generate_knowledge_graph_community_report_input_params,
    generate_knowlege_graph_summary_input_params,
)
from infra.llm.prompt.prompt_response import PromptResponse
from infra.llm.prompt.prompt_title import PromptTitle

TEST_DATA = "tests/data"
TRIPLES_JSON = f"{TEST_DATA}/triples.json"
TRIPLES_JSON_LG = f"{TEST_DATA}/triples-lg.json"
COMMUNITY_REPORT_FILE = f"{TEST_DATA}/community-summary.txt"


@pytest.fixture(scope="class", autouse=True)
def summary_provider(kg_summary_analyzer_mock: DocumentAnalyzer) -> SummaryProvider:
    return SummaryProvider(kg_summary_analyzer_mock)


@pytest.fixture(scope="class", autouse=True)
def community_summary_provider(
    community_summary_analyzer_mock: DocumentAnalyzer,
    csv_mapper: CsvMapper,
) -> CommunitySummaryProvider:
    return CommunitySummaryProvider(
        document_analyzer=community_summary_analyzer_mock,
        csv_mapper=csv_mapper,
    )


@pytest.fixture(scope="class", autouse=False)
def csv_mapper() -> CsvMapper:
    return CsvMapper()


@pytest.fixture(scope="class", autouse=False)
def community_provider() -> CommunityProvider:
    return LouvainCommunityProvider()


@pytest.fixture(scope="class", autouse=False)
def community_report_parser() -> CommunityReportParser:
    return CommunityReportParser()


@pytest.fixture(scope="class", autouse=True)
def community_summary_analyzer_mock(
    community_summary_response: list[PromptResponse],
) -> DocumentAnalyzer:
    input_params = [generate_knowledge_graph_community_report_input_params()]
    document_analyzer = DocumentAnalyzer(
        None,
        input_params,
    )
    document_analyzer.analyze_document_pages = MagicMock(
        return_value=community_summary_response
    )
    return document_analyzer


@pytest.fixture(scope="class", autouse=True)
def community_summary_analyzer(
    chatgpt_llm: BaseChatModel,
) -> DocumentAnalyzer:
    input_params = [generate_knowledge_graph_community_report_input_params()]
    document_analyzer = DocumentAnalyzer(
        chatgpt_llm,
        input_params,
    )
    return document_analyzer


@pytest.fixture(scope="class", autouse=False)
def chatgpt_llm() -> BaseChatModel:
    model_name = "chatgpt-4o-latest"
    return LlmChatFactory.openai_instance(model=model_name)


@pytest.fixture(scope="class", autouse=False)
def bedrock_llm() -> BaseChatModel:
    model_name = "meta.llama3-70b-instruct-v1:0"
    return LlmChatFactory.bedrock_instance(model=model_name)


@pytest.fixture(scope="class", autouse=True)
def kg_summary_analyzer(bedrock_llm: BaseChatModel) -> DocumentAnalyzer:
    input_params = [generate_knowlege_graph_summary_input_params()]
    document_analyzer = DocumentAnalyzer(
        bedrock_llm,
        input_params,
    )
    return document_analyzer


@pytest.fixture(scope="class", autouse=True)
def kg_summary_analyzer_mock(
    analyze_document_response: list[PromptResponse],
) -> DocumentAnalyzer:
    input_params = [generate_knowlege_graph_summary_input_params()]
    document_analyzer = DocumentAnalyzer(
        None,
        input_params,
    )
    document_analyzer.analyze_document_pages = MagicMock(
        return_value=analyze_document_response
    )
    return document_analyzer


@pytest.fixture(scope="class", autouse=True)
def analyze_document_response() -> list[PromptResponse]:
    return [
        PromptResponse(
            title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
            question="",
            llm_response="""Here is the comprehensive summary:
DNA-PKcs, also known as DNA-dependent protein kinase catalytic subunit, is a key enzyme that plays a crucial role in the Non-Homologous End Joining (NHEJ) pathway. Interestingly, inhibition of DNA-PKcs has been found to promote Homology-Directed Repair (HDR) in gene editing applications.
""",
        ),
        PromptResponse(
            title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
            question="",
            llm_response="""Here is the comprehensive summary:
Recombinant Adeno-Associated Virus serotype 6 (rAAV6) templates are viral vectors used to deliver DNA templates for Homology-Directed Repair (HDR) in gene editing applications.
""",
        ),
        PromptResponse(
            title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
            question="",
            llm_response="""Here is the comprehensive summary:
i53 mRNA is a synthetic messenger RNA designed to inhibit 53BP1, thereby promoting Homology-Directed Repair (HDR) over Non-Homologous End Joining (NHEJ) in gene editing applications.
""",
        ),
        PromptResponse(
            title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
            question="",
            llm_response="""Here is the comprehensive summary:
HDR (Homologous Directed Repair) is a precise DNA repair mechanism that uses a homologous sequence as a template to repair double-strand breaks. It is often targeted in gene editing to achieve accurate genetic modifications.
""",
        ),
    ]


@pytest.fixture(scope="class", autouse=True)
def community_summary_response(sample_community_report: str) -> list[PromptResponse]:
    return [
        PromptResponse(
            title=PromptTitle.KNOWLEGE_GRAPH_COMMUNITY_SUMMARY,
            question="",
            llm_response=sample_community_report,
        )
    ]


@pytest.fixture(scope="class", autouse=True)
def sample_extraction() -> Extraction:
    return _read_extraction(TRIPLES_JSON)


@pytest.fixture(scope="class", autouse=True)
def sample_extraction_lg() -> Extraction:
    return _read_extraction(TRIPLES_JSON_LG)


@pytest.fixture(scope="class", autouse=True)
def sample_graph() -> Graph:
    extraction = _read_extraction(TRIPLES_JSON)
    graph_mapper = GraphMapper()
    return graph_mapper.map(extraction)


@pytest.fixture(scope="class", autouse=True)
def sample_graph_lg() -> Graph:
    extraction = _read_extraction(TRIPLES_JSON_LG)
    graph_mapper = GraphMapper()
    return graph_mapper.map(extraction)


@pytest.fixture(scope="class", autouse=True)
def sample_community_report() -> str:
    return Path(COMMUNITY_REPORT_FILE).read_text()


def _read_extraction(file_name: str) -> Extraction:
    triples_parser = TriplesParser()
    json = Path(file_name).read_text()
    extraction = triples_parser.parse(json)
    return extraction
