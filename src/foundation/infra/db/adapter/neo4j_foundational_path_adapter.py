import logging
from typing import Any

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
from pandas import DataFrame

from annotation.timer_annotation import log_time
from graph.util.util import ensure_connection
from foundation.model.reachability import Reachability

logger = logging.getLogger(__name__)


class Neo4jFoundationalPathAdapter:
    # the eugene graph is highly connected, keep this number to a minimum
    MAX_SUPPORTED_HOPS = 4
    TOP_N = 10

    """
    Adapter to search reachability and shortest path on a given eugene(genieve) graph node in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def find_shortest_path_by_start_id_and_end_id(
        self, start_id: str, end_id: str, n_hop: int = 2
    ) -> DataFrame | None:
        n_hop = self._ensure_valid_n_hop_size_or_throw(n_hop)
        ensure_connection(self.driver)
        return self._find_shortest_path(start_id=start_id, end_id=end_id, n_hop=n_hop)

    @log_time
    def find_is_reachable_by_start_id_and_end_id(
        self,
        start_id: str,
        end_id: str,
        n_hop: int = 2,
    ) -> Reachability:
        n_hop = self._ensure_valid_n_hop_size_or_throw(n_hop)
        ensure_connection(self.driver)
        is_reachable = self._find_is_reachable(
            start_id=start_id,
            end_id=end_id,
            n_hop=n_hop,
        )
        return Reachability(
            start_id=start_id, end_id=end_id, max_hop=n_hop, is_reachable=is_reachable
        )

    def _find_shortest_path(
        self, start_id: str, end_id: str | None, n_hop: int
    ) -> DataFrame | None:
        query = self._build_shortest_path_by_ids_query(n_hop)
        params = {"start_id": start_id, "end_id": end_id}
        return self._execute_query(query=query, params=params)

    def _find_is_reachable(
        self,
        start_id: str,
        end_id: str | None,
        n_hop: int,
    ) -> bool:
        query = self._build_reachability_by_ids_query(n_hop)
        params = {"start_id": start_id, "end_id": end_id}
        df = self._execute_query(query=query, params=params)
        if df is None:
            return False
        return bool(df["is_reachable"][0])

    def _execute_query(self, query: str, params: dict[str, Any]) -> DataFrame | None:
        logger.info(f"find all: {query} params: {params}")
        try:
            records = self.driver.execute_query(
                query_=query,
                parameters_=params,
                result_transformer_=neo4j.Result.to_df,
            )
            logger.info(f"cypher response: {records.shape}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_shortest_path_by_ids_query(self, n_hop: int) -> str:
        return """MATCH path = SHORTEST %s
        (startNode { node_id: $start_id })-[link]-{0,%s}(endNode { node_id: $end_id })
        RETURN [n in nodes(path) | n.node_id] AS paths
        """ % (
            Neo4jFoundationalPathAdapter.TOP_N,
            n_hop,
        )

    def _build_reachability_by_ids_query(self, n_hop: int) -> str:
        return """MATCH path = ANY
        (startNode { node_id: $start_id })-[link]-{0,%s}(endNode { node_id: $end_id })
        RETURN toBoolean(count(path)) as is_reachable
        """ % (
            n_hop,
        )

    def _ensure_valid_n_hop_size_or_throw(self, n_hop: int) -> int:
        n_hop = max(1, n_hop)
        max_supported_hops = Neo4jFoundationalPathAdapter.MAX_SUPPORTED_HOPS
        if n_hop > max_supported_hops:
            raise ValueError(
                "Request for N hop query of size {n_hop} exceeds max supported hops of {max_supported_hops}"
            )
        return n_hop
