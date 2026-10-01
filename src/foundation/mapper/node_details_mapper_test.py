import logging
import unittest

from pandas import DataFrame
import pytest

from foundation.mapper.node_details_mapper import NodeDetailsMapper


logger = logging.getLogger(__name__)


class NodeDetailsMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _node_details_mapper(self, node_details_mapper: NodeDetailsMapper) -> None:
        self.node_details_mapper = node_details_mapper

    @pytest.fixture(autouse=True)
    def _sample_node_details_0(self, sample_node_details_0: DataFrame) -> None:
        self.sample_node_details_0 = sample_node_details_0

    def test_sanity(self):
        assert self.sample_node_details_0 is not None

    def test_when_map_empty_dataframe_then_return(self):
        details = self.node_details_mapper.map(self.sample_node_details_0)
        assert details is not None
        assert len(details) == 1
        node_details = details[0]
        assert len(node_details.labels) == 1
        assert node_details.labels[0] == "exposure"
        assert node_details.id == "C031180"
        assert node_details.value == "chrysene"
        assert node_details.source == "CTD"
        assert node_details.description == None
