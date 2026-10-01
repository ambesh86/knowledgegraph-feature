import logging

from annotation.timer_annotation import log_time
from foundation.infra.db.adapter.neo4j_foundational_node_details_adapter import (
    Neo4jFoundationalNodeDetailsAdapter,
)
from foundation.mapper.node_details_mapper import NodeDetailsMapper
from foundation.model.generic_node_details import GenericNodeDetails


logger = logging.getLogger(__name__)


class FoundationalNodeDetailsProvider:
    """
    Query eugene graph for generic node details against non hidden nodes
    """

    def __init__(
        self,
        neo4j_foundational_node_details_adapter: Neo4jFoundationalNodeDetailsAdapter,
        node_details_mapper: NodeDetailsMapper,
    ):
        self.neo4j_foundational_node_details_adapter = (
            neo4j_foundational_node_details_adapter
        )
        self.node_details_mapper = node_details_mapper

    @log_time
    def find_node_details_by_node_ids(
        self, ids: set[str]
    ) -> list[GenericNodeDetails] | None:
        df = self.neo4j_foundational_node_details_adapter.find_node_details_by_node_ids(
            ids=ids
        )
        return self.node_details_mapper.map(df=df)
