import logging

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection

logger = logging.getLogger(__name__)


class Neo4jFoundationalNodeCountAdapter:
    """
    Adapter to perform count operations on eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def count_all_by_label(self, label: str) -> int:
        ensure_connection(self.driver)
        return self._count_all_by_label(label)

    def _count_all_by_label(self, label: str) -> int:
        query = self._build_count_all_by_label(label)
        logger.info(f"count all: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.info(f"cypher response: {record}")
            return record["count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_all_by_label(self, label: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
            RETURN count(n) as count
            """ % (
            label,
            # normalize_node_label(label),
        )
        return lookup_node_query
