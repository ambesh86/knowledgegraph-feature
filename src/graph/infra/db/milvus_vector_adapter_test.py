import logging
import unittest

import pytest

from graph.model.summary import Summary
from graph.infra.db.milvus_vector_adapter import MilvusVectorAdapter

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Ignore integration test")
class MilvusVectorAdapterTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _milvus_vector_adapter(self, milvus_vector_adapter: MilvusVectorAdapter):
        self.milvus_vector_adapter = milvus_vector_adapter

    @pytest.fixture(autouse=True)
    def _sample_summary(self, sample_summary: Summary):
        self.sample_summary = sample_summary

    def test_sanity(self):
        assert self.milvus_vector_adapter is not None
        assert self.sample_summary is not None

    @pytest.mark.integration
    def test_given_a_database_and_summary_when_ingest_then_verify(self):
        response = self.milvus_vector_adapter.ingest([self.sample_summary])
        assert response is not None
        assert response["insert_count"] >= 1
        ids = response["ids"]
        assert len(ids) == 1
        assert 0 in ids
