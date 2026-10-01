import logging
import unittest

import pytest

from graph.infra.db.neo4j_graphrag_adapter import Neo4jGraphragAdapter
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Ignore integration test")
class Neo4jGraphragAdapterTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _neo4j_graphrag_adapter(self, neo4j_graphrag_adapter: Neo4jGraphragAdapter):
        self.neo4j_graphrag_adapter = neo4j_graphrag_adapter

    @pytest.fixture(autouse=True)
    def _sample_extraction_lg(self, sample_extraction_lg: Extraction):
        self.sample_extraction_lg = sample_extraction_lg

    def test_sanity(self):
        assert self.neo4j_graphrag_adapter is not None
        assert self.sample_extraction_lg is not None

    @pytest.mark.integration
    def test_given_a_database_and_load_extraction_then_verify(self):
        count = self.neo4j_graphrag_adapter.ingest(self.sample_extraction_lg)
        assert count is not None
        assert count > 300
