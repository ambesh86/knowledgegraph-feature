import logging
from typing import Any

from neo4j import Driver, Transaction
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
from numpy import ndarray
import numpy

from graph.util.node_util import normalize_node_label
from graph.util.util import (
    ensure_connection,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum

logger = logging.getLogger(__name__)


class Neo4jMissingNodeIndexEmbeddingAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j

    namely to calculate default embeddings for the nodes with a missing node index
    All foundational nodes should have a node index.
    Nodes w/o index index are malformed and will be zeroed out.
    A default value is needed for the training steps.
    Only a few nodes are missing a node index field.
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def fix_embedding_by_common_labels(
        self, embedding_dimension: int | None = 256
    ) -> int:
        labels = [
            FoundationalNodeEnum.ANATOMY,
            FoundationalNodeEnum.BIOLOGICAL_PROCESS,
            FoundationalNodeEnum.CELLULAR_COMPONENT,
            FoundationalNodeEnum.DISEASE,
            FoundationalNodeEnum.DRUG,
            FoundationalNodeEnum.GENE_PROTEIN,
            FoundationalNodeEnum.MOLECULAR_FUNCTION,
            FoundationalNodeEnum.PATHWAY,
        ]
        normalized_labels = [normalize_node_label(el.value[1]) for el in labels]
        logger.info(
            f"zeroing embeddings for {len(normalized_labels)} node label type(s)"
        )
        return self.fix_embedding_by_missing_node_index(
            node_labels=normalized_labels, embedding_dimension=embedding_dimension
        )

    def fix_embedding_by_missing_node_index(
        self, node_labels: list[str], embedding_dimension: int | None
    ) -> int:
        """
        zero out embeddings

        return a list of node labels
        """
        if node_labels is None:
            raise ValueError(
                "Node lables are None. Cannot update embeddings for missing node index. Moving on..."
            )
            return

        if len(node_labels) == 0:
            return 0
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                return self._run_cypher(
                    tx=tx,
                    node_labels=node_labels,
                    embedding_dimension=embedding_dimension,
                )

    def _run_cypher(
        self, tx: Transaction, node_labels: list[str], embedding_dimension: int | None
    ) -> int:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/
        if node_labels is None or len(node_labels) == 0:
            return 0

        command = self._generate_cypher_template(node_labels=node_labels)
        embeddings = self._generate_default_embeddings(
            embedding_dimension=embedding_dimension
        )
        logger.info(f"command: {command}")
        logger.info(f"embedding dimension {len(embeddings)}")
        try:
            record = tx.run(
                command,
                {
                    "embeddings": embeddings,
                },
            ).single()

            if record is None:
                return 0

            logger.info(f"upsert response: {record}")
            return int(record["updated_node_count"])
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", command, exception)
            raise exception

    def _generate_cypher_template(self, node_labels: list[str]) -> str:
        labels = "|".join(node_labels)
        template = f"""
        MATCH (n:{labels})
        WHERE n.node_index IS NULL
        SET n.embeddings = $embeddings
        return count(n) as updated_node_count
        """
        return template

    def _generate_default_embeddings(
        self, embedding_dimension: int | None = 256
    ) -> ndarray:
        if embedding_dimension is None or embedding_dimension < 0:
            embedding_dimension = 256
        return numpy.zeros(embedding_dimension)
