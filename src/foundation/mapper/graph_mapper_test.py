import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.graph_mapper import GraphMapper

logger = logging.getLogger(__name__)


class GraphMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _graph_mapper(self, graph_mapper: GraphMapper) -> None:
        self.graph_mapper = graph_mapper

    @pytest.fixture(autouse=True)
    def _sample_subgraph_0(self, sample_subgraph_0: DataFrame) -> None:
        self.sample_subgraph_0 = sample_subgraph_0

    def test_sanity(self):
        assert self.graph_mapper is not None
        assert self.sample_subgraph_0 is not None

    def test_when_map_then_return(self):
        graph = self.graph_mapper.map(df=self.sample_subgraph_0)
        assert graph is not None

        nodes = graph.nodes
        rels = graph.relationships
        assert len(nodes) == 4
        assert len(rels) == 2

        drug1 = "DB00846"
        drug2 = "DB00538"
        assert drug1 in rels
        assert drug2 in rels

        drug1_rel_ids = {rel.id for rel in rels[drug1]}
        drug2_rel_ids = {rel.id for rel in rels[drug2]}
        assert len(drug1_rel_ids.difference(["989", "11123"])) == 0
        assert len(drug2_rel_ids.difference(["989", "11123"])) == 0

        drug1_rel_types = {rel.rel for rel in rels[drug1]}
        assert len(drug1_rel_types) == 1
        assert "drug_effect" in drug1_rel_types
