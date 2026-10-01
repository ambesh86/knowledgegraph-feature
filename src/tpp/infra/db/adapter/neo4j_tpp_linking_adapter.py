import logging

from neo4j import Driver
from graph.infra.db.neo4j_graphrag_linking_adapter import (
    Neo4jGraphragLinkingAdapter,
)
from tpp.infra.db.const import TPP_NODE_PRIMARY_KEY, TPP_NODE_TYPE

logger = logging.getLogger(__name__)


class Neo4jTppLinkingAdapter(Neo4jGraphragLinkingAdapter):

    def __init__(self, driver: Driver):
        super().__init__(driver=driver)

    def link_node(
        self,
        source_primary_key: str | int,
        target_node_index: str,
    ) -> str | None:
        return self.link_publication_node(
            source_node_label=TPP_NODE_TYPE,
            source_primary_key_label=TPP_NODE_PRIMARY_KEY,
            source_primary_key=source_primary_key,
            target_node_index=target_node_index,
        )
