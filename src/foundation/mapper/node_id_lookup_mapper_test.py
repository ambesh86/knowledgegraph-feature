import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.node_id_lookup_mapper import NodeIdLookupMapper


logger = logging.getLogger(__name__)


class NodeIdLookupMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _node_id_lookup_mapper(self, node_id_lookup_mapper: NodeIdLookupMapper) -> None:
        self.node_id_lookup_mapper = node_id_lookup_mapper

    @pytest.fixture(autouse=True)
    def _sample_node_id_lookup_0(self, sample_node_id_lookup_0: DataFrame) -> None:
        self.sample_node_id_lookup_0 = sample_node_id_lookup_0

    def test_sanity(self):
        assert self.sample_node_id_lookup_0 is not None

    def test_when_map_empty_dataframe_then_return(self):
        node_id_lookup = self.node_id_lookup_mapper.map(
            value="", fuzzy_match=False, df=None
        )
        assert node_id_lookup is not None

        assert node_id_lookup.fuzzy_match == False
        assert node_id_lookup.count == 0
        assert node_id_lookup.query == ""

    def test_when_map_then_return(self):
        node_id_lookup = self.node_id_lookup_mapper.map(
            value="test", fuzzy_match=False, df=self.sample_node_id_lookup_0
        )
        assert node_id_lookup is not None

        assert node_id_lookup.fuzzy_match == False
        assert node_id_lookup.count == 2
        assert node_id_lookup.query == "test"
        assert len(node_id_lookup.results) == 2
        assert node_id_lookup.results[0].id == "DB00846"
        assert node_id_lookup.results[0].value == "Flurandrenolide"
        assert node_id_lookup.results[1].id == "DB00538"
        assert node_id_lookup.results[1].value == "Gadoversetamide"
