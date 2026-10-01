import csv
import logging
import os
import neo4j
from neo4j import Driver
from dotenv import load_dotenv
from adapter.neo4j_adapter import Neo4jAdapter
from model.node import Node

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    nodes_csv_path = "./nodes_modified.csv"
    nodes = _load_nodes_csv(nodes_csv_path)
    logger.info(f"loaded {len(nodes)} for ingest...")
    neo4j_adapter = Neo4jAdapter(driver = _driver())
    neo4j_adapter.ingest(nodes)
    logger.info(f"ingest finished...")


def _load_nodes_csv(path) -> list[Node]:
    nodes = []
    with open(path, mode="r") as csv_in:
        reader = csv.DictReader(csv_in)
        for row in reader:
            # node_index,node_id,label,node_name,node_source
            index = row["node_index"]
            id = row["node_id"]
            label = row["label"]
            name = row["node_name"]
            source = row["node_source"]
            node = Node(index, id, label, name, source)
            nodes.append(node)
    return nodes


def _driver() -> Driver:
    neo4j_uri = os.environ["NEO4J_URI"]
    neo4j_user = os.environ["NEO4J_USERNAME"]
    neo4j_passwd = os.environ["NEO4J_PASSWORD"]
    logger.info(f"uri = {neo4j_uri}")
    return neo4j.GraphDatabase.driver(uri=neo4j_uri,auth=(neo4j_user, neo4j_passwd))

if __name__ == "__main__":
    main()

