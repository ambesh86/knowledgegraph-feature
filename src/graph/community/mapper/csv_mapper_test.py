import logging
import unittest

import pytest

from graph.community.mapper.csv_mapper import CsvMapper
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class CsvMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _csv_mapper(self, csv_mapper: CsvMapper):
        self.csv_mapper = csv_mapper

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    def test_ready(self):
        assert self.sample_extraction is not None
        assert self.csv_mapper is not None

    def test_given_extracted_triples_when_map_entities_then_return(self):
        csv = self.csv_mapper.entities_as_csv(self.sample_extraction.entities)
        assert csv is not None
        assert len(csv) == 15
        values = {
            "53BP1",
            "AZD7648",
            "CD34+ HSPCs",
            "CYBB locus",
            "DNA-PKcs",
            "GSE56 mRNA",
            "HDR",
            "MAGT1 locus",
            "NHEJ",
            "NSG-SGM3 recipients",
            "PolQ",
            "Q-mediated end joining",
            "i53 mRNA",
            "i53",
            "rAAV6 templates",
        }
        valid = [self._is_valid_entity_row(row, values) for row in csv]
        assert all(valid)

    def test_given_extracted_triples_when_map_relationships_then_return(self):
        csv = self.csv_mapper.relationships_as_csv(self.sample_extraction.relationships)
        assert csv is not None
        assert len(csv) == 10
        values = {
            "53BP1",
            "AZD7648",
            "DNA-PKcs",
            "PolQ",
            "i53 mRNA",
            "i53",
            "rAAV6 templates",
        }
        valid = [self._is_valid_entity_row(row, values) for row in csv]
        assert all(valid)

    def test_given_triples_and_with_header_when_map_relationships_then_return_header(
        self,
    ):
        csv = self.csv_mapper.relationships_as_csv(
            self.sample_extraction.relationships, with_header=True
        )
        assert csv is not None
        assert len(csv) == 11
        assert csv[0] == "id,source,target,relation,description"

    def test_given_triples_and_with_header_when_map_entities_then_return_header(self):
        csv = self.csv_mapper.entities_as_csv(
            self.sample_extraction.entities, with_header=True
        )
        assert csv is not None
        assert len(csv) == 16
        assert csv[0] == "id,entity,type,description"

    def _is_valid_entity_row(self, row: str, valid_values: set[str]) -> bool:
        return row.split(",")[1] in valid_values

    def _is_valid_relationship_row(self, row: str, valid_values: set[str]) -> bool:
        return row.split(",")[1] in valid_values
