import logging
from typing import Any

from neo4j import Driver

from graph.util.node_util import normalize_node_label
from graph.util.util import (
    _wrap_tx_with_arg,
    ensure_connection,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)
from foundation.infra.db.adapter.neo4j_project_graph_adapter import (
    Neo4jProjectGraphAdapter,
)

logger = logging.getLogger(__name__)


class Neo4jProjectSimilarityGraphAdapter(Neo4jProjectGraphAdapter):
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    This class is to project graphs in neo4j specifically for the similarity query
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        super().__init__(driver=driver, database=database)

    def project_similarity_graph(
        self,
        projection_graph_name: str,
        source_node_labels: list[FoundationalNodeEnum],
        target_node_labels: list[FoundationalNodeEnum],
        relationship_labels: list[FoundationalRelationshipEnum],
        replace: bool = False,
    ) -> None:
        """
        project graph

        if replace is True then drop and project the graph
        """
        if projection_graph_name is None:
            raise ValueError("graph name is None")
        if source_node_labels is None:
            raise ValueError("source node labels are None")
        if target_node_labels is None:
            raise ValueError("target node labels are None")
        if relationship_labels is None:
            raise ValueError("relationship labels are None")
        ensure_connection(self.driver)

        if replace:
            self.drop_graph_if_exists(graph_name=projection_graph_name)

        projection_command = self._generate_cypher_template(
            projection_graph_name=projection_graph_name,
            source_node_labels=source_node_labels,
            target_node_labels=target_node_labels,
            relationship_labels=relationship_labels,
        )
        logger.info(f"projection: {projection_command}")
        _wrap_tx_with_arg(
            driver=self.driver, callback=self._run_cypher, arg=projection_command
        )

    def _generate_cypher_template(
        self,
        projection_graph_name: str,
        source_node_labels: list[FoundationalNodeEnum],
        target_node_labels: list[FoundationalNodeEnum],
        relationship_labels: list[FoundationalRelationshipEnum],
    ) -> str:
        join_char = "|"
        normalized_source_node_labels = join_char.join(
            [normalize_node_label(el.value[1]) for el in source_node_labels]
        )
        normalized_target_node_labels = join_char.join(
            [normalize_node_label(el.value[1]) for el in target_node_labels]
        )
        escaped_relationship_labels = join_char.join(
            [self._escape_label(el.value[1]) for el in relationship_labels]
        )
        template = """
            MATCH (source:%s)
            OPTIONAL MATCH (source)-[r:%s]-(target:%s)
            RETURN gds.graph.project(
                '%s',
                source,
                target,
                { 
                    relationshipProperties: r { strength: 1 } 
                }
            )
        """ % (
            normalized_source_node_labels,
            escaped_relationship_labels,
            normalized_target_node_labels,
            projection_graph_name,
        )
        return template

    def _escape_label(self, label: str) -> str:
        return f"`{label}`"
