from pathlib import Path

import pytest
from graph.mapper.triples_parser import TriplesParser
from graph.model.extraction import Extraction

TEST_DATA = "tests/data"
TRIPLES_JSON = f"{TEST_DATA}/triples.json"
TRIPLES_JSON_LG = f"{TEST_DATA}/triples-lg.json"


@pytest.fixture(scope="class", autouse=True)
def sample_extraction() -> Extraction:
    return _read_extraction(TRIPLES_JSON)


@pytest.fixture(scope="class", autouse=True)
def sample_extraction_lg() -> Extraction:
    return _read_extraction(TRIPLES_JSON_LG)


def _read_extraction(file_name: str) -> Extraction:
    triples_parser = TriplesParser()
    json = Path(file_name).read_text()
    extraction = triples_parser.parse(json)
    return extraction
