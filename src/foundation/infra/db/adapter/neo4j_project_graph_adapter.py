import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import (
    _wrap_tx_with_arg,
    ensure_connection,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)

logger = logging.getLogger(__name__)


class Neo4jProjectGraphAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    This class is to project graphs in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def project_graph(
        self,
        projection_graph_name: str,
        node_labels: list[FoundationalNodeEnum],
        relationship_labels: list[FoundationalRelationshipEnum],
        node_properties: list[str],
        replace: bool = False,
    ) -> None:
        """
        project graph

        if replace is True then drop and project the graph
        """
        if projection_graph_name is None:
            raise ValueError("graph name is None")
        if node_labels is None:
            raise ValueError("node labels are None")
        if relationship_labels is None:
            raise ValueError("relationship labels are None")
        if node_properties is None:
            # todo: default to a star
            raise ValueError("node properties are None")
        ensure_connection(self.driver)

        if replace:
            self.drop_graph_if_exists(graph_name=projection_graph_name)

        projection_command = self._generate_cypher_template(
            projection_graph_name=projection_graph_name,
            node_labels=node_labels,
            relationship_labels=relationship_labels,
            node_properties=node_properties,
        )
        _wrap_tx_with_arg(
            driver=self.driver, callback=self._run_cypher, arg=projection_command
        )

    def drop_graph_if_exists(self, graph_name: str) -> None:
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                exists = self._does_graph_exist(tx=tx, graph_name=graph_name)
                if exists:
                    logger.info(f"dropping graph: {graph_name}")
                    self.drop_graph(graph_name)

    def drop_graph(
        self,
        graph_name: str,
    ) -> None:
        """
        drop a projected graph
        """
        if graph_name is None:
            raise ValueError("graph name is None")
        ensure_connection(self.driver)

        drop_command = self._generate_drop_graph(
            graph_name=graph_name,
        )
        _wrap_tx_with_arg(
            driver=self.driver, callback=self._run_cypher, arg=drop_command
        )

    def _does_graph_exist(self, tx: Transaction, graph_name: str) -> bool:
        command = self._generate_graph_exists_cypher(graph_name)
        try:
            record = tx.run(command, {}).single()

            if record is None:
                return False

            logger.info(f"command response: {record}")
            exists_dict = {
                "graphName": record["graphName"],
                "exists": bool(record["exists"]),
            }
            return exists_dict["exists"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", command, exception)
            logging.error("%s raised an error: \n%s", command, exception)
            raise exception

    def _run_cypher(self, tx: Transaction, command: str) -> dict[str, str] | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/
        if command is None:
            raise ValueError("command is None")

        logger.info(f"command: {command}")
        try:
            record = tx.run(command, {}).single()

            if record is None:
                return None

            logger.debug(f"command response: {record}")
            counts = {
                "graphName": record["graphName"],
                "nodeCount": record["nodeCount"],
                "relationshipCount": record["relationshipCount"],
            }
            logger.info(f"{counts}")
            return counts
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", command, exception)
            logging.error("%s raised an error: \n%s", command, exception)
            raise exception

    def _generate_cypher_template(
        self,
        projection_graph_name: str,
        node_labels: list[FoundationalNodeEnum],
        relationship_labels: list[FoundationalRelationshipEnum],
        node_properties: list[str],
    ) -> str:
        normalized_node_labels = [
            normalize_node_label(el.value[1]) for el in node_labels
        ]
        relationships = self._generate_relationships(relationship_labels)
        template = """
            call gds.graph.project(
                '%s',
                %s,
                {
                    %s
                },
                {
                    nodeProperties: %s
                }
            )
            yield graphName, nodeProjection, nodeCount, relationshipCount
            return graphName, nodeProjection, nodeCount, relationshipCount
        """ % (
            projection_graph_name,
            normalized_node_labels,
            relationships,
            node_properties,
        )
        return template

    def _generate_relationships(
        self, relationship_labels: list[FoundationalRelationshipEnum]
    ) -> str:
        rels = []
        for label in relationship_labels:
            relationships = "%s: {orientation: 'UNDIRECTED', type:'*'}" % label.value[1]
            rels.append(relationships)

        return ",\n\t\t\t\t".join(rels)

    def _generate_drop_graph(self, graph_name: str) -> str:
        return f"call gds.graph.drop('{graph_name}')"

    def _generate_graph_exists_cypher(self, graph_name: str) -> str:
        return f"call gds.graph.exists('{graph_name}')"
