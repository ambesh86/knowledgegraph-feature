import logging
import unittest

import pytest

from graph.mapper.entity_mapper import EntityMapper
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class EntityMapperTest(unittest.TestCase):
    entity_mapper = EntityMapper()

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    def test_ready(self):
        assert self.sample_extraction is not None
        assert self.entity_mapper is not None

    def test_when_entities_then_map(self):
        entities = self.entity_mapper.map_entities(self.sample_extraction.entities)
        assert entities is not None
        values = set([e.type for e in entities])
        expected_values = {
            "BiologicalProcess",
            "CellType",
            "GenomicLocus",
            "Molecule",
            "SmallMolecule",
            "Organism",
            "Protein",
            "Unknown",
        }
        for expected in expected_values:
            assert expected in values
