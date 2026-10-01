import logging
from pathlib import Path

import pandas as pd

from infra.util.file_util import ensure_path_exists
from graph.util.node_util import normalize_node_label
from foundation.infra.db.adapter.neo4j_list_embeddings_adapter import (
    Neo4jListEmbeddingsAdapter,
)
from foundation.writer.tsv_embeddings_writer import TsvEmbeddingsWriter
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.conf.const import EMBEDDINGS_FIELD_NAME, GRAPH_EMBEDDINGS_FIELD_NAME

logger = logging.getLogger(__name__)


class ListEmbeddingsProvider:

    def __init__(
        self,
        neo4j_list_embeddings_adapter: Neo4jListEmbeddingsAdapter,
        tsv_embeddings_writer: TsvEmbeddingsWriter,
    ):
        self.neo4j_list_embeddings_adapter = neo4j_list_embeddings_adapter
        self.tsv_embeddings_writer = tsv_embeddings_writer

    def write_all_graph_embeddings_by_labels(
        self, labels: list[FoundationalNodeEnum]
    ) -> Path | None:
        normalized_labels = self._enum_to_list(labels=labels)
        dataframes = (
            self.neo4j_list_embeddings_adapter.list_all_graph_embeddings_by_labels(
                labels=normalized_labels
            )
        )
        base_path = self._tmp_path() / "graph_embeddings"
        ensure_path_exists(base_path)
        self._write_tsv_bundle(
            base_path=base_path,
            field=GRAPH_EMBEDDINGS_FIELD_NAME,
            dataframe=pd.concat(dataframes),
        )

    def write_all_sentence_embeddings_by_labels(
        self, labels: list[FoundationalNodeEnum]
    ) -> list[pd.DataFrame] | None:
        normalized_labels = self._enum_to_list(labels=labels)
        dataframes = (
            self.neo4j_list_embeddings_adapter.list_all_sentence_embeddings_by_labels(
                labels=normalized_labels
            )
        )
        base_path = self._tmp_path() / "sentence_embeddings"
        ensure_path_exists(base_path)
        self._write_tsv_bundle(
            base_path=base_path,
            field=EMBEDDINGS_FIELD_NAME,
            dataframe=pd.concat(dataframes),
        )

    def _write_tsv_bundle(
        self, base_path: Path, field: str, dataframe: pd.DataFrame
    ) -> None:
        metadata_path = base_path / "metadata.tsv"
        logger.info(f"writing metadata to {metadata_path}")
        self.tsv_embeddings_writer.write_node_metadata_to_tsv(
            output_path=metadata_path, nodes=dataframe
        )

        embeddings_dataframe = dataframe[[field]]
        embeddings_path = base_path / f"{field}.tsv"
        logger.info(f"writing embeddings to {embeddings_path}")
        self.tsv_embeddings_writer.write_embeddings_to_tsv(
            output_path=embeddings_path,
            field=field,
            nodes=embeddings_dataframe,
        )

    def _enum_to_list(self, labels: list[FoundationalNodeEnum]) -> list[str]:
        return [normalize_node_label(el.value[1]) for el in labels]

    def _tmp_path(self) -> Path:
        return Path("./tmp")
