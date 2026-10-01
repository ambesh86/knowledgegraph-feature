import logging

from langchain_core.language_models import BaseChatModel
from neo4j import Driver

from document.analyze.document_analyzer import DocumentAnalyzer
from document.load.stored_summaries_loader import StoredSummariesLoader
from document.load.stored_triples_loader import StoredTriplesLoader
from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import (
    CommunitySummaryProvider,
)
from graph.community.analyze.leiden_community_provider import LeidenCommunityProvider
from graph.community.mapper.csv_mapper import CsvMapper
from graph.mapper.graph_mapper import GraphMapper
from graph.mapper.relationship_mapper import RelationshipMapper
from graph.mapper.triples_parser import TriplesParser
from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.summaries_parser import SummariesParser
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from infra.llm.llm_chat_factory import LlmChatFactory
from infra.llm.prompt.generate import (
    generate_knowledge_graph_community_report_input_params,
    generate_knowlege_graph_extraction_input_params,
    generate_knowlege_graph_summary_input_params,
)
from patent.pgpub.analyze.pgpub_knowledge_graph_analyzer import (
    PgPubKnowledgeGraphAnalyzer,
)
from patent.pgpub.analyze.pgpub_graph_summary_orchestrator import (
    PgpubGraphSummaryOrchestrator,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_linking_adapter import (
    Neo4jPgpubLinkingAdapter,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_summary_adapter import (
    Neo4jPgpubSummaryAdapter,
)

logger = logging.getLogger(__name__)


def pgpub_knowledge_graph_analyzer() -> PgPubKnowledgeGraphAnalyzer:
    return _pgpub_knowledge_graph_analyzer(
        pgpub_graph_summary_orchestrator=pgpub_graph_summary_orchestrator(4),
    )


def _pgpub_knowledge_graph_analyzer(
    pgpub_graph_summary_orchestrator: PgpubGraphSummaryOrchestrator,
) -> PgPubKnowledgeGraphAnalyzer:
    return PgPubKnowledgeGraphAnalyzer(
        summary_orchestrator=pgpub_graph_summary_orchestrator
    )


def pgpub_graph_summary_orchestrator(max_workers: int) -> PgpubGraphSummaryOrchestrator:
    driver = _neo4j_driver()
    model = _llm()
    return PgpubGraphSummaryOrchestrator(
        graph_mapper=_graph_mapper(),
        triples_parser=_triples_parser(),
        extraction_document_analyzer=_extraction_document_analyzer(
            model=model, max_workers=max_workers
        ),
        csv_mapper=_csv_mapper(),
        community_provider=_community_provider(),
        community_summary_provider=_community_summary_provider(model=model),
        stored_summaries_loader=_stored_summaries_loader(
            summaries_parser=_summaries_parser()
        ),
        neo4j_summary_adapter=_neo4j_pgpub_summary_adapter(driver=driver),
        neo4j_pgpub_search_adapter=_neo4j_pgpub_search_adapter(driver=driver),
        neo4j_pgpub_linking_adapter=_neo4j_pgpub_linking_adapter(driver=driver),
    )


def _neo4j_pgpub_search_adapter(driver: Driver) -> Neo4jPgpubSearchAdapter:
    return Neo4jPgpubSearchAdapter(driver=driver)


def _neo4j_pgpub_linking_adapter(driver: Driver) -> Neo4jPgpubLinkingAdapter:
    return Neo4jPgpubLinkingAdapter(driver=driver)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _neo4j_pgpub_summary_adapter(driver: Driver) -> Neo4jPgpubSummaryAdapter:
    return Neo4jPgpubSummaryAdapter(driver=driver)


def _summaries_parser() -> SummariesParser:
    return SummariesParser()


def _stored_summaries_loader(
    summaries_parser: SummariesParser,
) -> StoredSummariesLoader:
    return StoredSummariesLoader(summaries_parser=summaries_parser)


def _community_provider() -> CommunityProvider:
    return LeidenCommunityProvider()


def _community_summary_provider(
    model: BaseChatModel, max_workers=4
) -> CommunitySummaryProvider:
    return CommunitySummaryProvider(
        document_analyzer=_report_document_analyzer(
            model=model, max_workers=max_workers
        ),
        csv_mapper=_csv_mapper(),
    )


def _csv_mapper() -> CsvMapper:
    return CsvMapper()


def _triples_parser() -> TriplesParser:
    return TriplesParser()


def _graph_mapper() -> GraphMapper:
    return GraphMapper()


def _relationship_mapper() -> RelationshipMapper:
    return RelationshipMapper()


def _entity_mapper() -> EntityMapper:
    return EntityMapper()


def _extraction_document_analyzer(
    model: BaseChatModel, max_workers: int
) -> DocumentAnalyzer:
    input_params = [
        generate_knowlege_graph_extraction_input_params(""),
    ]
    return DocumentAnalyzer(
        model=model, input_params=input_params, max_workers=max_workers
    )


def _summary_document_analyzer(
    model: BaseChatModel, max_workers: int
) -> DocumentAnalyzer:
    return DocumentAnalyzer(
        model=model,
        input_params=[
            generate_knowlege_graph_summary_input_params(""),
        ],
        max_workers=max_workers,
    )


def _report_document_analyzer(
    model: BaseChatModel, max_workers: int
) -> DocumentAnalyzer:
    return DocumentAnalyzer(
        model=model,
        input_params=[
            generate_knowledge_graph_community_report_input_params(""),
        ],
        max_workers=max_workers,
    )


def _llm() -> BaseChatModel:
    return LlmChatFactory.openai_instance(model="chatgpt-4o-latest")


def stored_triples_loader() -> StoredTriplesLoader:
    return StoredTriplesLoader(
        entities_mapper=_entity_mapper(), relationship_mapper=_relationship_mapper()
    )
