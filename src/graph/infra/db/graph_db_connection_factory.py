import logging
import os
import kuzu
from kuzu import Connection
import neo4j

logger = logging.getLogger(__name__)


class GraphDbConnectionFactory:
    _KUZU_CONNECTION = None
    _NEO4J_DRIVER = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    @classmethod
    def instance(cls) -> Connection:
        return GraphDbConnectionFactory.local_kuzu_instance()

    @classmethod
    def local_kuzu_instance(
        cls, database_path: str = ".db/knowledge_graph_db"
    ) -> Connection:
        if cls._KUZU_CONNECTION is None:
            db = kuzu.Database(database_path)
            cls._KUZU_CONNECTION = kuzu.Connection(db)
        return cls._KUZU_CONNECTION

    @classmethod
    def remote_neo4j_instance(
        cls, uri: str = "neo4j://localhost:7687", user: str = "neo4j", passwd: str = ""
    ) -> neo4j.Driver:
        if cls._NEO4J_DRIVER is None:
            # DB-01/02 fix: bound connection/transaction lifetimes so a slow or
            # deadlocked Cypher query cannot block the adapter thread forever.
            # See Stage 1 Assessment §05.2 (Hot-spots in code).
            pool_size = int(os.environ.get("NEO4J_MAX_POOL_SIZE", "50"))
            connect_timeout = float(os.environ.get("NEO4J_CONNECTION_TIMEOUT", "10"))
            tx_retry_time = float(os.environ.get("NEO4J_MAX_TX_RETRY_TIME", "30"))
            driver = neo4j.GraphDatabase.driver(
                uri=uri,
                auth=(user, passwd),
                max_connection_pool_size=pool_size,
                connection_timeout=connect_timeout,
                max_transaction_retry_time=tx_retry_time,
                keep_alive=True,
            )
            cls._NEO4J_DRIVER = driver
        return cls._NEO4J_DRIVER

    @classmethod
    def remote_neo4j_instance_from_env(cls) -> neo4j.Driver:
        neo4j_uri = os.environ["NEO4J_URI"]
        neo4j_user = os.environ["NEO4J_USERNAME"]
        neo4j_passwd = os.environ["NEO4J_PASSWORD"]
        logger.info(f"found neo4j creds {neo4j_user}@{neo4j_uri}")
        return GraphDbConnectionFactory.remote_neo4j_instance(
            uri=neo4j_uri, user=neo4j_user, passwd=neo4j_passwd
        )
