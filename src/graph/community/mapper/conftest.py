from pathlib import Path

import pytest
from graph.community.mapper.community_report_parser import CommunityReportParser
from graph.community.mapper.csv_mapper import CsvMapper
from graph.mapper.triples_parser import TriplesParser
from graph.model.extraction import Extraction

TEST_DATA = "tests/data"
TRIPLES_JSON = f"{TEST_DATA}/triples.json"
TRIPLES_JSON_LG = f"{TEST_DATA}/triples-lg.json"
COMMUNITY_REPORT_FILE = f"{TEST_DATA}/community-summary.txt"


@pytest.fixture(scope="class", autouse=False)
def csv_mapper() -> CsvMapper:
    return CsvMapper()


@pytest.fixture(scope="class", autouse=False)
def community_report_parser() -> CommunityReportParser:
    return CommunityReportParser()


@pytest.fixture(scope="class", autouse=True)
def sample_extraction() -> Extraction:
    return _read_extraction(TRIPLES_JSON)


@pytest.fixture(scope="class", autouse=True)
def sample_extraction_lg() -> Extraction:
    return _read_extraction(TRIPLES_JSON_LG)


@pytest.fixture(scope="class", autouse=True)
def sample_community_report() -> str:
    return Path(COMMUNITY_REPORT_FILE).read_text()


def _read_extraction(file_name: str) -> Extraction:
    triples_parser = TriplesParser()
    json = Path(file_name).read_text()
    extraction = triples_parser.parse(json)
    return extraction
