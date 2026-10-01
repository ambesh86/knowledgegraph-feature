from neo4j import Driver

from foundation.infra.db.adapter.neo4j_project_graph_adapter import (
    Neo4jProjectGraphAdapter,
)
from foundation.infra.db.adapter.neo4j_train_embeddings_adapter import (
    Neo4jTrainEmbeddingsAdapter,
)
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from tpp.provider.tpp_patent_train_orchestrator import TppPatentTrainOrchestrator


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def neo4j_train_embeddings_adapter(driver: Driver) -> Neo4jTrainEmbeddingsAdapter:
    return Neo4jTrainEmbeddingsAdapter(driver=driver)


def neo4j_project_graph_adapter(
    driver: Driver,
) -> Neo4jProjectGraphAdapter:
    return Neo4jProjectGraphAdapter(driver=driver)


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
