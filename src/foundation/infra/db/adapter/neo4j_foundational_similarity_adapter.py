import logging

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
import pandas as pd

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.conf.const import SIMILARITY_GRAPH_PROJECTION_NAME

logger = logging.getLogger(__name__)


class Neo4jFoundationalSimilarityAdapter:
    """
    Adapter to collect simialar nodes on a given eugene(genieve) graph node in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def calculate_similar_by_label_and_values(
        self, label: FoundationalNodeEnum, values: list[str] = []
    ) -> pd.DataFrame | None:
        ensure_connection(self.driver)
        return self._calculate_similar_by_label_and_values(
            graph_name=SIMILARITY_GRAPH_PROJECTION_NAME, label=label, values=values
        )

    def _calculate_similar_by_label_and_values(
        self, graph_name: str, label: FoundationalNodeEnum, values: list[str]
    ) -> pd.DataFrame | None:
        query = self._build_similarity_query_by_label_and_values(
            graph_name=graph_name, label=label, values=values
        )
        logger.info(f"query: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.to_df,
            )
            logger.debug(f"cypher response: {records}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_similarity_query_by_label_and_values(
        self, graph_name: str, label: FoundationalNodeEnum, values: list[str]
    ) -> str:
        # FIXME: cypher injection issue
        # WARNING: this is wrong to inject a user query into the cypher
        # however the api does not let me pass a parameter into a query when using a regex like this?

        if (
            label is not FoundationalNodeEnum.DRUG
            and label is not FoundationalNodeEnum.DISEASE
        ):
            raise ValueError(f"Unsupported node {label.value[1]}!")

        normalized_node_label = normalize_node_label(label.value[1])
        match_clause = f"MATCH (d1:`{normalized_node_label}`)"
        where_clauses = []
        for value in values:
            where_clause = f"d1.node_name =~ '(?i).*{value}.*'"
            where_clauses.append(where_clause)

        optional_where_clause = ""
        if len(where_clauses) > 0:
            optional_where_clause = "WHERE " + "\n\tor ".join(where_clauses)

        facet_count_clause = """
            CALL gds.nodeSimilarity.filtered.stream('%s', {
                degreeCutoff: 1,
                similarityCutoff: .45,
                similarityMetric: "COSINE",
                sourceNodeFilter: [d1]
            })
            YIELD node1, node2, similarity
            RETURN similarity,
            gds.util.asNode(node1).node_name AS name1,
            gds.util.asNode(node2).node_name AS name2,
            toStringOrNull(gds.util.asNode(node1).node_id) AS id1,
            toStringOrNull(gds.util.asNode(node2).node_id) AS id2
            ORDER BY similarity DESCENDING, name1, name2
        """ % (
            graph_name
        )

        facet_count_query = "\n".join(
            [match_clause, optional_where_clause, facet_count_clause]
        )
        return facet_count_query
