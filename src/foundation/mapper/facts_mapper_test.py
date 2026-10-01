import logging
import unittest

import pytest

from foundation.mapper.facts_mapper import FactsMapper
from foundation.model.graph.graph import Graph


logger = logging.getLogger(__name__)


class FactsMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _facts_mapper(self, facts_mapper: FactsMapper) -> None:
        self.facts_mapper = facts_mapper

    @pytest.fixture(autouse=True)
    def _sample_graph_0(self, sample_graph_0: Graph) -> None:
        self.sample_graph_0 = sample_graph_0

    def test_sanity(self):
        assert self.facts_mapper is not None
        assert self.sample_graph_0 is not None

    def test_when_map_then_return(self):
        facts = self.facts_mapper.map(graph=self.sample_graph_0)

        expected = [
            "Drug Flurandrenolide has effect phenotype, Inflammatory abnormality of the skin",
            "Drug Flurandrenolide has effect phenotype, Pruritus",
            "Drug Gadoversetamide has effect phenotype, Inflammatory abnormality of the skin",
            "Drug Gadoversetamide has effect phenotype, Pruritus",
        ]
        assert facts is not None
        assert len(facts) == 4
        for expect in expected:
            assert expect in facts
