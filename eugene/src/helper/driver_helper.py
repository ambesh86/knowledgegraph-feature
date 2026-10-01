import logging
import os
from neo4j import Driver
import neo4j

logger = logging.getLogger(__name__)

def new_driver_from_env() -> Driver:
    neo4j_uri = os.environ["NEO4J_URI"]
    neo4j_user = os.environ["NEO4J_USERNAME"]
    neo4j_passwd = os.environ["NEO4J_PASSWORD"]
    logger.info(f"uri = {neo4j_uri}")
    return neo4j.GraphDatabase.driver(uri=neo4j_uri,auth=(neo4j_user, neo4j_passwd))


def ensure_connection(driver: Driver):
    if driver is None:
        raise Exception("Missing neo4j connection!")
    
