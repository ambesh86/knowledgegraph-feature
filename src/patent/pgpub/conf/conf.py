import logging
import os

from neo4j import Driver

from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from patent.pgpub.provider.pgpub_metadata_provider import PgpubMetadataProvider
from patent.pgpub.provider.pgpub_provider import PgpubProvider
from patent.pgpub.mapper.pgpub_mapper import PgpubMapper
from patent.pgpub.mapper.pgpub_metadata_mapper import PgpubMetadataMapper
from patent.conf.conf import patent_application_api_key
from patent.pgpub.provider.pgpub_orchestrator import PgpubOrchestrator
from patent.pgpub.infra.embedding.pgpub_metadata_embedding_provider import (
    PgpubEmbeddingProvider,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_adapter import Neo4jPgpubAdapter
from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)
from patent.pgpub.conf.graphrag_conf import pgpub_knowledge_graph_analyzer


logger = logging.getLogger(__name__)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _neo4j_pgpub_adapter(driver: Driver) -> Neo4jPgpubAdapter:
    return Neo4jPgpubAdapter(driver)


def model_cache_dir() -> str | None:
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    return value


def pgpub_embedding_provider() -> PgpubEmbeddingProvider:
    return PgpubEmbeddingProvider(model_cache_dir=model_cache_dir())


def pgpub_metadata_mapper() -> PgpubMetadataMapper:
    return PgpubMetadataMapper()


def pgpub_mapper() -> PgpubMapper:
    return PgpubMapper()


def pgpub_provider() -> PgpubProvider:
    return _pgpub_provider(
        mapper=pgpub_mapper(),
        api_key=patent_application_api_key(),
    )


def _pgpub_provider(mapper: PgpubMapper, api_key: str) -> PgpubProvider:
    return PgpubProvider(pgpub_mapper=mapper, api_key=api_key)


def pgpub_metadata_provider() -> PgpubMetadataProvider:
    return _pgpub_metadata_provider(
        pgpub_metadata_mapper=pgpub_metadata_mapper(),
        api_key=patent_application_api_key(),
    )


def _pgpub_metadata_provider(
    pgpub_metadata_mapper: PgpubMetadataMapper, api_key: str
) -> PgpubMetadataProvider:
    return PgpubMetadataProvider(
        pgpub_metadata_mapper=pgpub_metadata_mapper, api_key=api_key
    )


def pgpub_orchestrator() -> PgpubOrchestrator:
    return _pgpub_orchestrator(
        pgpub_metadata_provider=pgpub_metadata_provider(),
        pgpub_provider=pgpub_provider(),
        pgpub_embedding_provider=pgpub_embedding_provider(),
        pgpub_adapter=_neo4j_pgpub_adapter(_neo4j_driver()),
    )


def _pgpub_orchestrator(
    pgpub_metadata_provider: PgpubMetadataProvider,
    pgpub_provider: PgpubProvider,
    pgpub_embedding_provider: PgpubEmbeddingProvider,
    pgpub_adapter: Neo4jPgpubAdapter,
) -> PgpubOrchestrator:
    return PgpubOrchestrator(
        pgpub_metadata_provider=pgpub_metadata_provider,
        pgpub_provider=pgpub_provider,
        pgpub_embedding_provider=pgpub_embedding_provider,
        pgpub_adapter=pgpub_adapter,
        pgpub_knowledge_graph_analyzer=pgpub_knowledge_graph_analyzer(),
    )


def neo4j_pgpub_search_adapter(driver: Driver) -> Neo4jPgpubSearchAdapter:
    return _neo4j_pgpub_search_adapter(driver=driver)


def _neo4j_pgpub_search_adapter(driver: Driver) -> Neo4jPgpubSearchAdapter:
    return Neo4jPgpubSearchAdapter(driver)
