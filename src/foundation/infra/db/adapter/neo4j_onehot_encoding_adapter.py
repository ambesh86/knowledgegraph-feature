import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import (
    _wrap_tx_with_arg,
    ensure_connection,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum

logger = logging.getLogger(__name__)


class Neo4jOnehotEncodingAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    namely to calculate and apply one hot encoding
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert_onehot_encodings(
        self, nodes_labels_to_update: list[str] | None = None
    ) -> list[str]:
        """
        apply onehot encoding for all known nodes in the graph

        return a list of node labels
        """
        ensure_connection(self.driver)

        all_node_labels = self._node_labels()
        if nodes_labels_to_update is None:
            nodes_labels_to_update = all_node_labels
        commands = self._generate_commands(
            node_labels=all_node_labels, nodes_to_generate=nodes_labels_to_update
        )
        for command in commands:
            _wrap_tx_with_arg(
                driver=self.driver, callback=self._run_cypher, arg=command
            )

        return nodes_labels_to_update

    def _run_cypher(self, tx: Transaction, command: str) -> None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/
        if command is None:
            return

        logger.info(f"command: {command}")
        try:
            record = self.driver.execute_query(command, {})

            if record is None:
                return None

            logger.debug(f"upsert response: {record}")
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", command, exception)
            raise exception

    def _node_labels(self) -> list[str]:
        return [
            normalize_node_label(el.value[1])
            for el in FoundationalNodeEnum
            if el.value[0] > 0
        ]

    def _generate_commands(
        self, node_labels: list[str], nodes_to_generate: list[str] | None = None
    ) -> list[str]:
        """
        generate commands to update every given label with it a new one hot encoding
        the onehot encoding needs to know the complete list of nodes given in the node_labels field

        returns list of cypher commands
        """

        if nodes_to_generate is None:
            nodes_to_generate = node_labels
        template = self._generate_cypher_template(node_labels=node_labels)
        commands = []
        for label in node_labels:
            normalized_label = normalize_node_label(label)
            command = template % (normalized_label, normalized_label)
            commands.append(command)

        return commands

    def _generate_cypher_template(self, node_labels: list[str]) -> str:
        template = f"""
            MATCH (n1:`%s`)
            WITH n1, gds.alpha.ml.oneHotEncoding(
            {node_labels}
            , ['%s']) AS encoding
            CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
            YIELD node
            RETURN node;
        """
        return template
