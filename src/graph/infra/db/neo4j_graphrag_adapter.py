import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.model.extraction import Extraction
from graph.model.relationship import Relationship
from graph.infra.db.graphrag_adapter import GraphragAdapter
from graph.util.node_util import normalize_node_label

logger = logging.getLogger(__name__)


class Neo4jGraphragAdapter(GraphragAdapter):
    def __init__(self, driver: Driver, database: str = "GraphRAG"):
        self.driver = driver
        self.database = database

    def ingest(self, extraction: Extraction) -> int:
        self._ensure_connection(self.driver)
        count = 0
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for relationship in extraction.relationships:
                    self._merge_relationships(tx, relationship)
                    # commit every 5k relationships?
                    count += 1
                    if count % 1_000 == 0:
                        logger.info(f"ingested {count} relationships")

        logger.info(f"ingested {count} relationships")
        return count

    def _merge_relationships(self, tx: Transaction, rel: Relationship):
        """
        transaction functions must be idempotent
        (i.e., they should produce the same effect when run several times),
        because you do not know upfront how many times they are going to be executed
        https://neo4j.com/docs/python-manual/current/transactions/#process-result
        """
        result = self._merge_and_return(tx, rel)
        logger.debug(
            "Merged relationship: " f"{result['n1']} -[{result['rel']}]- {result['n2']}"
        )

    def _merge_and_return(self, tx: Transaction, rel: Relationship):
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        create_node_1 = (
            "MERGE (n1:`%s` { value: $src_value, id: $src_id, description: $src_description, type: $src_type }) "
            % f"{normalize_node_label(rel.source.type)}"
        )
        create_node_2 = (
            "MERGE (n2:`%s` { value: $tgt_value, id: $tgt_id, description: $tgt_description, type: $tgt_type }) "
            % f"{normalize_node_label(rel.target.type)}"
        )
        create_rel = (
            "MERGE (n1)-[rel:`%s` { id: $rel_id, type: $rel_type, description: $rel_description }]->(n2) "
            % f"{rel.relation}"
        )
        query = "\n".join(
            [
                create_node_1,
                create_node_2,
                create_rel,
                "RETURN n1.value, n2.value, rel.type",
            ]
        )

        logger.debug(f"query: {query}")
        try:
            source = rel.source
            target = rel.target
            record = tx.run(
                query,
                {
                    "src_type": source.type,
                    "src_value": source.value,
                    "src_id": source.id,
                    "src_description": source.description,
                    "tgt_type": target.type,
                    "tgt_value": target.value,
                    "tgt_id": target.id,
                    "tgt_description": target.description,
                    "rel_id": rel.id,
                    "rel_type": rel.relation,
                    "rel_description": rel.description,
                },
            ).single()
            # database_=self.database,
            # result_transformer_=lambda r: r.single(strict=True)

            logger.debug(f"cypher response: {record}")
            return {
                "n1": record["n1.value"],
                "n2": record["n2.value"],
                "rel": record["rel.type"],
            }
        # Capture any errors along with the query and data for traceability
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise

    def _ensure_connection(self, driver: Driver):
        if driver is None:
            raise Exception("Missing neo4j connection!")
