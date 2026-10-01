import logging

from foundation.conf.const import (
    SIMILARITY_GRAPH_PROJECTION_NAME,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)
from foundation.infra.db.adapter.neo4j_project_similarity_graph_adapter import (
    Neo4jProjectSimilarityGraphAdapter,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class SimilaritySearchTrainOrchestrator:

    def __init__(
        self,
        neo4j_project_similarity_graph_adapter: Neo4jProjectSimilarityGraphAdapter,
    ):
        self.neo4j_project_similarity_graph_adapter = (
            neo4j_project_similarity_graph_adapter
        )

    @log_time
    def project_for_similarity_search(
        self,
    ) -> None:
        projection_graph_name = SIMILARITY_GRAPH_PROJECTION_NAME
        self._project_graph(projection_graph_name)

    def _project_graph(self, projection_graph_name: str) -> None:
        source_node_labels = [FoundationalNodeEnum.DISEASE, FoundationalNodeEnum.DRUG]
        target_node_labels = [
            FoundationalNodeEnum.ANATOMY,
            FoundationalNodeEnum.DISEASE,
            FoundationalNodeEnum.DRUG,
            FoundationalNodeEnum.EFFECT_PHENOTYPE,
            FoundationalNodeEnum.EXPOSURE,
            FoundationalNodeEnum.GENE_PROTEIN,
            FoundationalNodeEnum.PATHWAY,
        ]

        relationship_labels = [
            FoundationalRelationshipEnum.CONTRAINDICATION,
            FoundationalRelationshipEnum.DISEASE_PHENOTYPE_NEGATIVE,
            FoundationalRelationshipEnum.DISEASE_PHENOTYPE_POSITIVE,
            FoundationalRelationshipEnum.DISEASE_PROTEIN,
            FoundationalRelationshipEnum.EXPOSURE_DISEASE,
            FoundationalRelationshipEnum.INDICATION,
            FoundationalRelationshipEnum.OFF_LABEL_USE,
            FoundationalRelationshipEnum.PATHWAY_PATHWAY,
            FoundationalRelationshipEnum.PATHWAY_PROTEIN,
        ]

        logger.info(f"projecting graph {projection_graph_name}...")
        self.neo4j_project_similarity_graph_adapter.project_similarity_graph(
            projection_graph_name=projection_graph_name,
            source_node_labels=source_node_labels,
            target_node_labels=target_node_labels,
            relationship_labels=relationship_labels,
            replace=True,
        )
