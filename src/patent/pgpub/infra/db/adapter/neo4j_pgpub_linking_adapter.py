import logging

from neo4j import Driver
from graph.infra.db.neo4j_graphrag_linking_adapter import (
    Neo4jGraphragLinkingAdapter,
)
from patent.pgpub.infra.db.const import (
    USPTO_PGPUB_NODE_PRIMARY_KEY,
    USPTO_PGPUB_NODE_TYPE,
)

logger = logging.getLogger(__name__)


class Neo4jPgpubLinkingAdapter(Neo4jGraphragLinkingAdapter):

    def __init__(self, driver: Driver):
        super().__init__(driver=driver)

    def link_pgpub_node(
        self,
        source_primary_key: str | int,
        target_node_index: str,
    ) -> str | None:
        return self.link_publication_node(
            source_node_label=USPTO_PGPUB_NODE_TYPE,
            source_primary_key_label=USPTO_PGPUB_NODE_PRIMARY_KEY,
            source_primary_key=source_primary_key,
            target_node_index=target_node_index,
        )
