import logging
from typing import Tuple

from numpy import ndarray
from pandas import DataFrame
import pandas

from foundation.model.graph.graph import Graph
from foundation.model.graph.node import Node
from foundation.model.graph.relationship import Relationship
from foundation.mapper.const import (
    END_NODE_ID,
    END_NODE_LABELS,
    END_NODE_NAME,
    REL_TYPE,
    START_NODE_ID,
    START_NODE_LABELS,
    START_NODE_NAME,
)
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class GraphMapper:
    """
    map responses for an n hop subgraph, the result of a nhop eugene query
    """

    @log_time
    def map(self, df: DataFrame | None) -> Graph | None:
        if df is None:
            return None

        logger.info(f"mapping dataframe: {df.shape}")
        uniq_ids = self.get_unique_node_ids(df)
        logger.info(f"found {len(uniq_ids)} uniq ids")
        # fetch unique nodes
        uniq_nodes = self._build_uniq_nodes(df=df, uniq_ids=uniq_ids)
        # build relationships
        relationships = self._build_relationships(df=df)
        logger.info(
            f"mapped {len(uniq_nodes)} uniq nodes and {len(relationships)} relationships"
        )
        return Graph(
            node_count=len(uniq_nodes),
            nodes=uniq_nodes,
            relationships=relationships,
        )

    def _build_uniq_nodes(self, df: DataFrame, uniq_ids: ndarray) -> set[Node]:
        logger.info("generating uniq nodes")
        nodes = set()
        for uniq_id in uniq_ids:
            start_node_match = df[START_NODE_ID] == uniq_id
            end_node_match = df[END_NODE_ID] == uniq_id
            all_matches = df.loc[start_node_match | end_node_match]
            if all_matches is None or len(all_matches) == 0:
                logger.warning(
                    f"failed to find expected id for {uniq_id}. this should not happen, skipping..."
                )
                continue
            first_match = all_matches.iloc[0]
            if first_match[START_NODE_ID] == uniq_id:
                node = self._map_row_to_node(
                    first_match[START_NODE_ID],
                    first_match[START_NODE_NAME],
                    first_match[START_NODE_LABELS],
                )
            elif first_match[END_NODE_ID] == uniq_id:
                node = self._map_row_to_node(
                    first_match[END_NODE_ID],
                    first_match[END_NODE_NAME],
                    first_match[END_NODE_LABELS],
                )
            else:
                logger.warning(
                    f"failed to find expected id for {uniq_id}. this should not happen, skipping..."
                )
                continue
            nodes.add(node)

        return nodes

    def _map_row_to_node(self, id: str, value: str, labels: list[str]) -> Node:
        return Node(id=id, value=value, labels=frozenset(sorted(labels)))

    def _map_row_to_relationship(self, id: str, rel: str) -> Relationship:
        return Relationship(id=id, rel=rel)

    def get_unique_node_ids(self, df: DataFrame) -> ndarray:
        # Concatenate the Series of the two id columns and then find unique ids
        return pandas.concat([df[START_NODE_ID], df[END_NODE_ID]]).unique()

    def _build_relationships(self, df: DataFrame) -> dict[str, set[str]]:
        logger.info("generating relationships")
        relationships = {}
        uniq_ids = df[START_NODE_ID].unique()
        for uniq_id in uniq_ids:
            start_node_match = df[START_NODE_ID] == uniq_id
            all_matches = df.loc[start_node_match]
            if all_matches is None or len(all_matches) == 0:
                logger.warning(
                    f"failed to find expected id for {uniq_id}. this should not happen, skipping..."
                )
                continue
            rels = all_matches.apply(
                lambda row: (row[END_NODE_ID], row[REL_TYPE]), axis=1
            )
            relationships[uniq_id] = self._build_rel_set(rels)

        return relationships

    def _build_rel_set(self, rows: list[Tuple[str, str]]) -> set[Relationship]:
        if rows is None or len(rows) == 0:
            return set()

        rels = set()
        for row in rows:
            rels.add(self._map_row_to_relationship(row[0], row[1]))

        return rels
