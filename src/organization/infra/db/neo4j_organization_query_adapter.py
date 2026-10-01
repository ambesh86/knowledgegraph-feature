import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection, get_or_default
from organization.model.organization_node_enum import OrganizationNodeEnum

logger = logging.getLogger(__name__)


class Neo4jOrganizationQueryAdapter:
    """
    @deprecated This class queries an old schema of the organization names

    Adapter to query organization names found for eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_aliases_by_name(self, organization: str) -> list[str]:
        ensure_connection(self.driver)

        logger.info(f"searching for organization aliases. organization: {organization}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                aliases = self._find_aliases_by_name(tx=tx, organization=organization)
                logger.info(
                    f"found {len(aliases)} alias(es) for organization {organization}"
                )
                return aliases

    def _find_aliases_by_name(self, tx: Transaction, organization: str) -> list[str]:
        search = self._generate_search()
        params = {"organization_name": organization}
        logger.debug(f"search: {search}")
        logger.debug(f"params: {params}")
        try:
            record = tx.run(
                search,
                params,
            ).single()
            logger.info(f"cypher response: {record}")

            if record is None:
                return []

            return record[f"aliases"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_search(self) -> str:
        return """
        OPTIONAL MATCH (o:`%s`)
        WHERE o.organization_name = $organization_name AND (n.is_hidden IS NULL OR NOT n.is_hidden)
        WITH o.organization_id as org_id
        OPTIONAL MATCH (o:`%s`)
        WHERE o.organization_id = org_id
        RETURN DISTINCT toStringOrNull(org.node_id) as org_id, toStringOrNull(org.organization_name) as org_name
        """.strip() % (
            OrganizationNodeEnum.ORGANIZATION_V2.value[1],
            OrganizationNodeEnum.ORGANIZATION_V2.value[1],
        )
