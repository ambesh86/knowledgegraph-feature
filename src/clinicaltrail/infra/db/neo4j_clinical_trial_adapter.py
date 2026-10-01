import logging
from typing import Any

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from clinicaltrail.infra.db.const import CLINICAL_TRIAL_NODE_TYPE
from graph.util.util import ensure_connection

logger = logging.getLogger(__name__)


class Neo4jClinicalTrialAdapter:
    """
    Adapter to perform operations on the clinical trail nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_id_by_nct(self, nct: str) -> str | None:
        ensure_connection(self.driver)
        return self._find_node_id(nct)

    def _find_node_id(self, nct: str) -> str | None:
        query = self._build_find_by_nct_query(nct)
        logger.debug(f"query: {query} nct: {nct}")
        try:
            record = self.driver.execute_query(
                query_=query,
                parameters_={"nct_number": nct},
                database_=self.database,
                result_transformer_=neo4j.Result.single,
            )
            if record is None:
                return record
            node_id = str(record["node_id"])
            logger.debug(f"cypher response: {node_id}")
            return node_id
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise

    def _build_find_by_nct_query(self, nct: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
                WHERE n.nct_number = $nct_number
                RETURN n.node_id as node_id
            """ % (
            CLINICAL_TRIAL_NODE_TYPE
        )
        return lookup_node_query
