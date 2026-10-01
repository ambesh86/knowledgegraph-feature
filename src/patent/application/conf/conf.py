import logging

from neo4j import Driver

from patent.application.provider.application_provider import ApplicationProvider
from patent.application.mapper.application_mapper import ApplicationMapper
from patent.application.infra.db.neo4j_application_adapter import (
    Neo4jApplicationAdapter,
)
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from patent.application.provider.application_orchestrator import ApplicationOrchestator
from patent.conf.conf import patent_application_api_key


logger = logging.getLogger(__name__)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def application_adapter(driver: Driver) -> Neo4jApplicationAdapter:
    return Neo4jApplicationAdapter(driver=driver)


def application_mapper() -> ApplicationMapper:
    return ApplicationMapper()


def application_provider() -> ApplicationProvider:
    api_key = patent_application_api_key()
    mapper = application_mapper()
    return ApplicationProvider(application_mapper=mapper, api_key=api_key)


def application_orchestrator() -> ApplicationOrchestator:
    return _application_orchestrator(
        application_provider=application_provider(),
        application_adapter=application_adapter(_neo4j_driver()),
    )


def _application_orchestrator(
    application_provider: ApplicationProvider,
    application_adapter: Neo4jApplicationAdapter,
) -> ApplicationOrchestator:
    return ApplicationOrchestator(
        application_adapter=application_adapter,
        application_provider=application_provider,
    )
