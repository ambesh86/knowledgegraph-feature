import logging
from typing import Any

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
from pandas import DataFrame

from graph.util.util import ensure_connection
from foundation.infra.db.util.pagination import Pagination
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class Neo4jFoundationalNHopAdapter:
    # the eugene graph is highly connected
    # a sufficient number of hops causes the entire graph to return
    MAX_SUPPORTED_HOPS = 2

    """
    Adapter to collect N relationships on a given eugene(genieve) graph node in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def collect_by_start_id(
        self, start_id: str, page: int, page_size: int, n_hop: int = 2
    ) -> DataFrame | None:
        return self.collect_by_start_id_and_end_id(
            start_id=start_id, n_hop=n_hop, page=page, page_size=page_size
        )

    @log_time
    def collect_by_start_id_and_end_id(
        self,
        start_id: str,
        page: int,
        page_size: int,
        end_id: str | None = None,
        n_hop: int = 2,
    ) -> DataFrame | None:
        n_hop = self._ensure_valid_n_hop_size_or_throw(n_hop)
        ensure_connection(self.driver)
        return self._collect_n_hop_by_id(
            start_id=start_id,
            end_id=end_id,
            n_hop=n_hop,
            page=page,
            page_size=page_size,
        )

    @log_time
    def collect_by_start_value(
        self, start_value: str, n_hop: int = 2
    ) -> DataFrame | None:
        return self.collect_by_start_value_and_end_value(
            start_value=start_value, n_hop=n_hop
        )

    @log_time
    def collect_by_start_value_and_end_value(
        self,
        start_value: str,
        end_value: str | None = None,
        n_hop: int = 2,
    ) -> DataFrame | None:
        n_hop = self._ensure_valid_n_hop_size_or_throw(n_hop)
        ensure_connection(self.driver)
        return self._collect_n_hop_by_value(
            start_value=start_value, n_hop=n_hop, end_value=end_value
        )

    def _collect_n_hop_by_id(
        self,
        start_id: str,
        page: int,
        page_size: int,
        end_id: str | None,
        n_hop: int,
    ) -> DataFrame | None:
        include_end_name = True if end_id is not None else False
        query = self._build_n_hop_by_id_query(
            n_hop=n_hop,
            include_end_condition=include_end_name,
            page=page,
            page_size=page_size,
        )
        params = {"start_id": start_id}
        if end_id is not None:
            params["end_id"] = end_id
        return self._collect_n_hop(query=query, params=params)

    def _collect_n_hop_by_value(
        self,
        start_value: str,
        end_value: str | None,
        n_hop: int,
    ) -> DataFrame | None:
        include_end_name = True if end_value is not None else False
        query = self._build_n_hop_by_value_query(
            n_hop=n_hop, include_end_condition=include_end_name
        )
        params = {"start_name": start_value}
        if end_value is not None:
            params["end_name"] = end_value
        return self._collect_n_hop(query=query, params=params)

    def _collect_n_hop(self, query: str, params: dict[str, Any]) -> DataFrame | None:
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

    def _build_n_hop_by_value_query(
        self, n_hop: int, include_end_condition: bool = False
    ) -> str:
        return """
            MATCH (startNode { node_name: $start_name })-[r]-{0,%s}(endNode%s)
            %s
            """ % (
            n_hop,
            "{ node_name: $end_name }" if include_end_condition else "",
            self._gen_n_hop_snippet(),
        )

    def _build_n_hop_by_id_query(
        self, n_hop: int, page: int, page_size: int, include_end_condition: bool = False
    ) -> str:
        return """MATCH (startNode { node_id: $start_id })-[r]-{0,%s}(endNode%s)
            %s
            """ % (
            n_hop,
            "{ node_id: $end_id }" if include_end_condition else "",
            self._gen_n_hop_snippet(page, page_size),
        )

    def _ensure_valid_n_hop_size_or_throw(self, n_hop: int) -> int:
        n_hop = max(1, n_hop)
        max_supported_hops = Neo4jFoundationalNHopAdapter.MAX_SUPPORTED_HOPS
        if n_hop > max_supported_hops:
            raise ValueError(
                "Request for N hop query of size {n_hop} exceeds max supported hops of {max_supported_hops}"
            )
        return n_hop

    def _gen_n_hop_snippet(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(page, page_size)
        return """UNWIND(r) AS rel
            RETURN DISTINCT startNode(rel).node_name as startName, toStringOrNull(startNode(rel).node_id) as startId, 
                labels(startNode(rel)) as startLabels, endNode(rel).node_name as endName, toStringOrNull(endNode(rel).node_id) as endId,  
                labels(endNode(rel)) as endLabels, type(rel) as relType
            ORDER BY startName
            SKIP %s
            LIMIT %s
        """ % (
            offset,
            limit,
        )
