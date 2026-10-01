import logging

from graspologic.partition import hierarchical_leiden
from networkx import Graph

from graph.community.analyze.community_provider import CommunityProvider

logger = logging.getLogger(__name__)


class HleidenCommunityProvider(CommunityProvider):
    """
    Class to build graph hierarchical_leiden communities

    2.4 Element Summaries → Graph Communities
    See, https://arxiv.org/html/2404.16130v1

    See, https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v1/
    """

    def __init__(self):
        self.community_summary = {}
        self.max_cluster_size = 10

    def build_communities_multilevel(self, graph: Graph):
        """
        Builds communities from the graph and summarizes them.
        """

        nx_graph = self._create_nx_graph(graph)
        community_hierarchical_clusters = hierarchical_leiden(
            nx_graph, max_cluster_size=self.max_cluster_size
        )
        community_info = self._collect_community_info(
            nx_graph, community_hierarchical_clusters
        )
        logger.info(f"{community_info}")
        # self._summarize_communities(community_info)
        logger.info(f"{nx_graph}")
        return community_info

    def _create_nx_graph(self, graph: Graph):
        """
        Converts internal graph representation to NetworkX graph.
        Converts Entity objects to a string form
        """
        nx_graph = Graph()
        for node in graph.nodes.data():
            node_data = node[1]
            nx_graph.add_node(
                node_data["value"], value=node_data["value"], type=node_data["type"]
            )
        for relation in graph.edges.data():
            source = relation[0]
            target = relation[1]
            relation_source = source.value
            relation_target = target.value
            relation = relation[2]
            nx_graph.add_edge(
                relation_source,
                relation_target,
                relation=relation["relation"],
                description=relation["description"],
            )
        return nx_graph

    def _collect_community_info(self, nx_graph, clusters) -> dict[str:str]:
        """
        Collect detailed information for each node based on their community.
        """
        community_mapping = {item.node: item.cluster for item in clusters}
        community_info = {}
        for item in clusters:
            cluster_id = item.cluster
            # parent_cluster_id = item.parent_cluster or 0
            # composite_id = f"{parent_cluster_id:03}-{cluster_id:03}"
            composite_id = cluster_id
            node = item.node
            if composite_id not in community_info:
                logger.info(f"new cluster_id {cluster_id}")
                community_info[composite_id] = []

            for neighbor in nx_graph.neighbors(node):
                if community_mapping[neighbor] == cluster_id:
                    edge_data = nx_graph.get_edge_data(node, neighbor)
                    if edge_data:
                        detail = f"{node} -> {neighbor} -> {edge_data['relation']} -> {edge_data['description']}"
                        community_info[composite_id].append(detail)
        return community_info

    # def _summarize_communities(self, community_info):
    #     """
    #     Generate and store summaries for each community.
    #     """
    #     for community_id, details in community_info.items():
    #         details_text = "\n".join(details) + "."  # Ensure it ends with a period
    #         self.community_summary[community_id] = self.generate_community_summary(
    #             details_text
    #         )

    # def get_community_summaries(self):
    #     """
    #     Returns the community summaries, building them if not already done.
    #     """
    #     if not self.community_summary:
    #         self.build_communities()
    #     return self.community_summary
