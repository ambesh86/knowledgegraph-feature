import logging
from collections import defaultdict

import igraph as ig
import leidenalg
import networkx
from leidenalg import ModularityVertexPartition

from graph.community.analyze.community_provider import CommunityProvider
from graph.model.entity import Entity

logger = logging.getLogger(__name__)


class LeidenCommunityProvider(CommunityProvider):
    """
    Class to build graph communities

    2.4 Element Summaries → Graph Communities
    See, https://arxiv.org/html/2404.16130v1
    """

    def build_communities_multilevel(
        self, graph: networkx.Graph
    ) -> list[list[set[Entity]]]:
        i_graph = self._convert_nx_to_igraph(graph)
        partition = leidenalg.find_partition(
            i_graph, ModularityVertexPartition, n_iterations=2
        )
        levels = self._get_hierarchical_levels(partition)
        community_levels = self._map_multilevels(partitions=levels, graph=graph)
        logger.info(
            f"created communities: {len(community_levels)}, approach: leiden algorithm"
        )

        community_levels.reverse()
        return community_levels

    def _get_hierarchical_levels(
        self,
        partition: ModularityVertexPartition,
        max_levels: int = 4,
    ) -> list[ModularityVertexPartition]:
        levels = [partition]

        while (
            len(levels) < max_levels and len(partition) > 1
        ):  # As long as we can further coarsen
            # Create a new graph by contracting the previous partition
            agg_partition = partition.aggregate_partition()
            partition = leidenalg.find_partition(
                agg_partition.graph, ModularityVertexPartition
            )
            levels.append(partition)

        return levels

    def _map_multilevels(
        self, partitions: list[ModularityVertexPartition], graph: networkx.Graph
    ) -> list[list[set[Entity]]]:
        levels = []
        for level, partition in enumerate(partitions):
            enhanced_graph = self._enhance_graph_with_community(graph, partition, level)
            communities = self._slice_communities(enhanced_graph, level)
            levels.append(communities)
        return levels

    def _enhance_graph_with_community(
        self, graph: networkx.Graph, partition: ModularityVertexPartition, level: int
    ) -> networkx.Graph:
        """
        Add a 'level' attribute to each node in the NetworkX graph
        the value is the community that node belongs to in that
        """
        # here we map the original graph nodes into a 0 based index
        #   this will be used to decode the igraph community
        # todo: make sure this is correct, results seem reasonable
        node_to_index_map = {i: node for i, node in enumerate(graph.nodes())}
        for idx, community in enumerate(partition):
            for node_id in community:
                node = node_to_index_map[node_id]
                graph.nodes[node][self._level_key(level)] = idx
        return graph

    def _slice_communities(
        self, graph: networkx.Graph, level: int
    ) -> list[set[Entity]]:
        """
        Function to slice nodes into sets based on their community indexes
        """
        community_dict = defaultdict(set)

        # Traverse each node and group them by their level and community index
        for node, data in graph.nodes(data=True):
            community_index = data.get(self._level_key(level), None)
            if community_index is not None:
                community_dict[community_index].add(node)

        # Return the list of sets of nodes, where each set represents a community
        return list(community_dict.values())

    def _convert_nx_to_igraph(self, graph: networkx.Graph):
        """
        Function to convert NetworkX graph to igraph
        """
        # return ig.Graph.TupleList(graph.edges(), directed=False)
        return ig.Graph.from_networkx(graph)

    def _convert_igraph_to_nx(
        self, partition: ModularityVertexPartition
    ) -> networkx.Graph:
        return ig.Graph.to_networkx(partition)

    def _level_key(self, level: int) -> str:
        return f"level_{level:02}"
