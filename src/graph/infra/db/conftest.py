import os
from pathlib import Path

from pymilvus import MilvusClient
import pytest
from neo4j import Driver
from kuzu import Connection

from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.relationship_mapper import RelationshipMapper
from graph.mapper.triples_parser import TriplesParser
from graph.model.extraction import Extraction
from graph.mapper.summaries_parser import SummariesParser
from graph.model.summary import Summary
from graph.infra.embedding.summary_embedding_provider import SummaryEmbeddingProvider
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from graph.infra.db.neo4j_graphrag_adapter import Neo4jGraphragAdapter
from graph.infra.db.milvus_vector_adapter import MilvusVectorAdapter
from graph.infra.db.vector_db_connection_factory import VectorDbConnectionFactory

JSON_LOAD_TEST_DIR = "tests/data/load"
JSON_ENTITY_LOAD_TEST_DIR = f"{JSON_LOAD_TEST_DIR}/entity"
JSON_RELATIONSHIP_LOAD_TEST_DIR = f"{JSON_LOAD_TEST_DIR}/relationship"

PROTEIN_JSON = f"{JSON_ENTITY_LOAD_TEST_DIR}/protein.json"
MOLECULE_JSON = f"{JSON_ENTITY_LOAD_TEST_DIR}/molecule.json"
BIOLOGICAL_PROCESS_JSON = f"{JSON_ENTITY_LOAD_TEST_DIR}/biological_process.json"
GENOMIC_LOCUS_JSON = f"{JSON_ENTITY_LOAD_TEST_DIR}/genomic_locus.json"

ENCHANCEMENT_JSON = f"{JSON_RELATIONSHIP_LOAD_TEST_DIR}/enhancement.json"
INHIBITION_JSON = f"{JSON_RELATIONSHIP_LOAD_TEST_DIR}/inhibition.json"
INVOLVEMENT_JSON = f"{JSON_RELATIONSHIP_LOAD_TEST_DIR}/involvement.json"


TEST_DATA = "tests/data"
TRIPLES_JSON = f"{TEST_DATA}/triples.json"
TRIPLES_JSON_LG = f"{TEST_DATA}/triples-lg.json"
COMMUNITY_REPORT_FILE = f"{TEST_DATA}/community-summary.txt"


@pytest.fixture(scope="module")
def kuzu_connection() -> Connection:
    return GraphDbConnectionFactory.local_kuzu_instance()


@pytest.fixture(scope="module")
def neo4j_driver() -> Driver:
    neo4j_uri = os.environ["NEO4J_URI"]
    neo4j_user = os.environ["NEO4J_USERNAME"]
    neo4j_passwd = os.environ["NEO4J_PASSWORD"]
    return GraphDbConnectionFactory.remote_neo4j_instance(
        uri=neo4j_uri, user=neo4j_user, passwd=neo4j_passwd
    )


@pytest.fixture(scope="class")
def sample_extraction_lg() -> Extraction:
    extraction = _read_extraction(TRIPLES_JSON_LG)
    entity_mapper = EntityMapper()
    relationship_mapper = RelationshipMapper()
    extraction.entities = entity_mapper.map_entities(extraction.entities)
    extraction.relationships = relationship_mapper.map_relationships(
        extraction.relationships
    )
    return extraction


def _read_extraction(file_name: str) -> Extraction:
    triples_parser = TriplesParser()
    json = Path(file_name).read_text()
    extraction = triples_parser.parse(json)
    return extraction


@pytest.fixture(scope="class")
def neo4j_graphrag_adapter(neo4j_driver: Driver) -> Neo4jGraphragAdapter:
    return Neo4jGraphragAdapter(neo4j_driver)


@pytest.fixture(scope="class")
def protein_entity_json() -> str:
    return _read_path_as_text(PROTEIN_JSON)


@pytest.fixture(scope="class")
def molecule_entity_json() -> str:
    return _read_path_as_text(MOLECULE_JSON)


@pytest.fixture(scope="class")
def biological_process_entity_json() -> str:
    return _read_path_as_text(BIOLOGICAL_PROCESS_JSON)


@pytest.fixture(scope="class")
def genomic_locus_entity_json() -> str:
    return _read_path_as_text(GENOMIC_LOCUS_JSON)


@pytest.fixture(scope="class")
def inhibition_relationship_json() -> str:
    return _read_path_as_text(INHIBITION_JSON)


@pytest.fixture(scope="class")
def involvement_relationship_json() -> str:
    return _read_path_as_text(INVOLVEMENT_JSON)


def _read_path_as_text(path: str) -> str:
    return Path(path).read_text()


@pytest.fixture(scope="class")
def graph_database_init(
    kuzu_connection: Connection,
) -> Connection:
    _drop_tables(kuzu_connection)
    _create_tables(kuzu_connection)

    # https://docs.kuzudb.com/extensions/json/
    kuzu_connection.execute("INSTALL json")
    kuzu_connection.execute("LOAD EXTENSION json")
    kuzu_connection.execute(f"COPY Protein FROM '{PROTEIN_JSON}'")
    kuzu_connection.execute(f"COPY Molecule FROM '{MOLECULE_JSON}'")
    kuzu_connection.execute(f"COPY BiologicalProcess FROM '{BIOLOGICAL_PROCESS_JSON}'")
    kuzu_connection.execute(f"COPY GenomicLocus FROM '{GENOMIC_LOCUS_JSON}'")
    # graph_db_connection.execute(f"COPY Enhancement FROM '{ENCHANCEMENT_JSON}'")
    return kuzu_connection


def _drop_tables(conn: Connection):
    # drop relation tables first
    relation_tables = ["Enhancement"]
    for relation_table in relation_tables:
        conn.execute(f"DROP TABLE IF EXISTS {relation_table}")

    entity_tables = ["Protein", "Molecule", "BiologicalProcess", "GenomicLocus"]
    for entity_table in entity_tables:
        conn.execute(f"DROP TABLE IF EXISTS {entity_table}")


def _create_tables(conn: Connection):
    conn.execute(
        "CREATE NODE TABLE Protein(entity_name STRING, entity_description STRING, PRIMARY KEY (entity_name))"
    )
    conn.execute(
        "CREATE NODE TABLE Molecule(entity_name STRING, entity_description STRING, PRIMARY KEY (entity_name))"
    )
    conn.execute(
        "CREATE NODE TABLE BiologicalProcess(entity_name STRING, entity_description STRING, PRIMARY KEY (entity_name))"
    )
    conn.execute(
        "CREATE NODE TABLE GenomicLocus(entity_name STRING, entity_description STRING, PRIMARY KEY (entity_name))"
    )
    conn.execute(
        "CREATE REL TABLE Enhancement(FROM Molecule TO GenomicLocus, relation STRING, relationship_description STRING)"
    )


@pytest.fixture(scope="class", autouse=True)
def sample_community_report() -> str:
    return Path(COMMUNITY_REPORT_FILE).read_text()


@pytest.fixture(scope="class", autouse=True)
def summaries_parser() -> SummariesParser:
    return SummariesParser()


@pytest.fixture(scope="class", autouse=True)
def sample_summary(
    sample_community_report: str, summaries_parser: SummariesParser
) -> Summary:
    marker = "```"
    first_found = sample_community_report.find(marker)
    start = first_found + len(marker)
    end = sample_community_report.find(marker, start)
    json = sample_community_report[start:end]
    summary = summaries_parser.parse(json)
    summary.id = "abc123"
    return summary


@pytest.fixture(scope="module")
def milvus_client() -> MilvusClient:
    milvus_uri = os.environ["MILVUS_URI"]
    milvus_token = os.environ["MILVUS_TOKEN"]
    return VectorDbConnectionFactory.milvus_client(uri=milvus_uri, token=milvus_token)


def model_cache_dir() -> str | None:
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    return value


@pytest.fixture(scope="class")
def summary_embedding_provider(model_cache_dir: str) -> SummaryEmbeddingProvider:
    return SummaryEmbeddingProvider(model_cache_dir=model_cache_dir)


@pytest.fixture(scope="class")
def milvus_vector_adapter(
    milvus_client: MilvusClient, summary_embedding_provider: SummaryEmbeddingProvider
) -> MilvusVectorAdapter:
    milvus_collection_name = os.environ["MILVUS_COLLECTION_NAME"]
    return MilvusVectorAdapter(
        client=milvus_client,
        summary_embedding_provider=summary_embedding_provider,
        collection_name=milvus_collection_name,
    )
