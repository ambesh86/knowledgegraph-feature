import logging
import unittest

import pytest
from graph.mapper.graph_mapper import GraphMapper
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class GraphMapperTest(unittest.TestCase):
    graph_mapper = GraphMapper()

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    def test_ready(self):
        assert self.sample_extraction is not None
        assert self.graph_mapper is not None

    def test_when_extraction_then_populate_graph(self):
        graph = self.graph_mapper.map(self.sample_extraction)
        assert graph is not None
        nodes = list(graph.nodes)
        assert nodes is not None
        assert len(nodes) == 15
        edges = list(graph.edges)
        assert edges is not None
        assert len(edges) == 10

    # def test_when_extraction_then_populate_render(self):
    #     render = GraphRender(self.graph_mapper)
    #     render.render_extraction(self.sample_extraction)
