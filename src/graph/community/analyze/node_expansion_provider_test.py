import logging
import unittest

import pytest

from graph.community.analyze.node_expansion_provider import NodeExpansionProvider
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class NodeExpansionTest(unittest.TestCase):
    node_expansion_provider = NodeExpansionProvider()

    @pytest.fixture(autouse=True)
    def _sample_extraction_lg(self, sample_extraction_lg: Extraction):
        self.sample_extraction_lg = sample_extraction_lg

    def test_ready(self):
        assert self.sample_extraction_lg is not None
        assert self.node_expansion_provider is not None

    def test_when_extraction_then_expand_nodes(self):
        expanded = self.node_expansion_provider.expand_type_nodes(
            extraction=self.sample_extraction_lg
        )
        assert expanded is not None
        assert len(expanded.entities) >= 415
        assert len(expanded.relationships) >= 600
