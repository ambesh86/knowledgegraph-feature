import logging
from typing import Any

import neo4j
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
import pandas as pd

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection
from foundation.conf.const import EMBEDDINGS_FIELD_NAME, GRAPH_EMBEDDINGS_FIELD_NAME

logger = logging.getLogger(__name__)


class Neo4jListEmbeddingsAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    This class supplies methods to list various embeddings in the graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def list_all_graph_embeddings_by_labels(
        self, labels: list[str]
    ) -> list[pd.DataFrame] | None:
        graph_embeddings_field = GRAPH_EMBEDDINGS_FIELD_NAME
        return self.list_all_embeddings_by_labels(
            labels=labels, field=graph_embeddings_field
        )

    def list_all_sentence_embeddings_by_labels(
        self, labels: list[str]
    ) -> list[pd.DataFrame] | None:
        sentence_embeddings_field = EMBEDDINGS_FIELD_NAME
        return self.list_all_embeddings_by_labels(
            labels=labels, field=sentence_embeddings_field
        )

    def list_all_embeddings_by_labels(
        self, labels: list[str], field: str
    ) -> list[pd.DataFrame] | None:
        if labels is None:
            return None
        ensure_connection(self.driver)

        dataframes = []
        for label in labels:
            dataframe = self._list_all_embeddings_by_label(label, field)
            if dataframe is None:
                continue
            dataframe["label"] = label
            dataframes.append(dataframe)

        return dataframes

    def list_all_embeddings_by_label(
        self, label: str, field: str
    ) -> pd.DataFrame | None:
        ensure_connection(self.driver)
        return self._list_all_embeddings_by_label(label, field)

    def _list_all_embeddings_by_label(
        self, label: str, field: str
    ) -> pd.DataFrame | None:
        query = self._build_find_all_embeddings_by_label(label=label, field=field)
        logger.debug(f"find all embeddings: {query}")
        try:
            records = self.driver.execute_query(
                query,
                result_transformer_=neo4j.Result.to_df,
            )
            logger.debug(f"cypher response: {records}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_find_all_embeddings_by_label(self, label: str, field: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
                RETURN n.node_index as node_index, n.node_name as node_name, n.%s as %s
            """ % (
            normalize_node_label(label),
            field,
            field,
        )
        return lookup_node_query
