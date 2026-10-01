import logging

from graph.analyze.summary_orchestrator import SummaryOrchestrator

from foundation.infra.embedding.foundational_node_embedding_provider import (
    FoundationalNodeEmbeddingProvider,
)
from foundation.infra.db.adapter.neo4j_foundational_node_adapter import (
    Neo4jFoundationalNodeAdapter,
)
from foundation.infra.db.adapter.neo4j_onehot_encoding_adapter import (
    Neo4jOnehotEncodingAdapter,
)
from foundation.infra.db.adapter.neo4j_missing_node_index_embedding_adapter import (
    Neo4jMissingNodeIndexEmbeddingAdapter,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class FoundationalNodeFixOrchestrator(SummaryOrchestrator):
    """
    Fix or update fields for foundational nodes related to the pubmed document graph
    """

    def __init__(
        self,
        foundational_node_embedding_provider: FoundationalNodeEmbeddingProvider,
        neo4j_foundational_node_adapter: Neo4jFoundationalNodeAdapter,
        neo4j_onehot_encoding_adapter: Neo4jOnehotEncodingAdapter,
        neo4j_missing_node_index_embedding_adapter: Neo4jMissingNodeIndexEmbeddingAdapter,
    ):

        self.foundational_node_embedding_provider = foundational_node_embedding_provider
        self.neo4j_foundational_node_adapter = neo4j_foundational_node_adapter
        self.neo4j_onehot_encoding_adapter = neo4j_onehot_encoding_adapter
        self.neo4j_missing_node_index_embedding_adapter = (
            neo4j_missing_node_index_embedding_adapter
        )

    @log_time
    def fix_all(self, labels: list[str]) -> None:
        if labels is None:
            return

        logger.info(f"fixing onehot encoding for {len(labels)} labels")
        self.neo4j_onehot_encoding_adapter.upsert_onehot_encodings(
            nodes_labels_to_update=labels
        )

        logger.info(f"fixing embeddings for nodes with missing node index fields")
        self.neo4j_missing_node_index_embedding_adapter.fix_embedding_by_common_labels()

        for label in labels:
            self.fix_all_nodes(label)
        logger.info(f"finished updating nodes for {labels}")

    def fix_all_nodes(self, label: str) -> None:
        logger.info(f"finding all node by label: {label}...")

        results = self.neo4j_foundational_node_adapter.find_all_by_label(label)
        if results is None:
            logger.warning(f"no results found for label {label}. skipping...")
            return

        num_results = len(results)
        logger.info(f"found {num_results} result(s) for label {label}")
        count = 0
        for row in results.to_dict("records"):
            self.fix_node(
                label=label,
                node_index=row["n.node_index"],
                node_name=row["n.node_name"],
            )
            count += 1
            if count % 1_000 == 0:
                logger.info(f"updated {label}, node count: {count}/{num_results}")
        logger.info(f"finished updating {label}, node count: {count}/{num_results}")

    def fix_node(self, label: str, node_index: str, node_name: str) -> None:
        """
        add embeddings to node label
        embeddings are needed on all nodes so the neo4j gds training can work across all nodes

        TODO: add one hot encoding
        TODO: better track all possible foundational graph label names
        """

        embeddings = self.foundational_node_embedding_provider.to_embedding(node_name)
        self.neo4j_foundational_node_adapter.upsert_embeddings(
            label=label, node_index=node_index, embeddings=embeddings
        )
        logger.debug(f"updated node_index:{node_index}")
