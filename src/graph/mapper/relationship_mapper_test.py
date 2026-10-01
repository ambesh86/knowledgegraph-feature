import logging
import unittest

import pytest

from graph.mapper.relationship_mapper import RelationshipMapper
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class RelationshipMapperTest(unittest.TestCase):
    relationship_mapper = RelationshipMapper()

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    def test_ready(self):
        assert self.sample_extraction is not None
        assert self.relationship_mapper is not None

    def test_when_relationships_then_map(self):
        relations = self.relationship_mapper.map(self.sample_extraction.relationships)
        assert relations is not None
        rels = set([rel.relation for rel in relations])
        expected_rels = {
            "has_application",
            "has_combination",
            "has_delivery",
            "has_enhancement",
            "has_inhibition",
            "has_involvement",
        }
        for expected in expected_rels:
            assert expected in rels
