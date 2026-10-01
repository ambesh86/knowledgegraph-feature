import logging

from foundation.infra.db.adapter.neo4j_train_embeddings_adapter import (
    Neo4jTrainEmbeddingsAdapter,
)
from foundation.conf.const import GRAPH_PROJECTION_NAME
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)
from foundation.infra.db.adapter.neo4j_project_graph_adapter import (
    Neo4jProjectGraphAdapter,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class TppPatentTrainOrchestrator:

    def __init__(
        self,
        neo4j_train_embeddings_adapter: Neo4jTrainEmbeddingsAdapter,
        neo4j_project_graph_adapter: Neo4jProjectGraphAdapter,
    ):
        self.neo4j_train_embeddings_adapter = neo4j_train_embeddings_adapter
        self.neo4j_project_graph_adapter = neo4j_project_graph_adapter

    @log_time
    def train_for_search(
        self,
        embedding_dimension: int = 512,
    ) -> None:
        projection_graph_name = GRAPH_PROJECTION_NAME
        self._project_graph(projection_graph_name)
        self._train(
            projection_graph_name=projection_graph_name,
            embedding_dimension=embedding_dimension,
        )
        self._create_indexes(
            projection_graph_name=projection_graph_name,
            embedding_dimension=embedding_dimension,
        )

    def _project_graph(self, projection_graph_name: str) -> None:
        nodes_labels = [
            FoundationalNodeEnum.ANATOMY,
            FoundationalNodeEnum.BIOLOGICAL_PROCESS,
            FoundationalNodeEnum.CELLULAR_COMPONENT,
            FoundationalNodeEnum.CSL_TPP,
            FoundationalNodeEnum.DISEASE,
            FoundationalNodeEnum.DRUG,
            FoundationalNodeEnum.GENE_PROTEIN,
            FoundationalNodeEnum.MOLECULAR_FUNCTION,
            FoundationalNodeEnum.PATHWAY,
            FoundationalNodeEnum.USPTO_PGPUB,
        ]
        relationship_labels = [
            FoundationalRelationshipEnum.HAS_PUBLICATION,
            FoundationalRelationshipEnum.ANATOMY_PROTEIN_ABSENT,
            FoundationalRelationshipEnum.ANATOMY_PROTEIN_PRESENT,
            FoundationalRelationshipEnum.BIOPROCESS_BIOPROCESS,
            FoundationalRelationshipEnum.CONTRAINDICATION,
            FoundationalRelationshipEnum.CELLCOMP_CELLCOMP,
            FoundationalRelationshipEnum.DISEASE_DISEASE,
            FoundationalRelationshipEnum.DISEASE_PROTEIN,
            FoundationalRelationshipEnum.DRUG_PROTEIN,
            FoundationalRelationshipEnum.DRUG_DRUG,
            FoundationalRelationshipEnum.DRUG_EFFECT,
            FoundationalRelationshipEnum.PROTEIN_PROTEIN,
            FoundationalRelationshipEnum.PATHWAY_PATHWAY,
            FoundationalRelationshipEnum.INDICATION,
            FoundationalRelationshipEnum.MOLFUNC_MOLFUNC,
        ]
        node_properties = ["embeddings", "label_one_hot_encoding"]

        logger.info(f"projecting graph {projection_graph_name}...")
        self.neo4j_project_graph_adapter.project_graph(
            projection_graph_name=projection_graph_name,
            node_labels=nodes_labels,
            relationship_labels=relationship_labels,
            node_properties=node_properties,
            replace=True,
        )

    def _train(self, projection_graph_name: str, embedding_dimension: int) -> None:
        logger.info(f"training graph embeddings for {projection_graph_name}...")
        self.neo4j_train_embeddings_adapter.train_fastrp_with_write(
            projection_graph_name=projection_graph_name,
            embeddings_dimension=embedding_dimension,
        )

    def _create_indexes(
        self, projection_graph_name: str, embedding_dimension: int
    ) -> None:
        embedding_property = "prediction_embeddings"
        csl_tpp_label = FoundationalNodeEnum.CSL_TPP.value[1]
        logger.info(
            f"create embeddings index for {projection_graph_name} label: {csl_tpp_label} embedding dimension: {embedding_dimension}..."
        )
        self.neo4j_train_embeddings_adapter.create_embedding_index(
            node_label=csl_tpp_label,
            property_name=embedding_property,
            embeddings_dimension=embedding_dimension,
        )

        pgpub_label = FoundationalNodeEnum.USPTO_PGPUB.value[1]
        logger.info(
            f"create embeddings index for {projection_graph_name} label: {pgpub_label} embedding dimension: {embedding_dimension}..."
        )
        self.neo4j_train_embeddings_adapter.create_embedding_index(
            node_label=pgpub_label,
            property_name=embedding_property,
            embeddings_dimension=embedding_dimension,
        )
