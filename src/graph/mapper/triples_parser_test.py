import logging
import unittest

import pytest
from graph.mapper.triples_parser import TriplesParser
from graph.model.entity import Entity

logger = logging.getLogger(__name__)


class TriplesParserTest(unittest.TestCase):
    triples_parser = TriplesParser()

    @pytest.fixture(autouse=True)
    def _samples_triples_json(self, sample_triples_json: str):
        self.samples_triples_json = sample_triples_json

        logger.debug(self.samples_triples_json)

    def test_ready(self):
        assert self.samples_triples_json is not None
        assert self.triples_parser is not None

    def test_when_triples_then_parse(self):
        extracted = self.triples_parser.parse(self.samples_triples_json)
        assert extracted is not None
        assert len(extracted.entities) == 15
        assert Entity(type="Protein", value="PolQ") in extracted.entities
        assert len(extracted.relationships) == 10

    def test_when_relationships_contain_missing_entities_then_add_missing(self):
        extracted = self.triples_parser.parse(self.samples_triples_json)
        assert extracted is not None
        self.assertIn(
            Entity(type="unknown", value="Q-mediated end joining"),
            extracted.entities,
        )
