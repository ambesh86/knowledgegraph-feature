import logging

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
import pandas as pd

from graph.util.util import ensure_connection

logger = logging.getLogger(__name__)


class Neo4jFoundationalNodeDetailsAdapter:
    MAX_QUERY_IDS = 50
    """
    Adapter to return generic node details from nodes in the eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_details_by_node_ids(self, ids: set[str]) -> pd.DataFrame | None:
        if ids is None or len(ids) == 0:
            return None
        self._ensure_query_limit_or_raise(ids=ids)
        ensure_connection(self.driver)
        return self._find_node_details_by_node_ids(
            ids=ids,
        )

    def _find_node_details_by_node_ids(
        self,
        ids: set[str],
    ) -> pd.DataFrame | None:
        query = self._build_find_node_details_by_node_ids()
        params = {"node_ids": list(ids)}
        logger.info(f"find node details query: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                parameters_=params,
                result_transformer_=neo4j.Result.to_df,
            )
            if records is None:
                return None
            logger.debug(f"cypher response: {records.shape}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_find_node_details_by_node_ids(self) -> str:
        lookup_node_query = """MATCH (n)
        WHERE (n.is_hidden IS NULL OR NOT n.is_hidden) and n.node_id in $node_ids
        RETURN labels(n) as labels, n.node_id as id, n.node_name as value,
            n.node_source as source, n.description as description
            """
        return lookup_node_query

    def _ensure_query_limit_or_raise(self, ids: set[str]) -> None:
        if ids is None:
            return
        max_query_ids = Neo4jFoundationalNodeDetailsAdapter.MAX_QUERY_IDS
        num_ids = len(ids)
        if num_ids > max_query_ids:
            raise ValueError(
                f"{num_ids} ids given for query, max ids are {max_query_ids}"
            )
