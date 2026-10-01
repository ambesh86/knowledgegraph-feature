import logging
import os
import requests

from neo4j import Driver
from huggingface_hub import configure_http_backend

from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)
from infra.embedding.embedding_merger import EmbeddingMerger
from infra.embedding.semantic_search_embedding_provider import (
    SemanticSearchEmbeddingProvider,
)
from tpp.infra.db.adapter.neo4j_tpp_search_adapter import Neo4jTppSearchAdapter
from tpp.provider.tpp_search_orchestrator import TppSearchOrchestrator

logger = logging.getLogger(__name__)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _neo4j_tpp_search_adapter(driver: Driver) -> Neo4jTppSearchAdapter:
    return Neo4jTppSearchAdapter(driver=driver)


def _neo4j_pgpub_search_adapter(driver: Driver) -> Neo4jPgpubSearchAdapter:
    return Neo4jPgpubSearchAdapter(driver)


def embedding_merger() -> EmbeddingMerger:
    return EmbeddingMerger()


def model_cache_dir() -> str | None:
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    return value


def semantic_search_embedding_provider() -> SemanticSearchEmbeddingProvider:
    return _semantic_search_embedding_provider(embedding_merger=embedding_merger())


def _semantic_search_embedding_provider(
    embedding_merger: EmbeddingMerger,
) -> SemanticSearchEmbeddingProvider:
    return SemanticSearchEmbeddingProvider(
        embedding_merger, model_cache_dir=model_cache_dir()
    )


def _tpp_search_orchestrator(
    neo4j_pgpub_search_adapter: Neo4jPgpubSearchAdapter,
    neo4j_tpp_search_adapter: Neo4jTppSearchAdapter,
) -> TppSearchOrchestrator:
    return TppSearchOrchestrator(
        neo4j_pgpub_search_adapter=neo4j_pgpub_search_adapter,
        neo4j_tpp_search_adapter=neo4j_tpp_search_adapter,
    )


def tpp_search_orchestrator() -> TppSearchOrchestrator:
    driver = _neo4j_driver()
    return _tpp_search_orchestrator(
        neo4j_pgpub_search_adapter=_neo4j_pgpub_search_adapter(driver),
        neo4j_tpp_search_adapter=_neo4j_tpp_search_adapter(driver),
    )


def backend_factory() -> requests.Session:
    """
    to fix the ssl error while downloading the model when running in ecs
    todo: find a better fix for the model download
    """
    logger.warning(
        f"WARNING!!!! Ignoring session requests TLS certificate verification. This is a fix for the huggingface download while running in ECS"
    )
    session = requests.Session()
    session.verify = False
    return session
