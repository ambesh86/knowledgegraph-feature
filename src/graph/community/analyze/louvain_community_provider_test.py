import logging
import unittest

import pytest
from networkx import Graph

from graph.community.analyze.louvain_community_provider import LouvainCommunityProvider
from graph.graph_render import GraphRender
from graph.mapper.graph_mapper import GraphMapper

logger = logging.getLogger(__name__)


class CommunityProviderTest(unittest.TestCase):
    community_provider = LouvainCommunityProvider()

    @pytest.fixture(autouse=True)
    def _sample_graph(self, sample_graph: Graph):
        self.sample_graph = sample_graph

    @pytest.fixture(autouse=True)
    def _sample_graph_lg(self, sample_graph_lg: Graph):
        self.sample_graph_lg = sample_graph_lg

    def test_ready(self):
        assert self.sample_graph is not None
        assert self.sample_graph_lg is not None
        assert self.community_provider is not None

    def test_when_graph_then_detect_communities(self):
        communities = self.community_provider.build_communities_multilevel(
            self.sample_graph
        )
        assert len(communities) >= 2

    def test_when_graph_large_then_detect_communities(self):
        community_levels = self.community_provider.build_communities_multilevel(
            self.sample_graph_lg
        )
        self.print_communities(community_levels)
        assert len(community_levels) >= 3
        each_level_has_communities = [
            len(community) > 70 for community in community_levels
        ]
        assert any(each_level_has_communities)
        has_level0_communities = [
            len(community) > 3 for community in community_levels[0]
        ]
        assert any(has_level0_communities)
        has_level1_communities = [
            len(community) > 3 for community in community_levels[1]
        ]
        assert any(has_level1_communities)
        has_level2_communities = [
            len(community) > 3 for community in community_levels[2]
        ]
        assert any(has_level2_communities)

    def print_communities(self, communities: list):
        logger.info(f"communities = {len(communities)}")
        i: int = 0
        for communitiy in communities:
            i += 1
            logger.info(f"{i} {len(communitiy)}")

    def vizualize_graph(self, graph: Graph) -> None:
        render = GraphRender(GraphMapper())
        render.render_graph(graph)
