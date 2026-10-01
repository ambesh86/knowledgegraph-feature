import logging
from neo4j import Driver, Session, Transaction
from neo4j.exceptions import DriverError, Neo4jError
from model.node import Node

logger = logging.getLogger(__name__)


class Neo4jAdapter:
    """
    deprecate: this apprpoach is slow as it requires many transactions. Consider using a batch method
    """

    def __init__(self, driver: Driver, database: str = "KnowlegeGraph"):
        self.driver = driver
        self.database = database

    def ingest(self, nodes: list[Node]) -> int:
        self._ensure_connection(self.driver)
        count = 0
        step = 1_000
        with self.driver.session() as session:
            # with session.begin_transaction() as tx:
            total = len(nodes)
            while count < total:
                batch = nodes[count:(count+step)]
                for node in batch:
                    self._merge_node(session, node)
                    count += 1
                    if count % 100 == 0:
                        logger.info(f"ingested {count} nodes")

        logger.info(f"ingested {count} nodes")
        return count

    def _merge_node(self, session: Session, node: Node) -> dict[str, any]:
        """
        transaction functions must be idempotent
        (i.e., they should produce the same effect when run several times),
        because you do not know upfront how many times they are going to be executed
        https://neo4j.com/docs/python-manual/current/transactions/#process-result
        """
        result = self._merge_and_return(session, node)
        return result

    def _merge_and_return(self, session: Session, node: Node) -> dict[str, any]:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        create_node_1 = (
            "MERGE (n1:`%s` { node_index: $node_index, id: $node_id, label: $label, node_name: $node_name, node_source: $node_source }) "
            % node.label
        )
        query = "\n".join(
            [
                create_node_1,
                "RETURN n1.node_name",
            ]
        )

        logger.debug(f"query: {query}")
        try:
            # node_index,node_id,label,node_name,node_source
            node_index = node.index
            node_id = node.id
            label = node.label
            node_name = node.name
            node_source = node.source
            record = session.run(
                query,
                {
                    "node_index": node_index,
                    "node_id": node_id,
                    "label": label,
                    "node_name": node_name,
                    "node_source": node_source,
                },
            ).single()
            # database_=self.database,
            # result_transformer_=lambda r: r.single(strict=True)

            logger.debug(f"cypher response: {record}")
            return {
                "n1": record["n1.node_name"],
            }
        # Capture any errors along with the query and data for traceability
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise

    def _ensure_connection(self, driver: Driver):
        if driver is None:
            raise Exception("Missing neo4j connection!")
