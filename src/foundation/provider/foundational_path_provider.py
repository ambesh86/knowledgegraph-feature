import logging

from annotation.timer_annotation import log_time
from foundation.infra.db.adapter.neo4j_foundational_path_adapter import (
    Neo4jFoundationalPathAdapter,
)
from foundation.model.shortest_paths import ShortestPaths
from foundation.model.reachability import Reachability


logger = logging.getLogger(__name__)


class FoundationalPathProvider:
    """
    Query eugene graph for reacability and shortest paths
    """

    def __init__(
        self,
        neo4j_foundational_path_adapter: Neo4jFoundationalPathAdapter,
    ):
        self.neo4j_foundational_path_adapter = neo4j_foundational_path_adapter

    @log_time
    def find_shortest_path_by_start_id_and_end_id(
        self, start_id: str, end_id: str, n_hop: int
    ) -> ShortestPaths:
        df = self.neo4j_foundational_path_adapter.find_shortest_path_by_start_id_and_end_id(
            start_id=start_id, end_id=end_id, n_hop=n_hop
        )
        if df is None:
            return ShortestPaths(
                start_id=start_id,
                end_id=end_id,
                max_hop=n_hop,
                count=0,
                paths=(),
            )

        paths = df["paths"].tolist()
        shortest_paths = []
        for path in paths:
            shortest_paths.append(tuple(path))

        return ShortestPaths(
            start_id=start_id,
            end_id=end_id,
            max_hop=n_hop,
            count=len(paths),
            paths=tuple(shortest_paths),
        )

    @log_time
    def find_is_reachable_by_start_id_and_end_id(
        self, start_id: str, end_id: str, n_hop: int
    ) -> Reachability:
        return self.neo4j_foundational_path_adapter.find_is_reachable_by_start_id_and_end_id(
            start_id=start_id, end_id=end_id, n_hop=n_hop
        )
