import os
from neo4j import Driver

from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from infra.embedding.embedding_merger import EmbeddingMerger
from patent.pgpub.conf.conf import neo4j_pgpub_search_adapter
from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)
from foundation.infra.db.adapter.neo4j_project_graph_adapter import (
    Neo4jProjectGraphAdapter,
)
from foundation.infra.db.adapter.neo4j_train_embeddings_adapter import (
    Neo4jTrainEmbeddingsAdapter,
)
from foundation.infra.db.adapter.neo4j_project_similarity_graph_adapter import (
    Neo4jProjectSimilarityGraphAdapter,
)
from tpp.provider.similarity_search_train_orchestrator import (
    SimilaritySearchTrainOrchestrator,
)
from tpp.provider.tpp_patent_train_orchestrator import TppPatentTrainOrchestrator
from tpp.conf.graphrag_conf import tpp_knowledge_graph_analyzer
from tpp.infra.db.adapter.neo4j_tpp_search_adapter import Neo4jTppSearchAdapter
from tpp.provider.tpp_search_orchestrator import TppSearchOrchestrator
from tpp.infra.db.adapter.neo4j_tpp_adapter import Neo4jTppAdapter
from tpp.infra.embedding.tpp_embedding_provider import TppEmbeddingProvider
from tpp.provider.tpp_orchestrator import TppOrchestrator
from tpp.mapper.tpp_mapper import TppMapper


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def neo4j_tpp_adapter(driver: Driver) -> Neo4jTppAdapter:
    return Neo4jTppAdapter(driver)


def neo4j_tpp_search_adapter(driver: Driver) -> Neo4jTppSearchAdapter:
    return Neo4jTppSearchAdapter(driver=driver)


def neo4j_train_embeddings_adapter(driver: Driver) -> Neo4jTrainEmbeddingsAdapter:
    return Neo4jTrainEmbeddingsAdapter(driver=driver)


def neo4j_project_graph_adapter(
    driver: Driver,
) -> Neo4jProjectGraphAdapter:
    return Neo4jProjectGraphAdapter(driver=driver)


def neo4j_project_similarity_graph_adapter(
    driver: Driver,
) -> Neo4jProjectSimilarityGraphAdapter:
    return Neo4jProjectSimilarityGraphAdapter(driver=driver)


def tpp_mapper() -> TppMapper:
    return TppMapper()


def embedding_merger() -> EmbeddingMerger:
    return EmbeddingMerger()


def model_cache_dir() -> str | None:
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    return value


def tpp_embedding_provider(embedding_merger: EmbeddingMerger) -> TppEmbeddingProvider:
    return TppEmbeddingProvider(
        model_cache_dir=model_cache_dir(), embedding_merger=embedding_merger
    )


def tpp_orchestrator() -> TppOrchestrator:
    return _tpp_orchestrator(
        tpp_mapper=tpp_mapper(),
        tpp_embedding_provider=tpp_embedding_provider(
            embedding_merger=embedding_merger()
        ),
        neo4j_tpp_adapter=neo4j_tpp_adapter(_neo4j_driver()),
    )


def _tpp_orchestrator(
    tpp_mapper: TppMapper,
    tpp_embedding_provider: TppEmbeddingProvider,
    neo4j_tpp_adapter: Neo4jTppAdapter,
) -> TppOrchestrator:
    return TppOrchestrator(
        tpp_mapper=tpp_mapper,
        tpp_embedding_provider=tpp_embedding_provider,
        neo4j_tpp_adapter=neo4j_tpp_adapter,
        tpp_knowledge_graph_analyzer=tpp_knowledge_graph_analyzer(),
    )


def _tpp_search_orchestrator(
    neo4j_pgpub_search_adapter: Neo4jPgpubSearchAdapter,
    neo4j_tpp_search_adapter: Neo4jTppSearchAdapter,
) -> TppSearchOrchestrator:
    return TppSearchOrchestrator(
        neo4j_pgpub_search_adapter=neo4j_pgpub_search_adapter,
        neo4j_tpp_search_adapter=neo4j_tpp_search_adapter,
    )


def similarity_search_orchestrator() -> SimilaritySearchTrainOrchestrator:
    driver = _neo4j_driver()
    return _similarity_search_orchestrator(
        neo4j_project_similarity_graph_adapter=neo4j_project_similarity_graph_adapter(
            driver
        ),
    )


def _similarity_search_orchestrator(
    neo4j_project_similarity_graph_adapter: Neo4jProjectSimilarityGraphAdapter,
) -> SimilaritySearchTrainOrchestrator:
    return SimilaritySearchTrainOrchestrator(
        neo4j_project_similarity_graph_adapter=neo4j_project_similarity_graph_adapter,
    )


def tpp_search_orchestrator() -> TppSearchOrchestrator:
    driver = _neo4j_driver()
    return _tpp_search_orchestrator(
        neo4j_pgpub_search_adapter=neo4j_pgpub_search_adapter(driver),
        neo4j_tpp_search_adapter=neo4j_tpp_search_adapter(driver),
    )


def _tpp_patent_train_orchestrator(
    neo4j_train_embeddings_adapter: Neo4jTrainEmbeddingsAdapter,
    neo4j_project_graph_adapter: Neo4jProjectGraphAdapter,
) -> TppPatentTrainOrchestrator:
    return TppPatentTrainOrchestrator(
        neo4j_train_embeddings_adapter=neo4j_train_embeddings_adapter,
        neo4j_project_graph_adapter=neo4j_project_graph_adapter,
    )


def tpp_patent_train_orchestrator() -> TppPatentTrainOrchestrator:
    driver = _neo4j_driver()
    return _tpp_patent_train_orchestrator(
        neo4j_train_embeddings_adapter=neo4j_train_embeddings_adapter(driver),
        neo4j_project_graph_adapter=neo4j_project_graph_adapter(driver),
    )
