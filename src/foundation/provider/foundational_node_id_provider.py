import logging

from annotation.timer_annotation import log_time
from foundation.infra.db.adapter.neo4j_foundational_node_adapter import (
    Neo4jFoundationalNodeAdapter,
)
from foundation.mapper.node_id_lookup_mapper import NodeIdLookupMapper
from foundation.model.node_id_lookup import NodeIdLookup


logger = logging.getLogger(__name__)


class FoundationalNodeIdProvider:
    """
    Query eugene graph for reacability and shortest paths
    """

    def __init__(
        self,
        neo4j_foundational_node_adapter: Neo4jFoundationalNodeAdapter,
        node_id_lookup_mapper: NodeIdLookupMapper,
    ):
        self.neo4j_foundational_node_adapter = neo4j_foundational_node_adapter
        self.node_id_lookup_mapper = node_id_lookup_mapper

    @log_time
    def find_node_id_by_node_name(
        self, value: str, fuzzy_match: bool = False
    ) -> NodeIdLookup:
        df = self.neo4j_foundational_node_adapter.find_node_id_by_node_name(
            value=value, fuzzy_match=fuzzy_match
        )

        return self.node_id_lookup_mapper.map(
            value=value, fuzzy_match=fuzzy_match, df=df
        )
