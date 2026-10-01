import logging

from pandas import DataFrame

from foundation.mapper.graph_mapper import GraphMapper
from foundation.infra.db.adapter.neo4j_foundational_n_hop_adapter import (
    Neo4jFoundationalNHopAdapter,
)
from foundation.model.graph.graph import Graph
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class FoundationalNHopProvider:
    MAX_RESULT_COUNT = 10_000
    MAX_RESULT_EXCEEDED_TMPL = (
        "Error result set attempted to return %s results which exceed the max of %s"
    )

    """
    Query eugene graph for one hop subgraph
    """

    def __init__(
        self,
        neo4j_foundational_n_hop_adapter: Neo4jFoundationalNHopAdapter,
        graph_mapper: GraphMapper,
    ):
        self.neo4j_foundational_n_hop_adapter = neo4j_foundational_n_hop_adapter
        self.graph_mapper = graph_mapper

    @log_time
    def find_subgraph_by_start_id(
        self,
        start_id: str,
        n_hop: int,
        page: int = 1,
        page_size: int = MAX_RESULT_COUNT,
    ) -> Graph | None:
        return self.find_subgraph_by_start_id_and_end_id(
            start_id=start_id, n_hop=n_hop, page=page, page_size=page_size
        )

    @log_time
    def find_subgraph_by_start_id_and_end_id(
        self,
        start_id: str,
        n_hop: int,
        page: int = 1,
        page_size: int = MAX_RESULT_COUNT,
        end_id: str | None = None,
    ) -> Graph | None:
        df = self.neo4j_foundational_n_hop_adapter.collect_by_start_id_and_end_id(
            start_id=start_id,
            end_id=end_id,
            n_hop=n_hop,
            page=page,
            page_size=page_size,
        )
        self._ensure_result_size_or_raise(df)
        return self.graph_mapper.map(df=df)

    @log_time
    def find_subgraph_by_start_value(
        self, start_value: str, n_hop: int
    ) -> Graph | None:
        return self.find_subgraph_by_start_value_and_end_value(
            start_value=start_value, n_hop=n_hop
        )

    @log_time
    def find_subgraph_by_start_value_and_end_value(
        self,
        start_value: str,
        n_hop: int,
        end_value: str | None = None,
    ) -> Graph | None:
        df = self.neo4j_foundational_n_hop_adapter.collect_by_start_value_and_end_value(
            start_value=start_value, end_value=end_value, n_hop=n_hop
        )
        self._ensure_result_size_or_raise(df)
        return self.graph_mapper.map(df=df)

    def _ensure_result_size_or_raise(self, df: DataFrame | None) -> None:
        if df is None:
            return
        max_result_count = FoundationalNHopProvider.MAX_RESULT_COUNT
        result_count = df.shape[0]
        if result_count > max_result_count:
            raise ValueError(
                FoundationalNHopProvider.MAX_RESULT_EXCEEDED_TMPL
                % (result_count, max_result_count)
            )
