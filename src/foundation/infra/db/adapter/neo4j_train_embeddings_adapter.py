import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import (
    _wrap_tx_with_arg,
    ensure_connection,
)

logger = logging.getLogger(__name__)


class Neo4jTrainEmbeddingsAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    This class is to train graph embeddings in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def train_fastrp_with_write(
        self,
        projection_graph_name: str,
        embeddings_dimension: int | None = 512,
    ) -> None:
        """
        train graph embedding using the fastrp method in the graph datascience (gds) package

        if replace is True then drop and project the graph
        """
        if projection_graph_name is None:
            raise ValueError("graph name is None")
        ensure_connection(self.driver)

        train_command = self._generate_cypher_template(
            projection_graph_name=projection_graph_name,
            node_properties=["embeddings", "label_one_hot_encoding"],
            embeddings_dimensions=embeddings_dimension,
        )
        _wrap_tx_with_arg(
            driver=self.driver, callback=self._run_cypher, arg=train_command
        )

    def create_embedding_index(
        self,
        node_label: str,
        property_name: str,
        embeddings_dimension: int | None = 512,
    ) -> None:
        """
        build embedding index
        """
        if node_label is None:
            raise ValueError("node label is None")
        if property_name is None:
            raise ValueError("property name is None")
        ensure_connection(self.driver)

        command = self._generate_create_index_cypher(
            node_label=node_label,
            property_name=property_name,
            embeddings_dimension=embeddings_dimension,
        )
        _wrap_tx_with_arg(driver=self.driver, callback=self._run_cypher, arg=command)

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

            logger.info(f"command response: {record}")
            counts = {
                "nodes": record["nodePropertiesWritten"],
            }
            return counts
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", command, exception)
            logging.error("%s raised an error: \n%s", command, exception)
            raise exception

    def _generate_cypher_template(
        self,
        projection_graph_name: str,
        node_properties: list[str],
        embeddings_dimensions: int | None = 512,
        write_field: str | None = "prediction_embeddings",
    ) -> str:
        template = """
            call gds.fastRP.write(
            '%s',
            {
                embeddingDimension: %s,
                writeProperty: '%s',
                iterationWeights: [0, .6, .8],
                normalizationStrength: -0.5,
                randomSeed: 75,
                featureProperties: %s,
                propertyRatio: .50
            }
            )
            yield nodePropertiesWritten
        """ % (
            projection_graph_name,
            embeddings_dimensions,
            write_field,
            node_properties,
        )
        return template

    def _generate_create_index_cypher(
        self,
        node_label: str,
        property_name: str,
        embeddings_dimension: int | None = 512,
    ) -> str:
        return """
        CREATE VECTOR INDEX %s_%s_index IF NOT EXISTS
            FOR (n:%s)
            ON n.%s
            OPTIONS { indexConfig: {
                `vector.dimensions`: %s,
                `vector.similarity_function`: 'cosine'
            }
        }
        """ % (
            node_label,
            property_name,
            node_label,
            property_name,
            embeddings_dimension,
        )
