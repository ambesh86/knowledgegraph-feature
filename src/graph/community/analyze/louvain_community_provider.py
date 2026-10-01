import logging
from typing import Generator

import networkx
from networkx import Graph

from graph.community.analyze.leiden_community_provider import CommunityProvider

logger = logging.getLogger(__name__)


class LouvainCommunityProvider(CommunityProvider):
    """
    Class to build graph communities

    2.4 Element Summaries → Graph Communities
    See, https://arxiv.org/html/2404.16130v1
    """

    def compress(self, graph: Graph) -> Graph:
        return networkx.dedensify(graph)

    def build_communities_multilevel(self, graph: Graph) -> list[list[Graph]]:
        return self.build_community1(graph)

    def build_community1(self, graph: Graph) -> list[list[Graph]]:
        # communities = networkx.community.louvain_communities(graph)
        community_level_partitions = networkx.community.louvain_partitions(graph)
        communities = self._exhaust_generator(community_level_partitions)
        logger.info(
            f"created communities: {len(communities)}, approach: louvain algorithm"
        )
        communities.reverse()
        return communities

    def build_community2(self, graph: Graph) -> list:
        communities_generator = networkx.community.girvan_newman(graph)
        communities = self._exhaust_generator(communities_generator)
        logger.info(f"created communities: {len(communities)}, approach: girvan_newman")
        return communities

    def build_community3(self, graph: Graph) -> list:
        communities = networkx.community.greedy_modularity_communities(graph)
        logger.info(
            f"created communities: {len(communities)}, approach: greedy_modularity_communities"
        )
        return communities

    def build_community4(self, graph: Graph) -> list:
        communities_generator = networkx.community.k_clique_communities(graph, 12)
        communities = self._exhaust_generator(communities_generator)
        logger.info(
            f"created communities: {len(communities)}, approach: k_clique_communities"
        )
        return communities

    def _exhaust_generator(self, communities_generator: Generator, max_levels=4):
        # >>> import networkx as nx
        # >>> G = nx.barbell_graph(5, 1)
        # >>> communities_generator = nx.community.girvan_newman(G)
        # >>> top_level_communities = next(communities_generator)
        # >>> next_level_communities = next(communities_generator)
        # >>> sorted(map(sorted, next_level_communities))
        communities = []
        i = 0
        for community in communities_generator:
            i += 1
            if i > max_levels:
                break
            communities.append(community)

        return communities
