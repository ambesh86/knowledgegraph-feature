import logging

from langchain_core.language_models import BaseChatModel
from neo4j import Driver

from document.analyze.document_analyzer import DocumentAnalyzer
from graph.analyze.graph_summary_orchestrator import GraphSummaryOrchestrator
from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import (
    CommunitySummaryProvider,
)
from graph.community.analyze.leiden_community_provider import LeidenCommunityProvider
from graph.community.analyze.summary_provider import SummaryProvider
from graph.community.mapper.csv_mapper import CsvMapper
from graph.graph_render import GraphRender
from graph.mapper.graph_mapper import GraphMapper
from graph.mapper.relationship_mapper import RelationshipMapper
from graph.mapper.triples_parser import TriplesParser
from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.summaries_parser import SummariesParser
from infra.llm.llm_chat_factory import LlmChatFactory
from infra.llm.prompt.generate import (
    generate_knowledge_graph_community_report_input_params,
    generate_knowlege_graph_extraction_input_params,
    generate_knowlege_graph_summary_input_params,
)
from graph.analyze.eugene_graph_summary_orchestrator import (
    EugeneGraphSummaryOrchestrator,
)
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from document.load.stored_summaries_loader import StoredSummariesLoader
from pubmed.infra.db.neo4j_article_adapter import Neo4jArticleAdapter
from pubmed.infra.db.neo4j_summary_adapter import Neo4jSummaryAdapter
from pubmed.mapper.article_mapper import ArticleMapper
from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from document.load.stored_triples_loader import StoredTriplesLoader

logger = logging.getLogger(__name__)


def graph_renderer() -> GraphRender:
    return GraphRender(_graph_mapper())


def graph_summary_orchestrator(max_workers: int = 4) -> GraphSummaryOrchestrator:
    model = _llm()
    return _graph_summary_orchestrator(
        graph_mapper=_graph_mapper(),
        triples_parser=_triples_parser(),
        extraction_document_analyzer=_extraction_document_analyzer(
            model=model, max_workers=max_workers
        ),
        relationship_mapper=_relationship_mapper(),
        entity_mapper=_entity_mapper(),
        csv_mapper=_csv_mapper(),
        summary_provider=_summary_provider(model=model, max_workers=max_workers),
        community_provider=_community_provider(),
        community_summary_provider=_community_summary_provider(
            model=model, max_workers=max_workers
        ),
    )


def _graph_summary_orchestrator(
    graph_mapper: GraphMapper,
    triples_parser: TriplesParser,
    relationship_mapper: RelationshipMapper,
    entity_mapper: EntityMapper,
    csv_mapper: CsvMapper,
    extraction_document_analyzer: DocumentAnalyzer,
    summary_provider: SummaryProvider,
    community_provider: CommunityProvider,
    community_summary_provider: CommunitySummaryProvider,
) -> GraphSummaryOrchestrator:
    return GraphSummaryOrchestrator(
        graph_mapper,
        triples_parser,
        extraction_document_analyzer,
        relationship_mapper,
        entity_mapper,
        csv_mapper,
        summary_provider,
        community_provider,
        community_summary_provider,
    )


def eugene_graph_summary_orchestrator(
    max_workers: int = 4,
) -> EugeneGraphSummaryOrchestrator:
    model = _llm()
    driver = _neo4j_driver()
    return _eugene_graph_summary_orchestrator(
        graph_mapper=_graph_mapper(),
        triples_parser=_triples_parser(),
        extraction_document_analyzer=_extraction_document_analyzer(
            model=model, max_workers=max_workers
        ),
        csv_mapper=_csv_mapper(),
        community_provider=_community_provider(),
        community_summary_provider=_community_summary_provider(
            model=model, max_workers=max_workers
        ),
        neo4j_article_adapter=_neo4j_article_adapter(driver=driver),
        neo4j_summary_adapter=_neo4j_summary_adapter(driver=driver),
        pubmed_fetch_provider=_pubmed_fetch_provider(article_mapper=_article_mapper()),
        stored_summaries_loader=_stored_summaries_loader(_summaries_parser()),
    )


def _eugene_graph_summary_orchestrator(
    graph_mapper: GraphMapper,
    triples_parser: TriplesParser,
    csv_mapper: CsvMapper,
    extraction_document_analyzer: DocumentAnalyzer,
    community_provider: CommunityProvider,
    community_summary_provider: CommunitySummaryProvider,
    neo4j_article_adapter: Neo4jArticleAdapter,
    neo4j_summary_adapter: Neo4jSummaryAdapter,
    pubmed_fetch_provider: PubmedFetchProvider,
    stored_summaries_loader: StoredSummariesLoader,
) -> EugeneGraphSummaryOrchestrator:
    return EugeneGraphSummaryOrchestrator(
        graph_mapper,
        triples_parser,
        extraction_document_analyzer,
        csv_mapper,
        community_provider,
        community_summary_provider,
        neo4j_article_adapter,
        neo4j_summary_adapter,
        pubmed_fetch_provider,
        stored_summaries_loader,
    )


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _neo4j_article_adapter(driver: Driver) -> Neo4jArticleAdapter:
    return Neo4jArticleAdapter(driver=driver)


def _neo4j_summary_adapter(driver: Driver) -> Neo4jSummaryAdapter:
    return Neo4jSummaryAdapter(driver=driver)


def _article_mapper() -> ArticleMapper:
    return ArticleMapper()


def _pubmed_fetch_provider(article_mapper: ArticleMapper) -> PubmedFetchProvider:
    return PubmedFetchProvider(article_mapper=article_mapper)


def _summary_provider(model: BaseChatModel, max_workers=4) -> SummaryProvider:
    return SummaryProvider(
        document_analyzer=_summary_document_analyzer(
            model=model, max_workers=max_workers
        )
    )


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
    # return LlmChatFactory.local_instance(model="deepseek-r1:70b")
    # return LlmChatFactory.bedrock_instance(model="us.meta.llama3-3-70b-instruct-v1:0")
    return LlmChatFactory.openai_instance(model="chatgpt-4o-latest")


def stored_triples_loader() -> StoredTriplesLoader:
    return StoredTriplesLoader(
        entities_mapper=_entity_mapper(), relationship_mapper=_relationship_mapper()
    )
