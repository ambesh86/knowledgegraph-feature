import logging
import csv

from pathlib import Path

from numpy import ndarray
import pandas as pd

logger = logging.getLogger(__name__)


class TsvEmbeddingsWriter:
    """
    Class responsible for writing node metadata and embeddings to TSV file.
    """

    def write_node_metadata_to_tsv(
        self, output_path: Path, nodes: pd.DataFrame
    ) -> None:
        """
        Writes nodes to a TSV file.
        """
        if output_path is None:
            return None
        if nodes is None:
            return None

        with open(output_path, "w", newline="") as tsv:
            fieldnames = ["VALUE", "ID", "LABEL"]

            writer = csv.DictWriter(tsv, fieldnames=fieldnames, delimiter="\t")

            # Write header only once
            if output_path.stat().st_size == 0:
                writer.writeheader()

            for node in nodes.to_dict("records"):
                row = {
                    "VALUE": node["node_name"],
                    "ID": node["node_index"],
                    "LABEL": node["label"],
                }
                writer.writerow(row)

    def write_embeddings_to_tsv(
        self, output_path: Path, field: str, nodes: pd.DataFrame
    ) -> None:
        """
        Writes nodes to a TSV file.
        """
        if output_path is None:
            return None
        if nodes is None:
            return None

        # todo: fix this ugly code, just use the to_csv options
        nodes["embeddings_tsv"] = nodes[field].apply(self._convert_embeddings_to_tsv)
        nodes["embeddings_tsv"].to_csv(
            output_path,
            index=False,
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
            header=False,
        )

    def _convert_embeddings_to_tsv(self, embeddings: ndarray) -> str:
        return "\t".join(map(str, embeddings))
