import logging
import unittest

import pytest
from graph.community.util.knowledge_util import (
    connected_relationships,
    connected_relationships_for_entities,
    unique_relationship_descriptions,
)
from graph.model.entity import Entity
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class KnowledgeUtilTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    def test_ready(self):
        assert self._sample_extraction is not None

    def test_given_extracted_triples_and_entity_when_find_descriptions_then_return(
        self,
    ):
        relationships = self.sample_extraction.relationships
        find_entity = Entity(type="Molecule", value="i53 mRNA")
        descriptions = unique_relationship_descriptions(
            entity=find_entity,
            rels=relationships,
        )
        assert descriptions is not None
        assert len(descriptions) == 4

    def test_given_extracted_triples_and_entity_when_find_relationships_then_return(
        self,
    ):
        relationships = self.sample_extraction.relationships
        find_entity = Entity(type="Molecule", value="i53 mRNA")
        connected = connected_relationships(
            entity=find_entity,
            relationships=relationships,
        )
        assert connected is not None
        assert len(connected) == 4
        assert connected.pop().source == find_entity

    def test_given_extracted_triples_and_entities_when_find_relationships_then_return(
        self,
    ):
        relationships = self.sample_extraction.relationships
        find_entities = {
            Entity(type="Molecule", value="i53 mRNA"),
            Entity(type="Small Molecule", value="AZD7648"),
        }
        connected = connected_relationships_for_entities(
            entities=find_entities,
            relationships=relationships,
        )
        assert connected is not None
        assert len(connected) == 5
        for rel in connected:
            assert rel.target in find_entities or rel.source in find_entities
