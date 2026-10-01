import logging

from neo4j import Driver
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory

from organization.infra.db.neo4j_organization_adapter import Neo4jOrganizationAdapter
from organization.infra.db.neo4j_organization_search_adapter import (
    Neo4jOrganizationSearchAdapter,
)


logger = logging.getLogger(__name__)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _organization_adapter(driver: Driver) -> Neo4jOrganizationAdapter:
    return Neo4jOrganizationAdapter(driver=driver)


def organization_adapter() -> Neo4jOrganizationAdapter:
    return _organization_adapter(driver=_neo4j_driver())


def _organization_search_adapter(driver: Driver) -> Neo4jOrganizationSearchAdapter:
    return Neo4jOrganizationSearchAdapter(driver=driver)


def organization_search_adapter() -> Neo4jOrganizationSearchAdapter:
    return _organization_search_adapter(driver=_neo4j_driver())
