import logging
import unittest

import pytest
from networkx import Graph

from graph.community.analyze.leiden_community_provider import LeidenCommunityProvider

logger = logging.getLogger(__name__)


class CommunityProviderTest(unittest.TestCase):
    community_provider = LeidenCommunityProvider()

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
        assert len(communities[0]) >= 2

    def test_when_graph_large_then_detect_communities(self):
        community_levels = self.community_provider.build_communities_multilevel(
            self.sample_graph_lg
        )
        assert len(community_levels) >= 1
        large_communities = [len(community) > 3 for community in community_levels]
        assert any(large_communities)
