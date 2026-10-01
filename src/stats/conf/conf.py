from neo4j import Driver

from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory

from stats.infra.db.adapter.neo4j_database_stats_adapter import (
    Neo4jDatabaseStatsAdapter,
)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def neo4j_database_stats_adapter() -> Neo4jDatabaseStatsAdapter:
    return Neo4jDatabaseStatsAdapter(driver=_neo4j_driver())
