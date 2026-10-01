import logging
from pathlib import Path

from dotenv import load_dotenv

from document.load.stored_triples_loader import StoredTriplesLoader
from graph.community.analyze.node_expansion_provider import NodeExpansionProvider
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from graph.infra.db.neo4j_graphrag_adapter import Neo4jGraphragAdapter

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

"""
Read entities and relationships and store into the graph database
"""


def main():
    load_dotenv()
    driver = GraphDbConnectionFactory.remote_neo4j_instance_from_env()
    neo4j_adapter = Neo4jGraphragAdapter(driver, "PubMedRAG")
    stored_triples_loader = StoredTriplesLoader()
    node_expansion_provider = NodeExpansionProvider()

    extraction = stored_triples_loader.load(data_dirs=_data_dirs())
    node_expansion_provider.expand_type_nodes(extraction=extraction)
    logger.info(
        f"ingesting data {len(extraction.entities)} entities and {len(extraction.relationships)} relationships"
    )
    neo4j_adapter.ingest(extraction=extraction)


def _data_dirs() -> list[Path]:
    data_root = Path("./output")
    data_dirs = [
        "01681224922d6072340533cd82bedc4b",
        "0223be7bb7cfc12ffab1529a7f30222a",
        "19e024b4954abfc429b19754155fada9",
        "23cf851a351d0d89174b9c76360396bf",
        "27c6f1b40b214416ca20a66258b889b8",
        "4a24f1c15fdce726ebd6340c7dff2f2a",
        "5cb17ba0e0a201abc979aac1bca9d67c.leiden",
        "7fb83630f305e6148cbb1e7e6df53452",
        "a010cedd52addd77371973b6cca48396",
        "ba533502204a4ecb4e5dc61977cc93d2",
        "bd0c11b505f8450a061d354f7add39f2",
        "e5976811cbf1095d1382cafbf8a14dc7",
        "eb9fa170776163c7800d97c5709bb122",
        "f2b8598844db225aad5878a1222365b8",
        "0a32222f6571c9d5e7b9d9fa5d0e3f81",
        "e636e16d8111b0aad7f2096edb2c7287",
        "e1bdb31293e5349c4856521b4518a41f",
        "700db136cb06a357772c15d869ba55c8",
    ]
    dirs = [(data_root / x) for x in data_dirs]
    return dirs


if __name__ == "__main__":
    main()
