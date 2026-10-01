import logging

import neo4j
from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label, normalize_node_name
from graph.util.util import ensure_connection
from graph.infra.db.graphrag_linking_adapter import GraphragLinkingAdapter
from graph.infra.db.const import HAS_PUBLICATION_EXTRACTION_REL_TYPE

logger = logging.getLogger(__name__)


class Neo4jGraphragLinkingAdapter(GraphragLinkingAdapter):
    """
    Class with responsibility to lookup nodes to be linked
    Uses regex
    TODO: improve lookup and linking processes
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_index_by_node_name(
        self, entity_type: str, node_name: str
    ) -> str | None:
        """
        return node_index of node with node_name
        """
        ensure_connection(self.driver)

        return self._find_node_index_by_node_name(entity_type, node_name)

    def link_publication_node(
        self,
        source_node_label: str,
        source_primary_key_label: str,
        source_primary_key: str | int,
        target_node_index: str,
    ) -> str | None:
        """
        Links a publication with the base euGENE graph
        a publication can be any unstructured text that we extracted from
        e.g. pgpub, pubmed, etc
        (publication of type source_primary_key_label given primary_key)-[:has_publication]-(base entity with given node_index)
        """
        if (
            source_node_label is None
            or source_primary_key_label is None
            or source_primary_key is None
            or target_node_index is None
        ):
            return None
        ensure_connection(self.driver)

        # merge to add new relationship between
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                primary_key = self._link_publication_and_node(
                    tx,
                    source_node_label=source_node_label,
                    source_primary_key_label=source_primary_key_label,
                    source_primary_key=source_primary_key,
                    target_node_index=target_node_index,
                )

        logger.info(
            f"linked {target_node_index} to {source_primary_key_label}:{primary_key}"
        )

    def _find_node_index_by_node_name(
        self, entity_type: str, node_name: str
    ) -> str | None:
        query = self._build_find_by_node_name_query(
            entity_type=entity_type, node_name=node_name
        )
        logger.debug(f"query: {query} node_name: {node_name}")
        try:
            record = self.driver.execute_query(
                query,
                database_=self.database,
                result_transformer_=neo4j.Result.single,
            )
            if record is None:
                return record
            node_name = str(record["n.node_name"])
            node_index = str(record["n.node_index"])
            logger.debug(f"cypher response: {node_name} {node_index}")
            return node_index
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise

    def _link_publication_and_node(
        self,
        tx: Transaction,
        source_node_label: str,
        source_primary_key_label: str,
        source_primary_key: str | int,
        target_node_index: str,
    ) -> str | None:
        """
        link article and node
        """
        if (
            source_node_label is None
            or source_primary_key_label is None
            or target_node_index is None
        ):
            return None

        link_doc = """
            OPTIONAL MATCH (doc:%s { %s: $primary_key })
            OPTIONAL MATCH (entity { node_index: $node_index })
            MERGE (doc)<-[r:%s]-(entity)
            RETURN doc.%s, type(r), entity.node_index
            """ % (
            normalize_node_label(source_node_label),
            source_primary_key_label,
            HAS_PUBLICATION_EXTRACTION_REL_TYPE,
            source_primary_key_label,
        )
        logger.info(
            f"linking source_primary_key: {source_primary_key} node_index: {target_node_index}"
        )
        logger.info(f"upsert: {link_doc}")
        try:
            record = tx.run(
                link_doc,
                {
                    "primary_key": source_primary_key,
                    "node_index": target_node_index,
                },
            ).single()
            logger.info(f"cypher response: {record}")

            if record is None:
                return None

            return record[f"doc.{source_primary_key_label}"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", link_doc, exception)
            raise

    def _build_find_by_node_name_query(self, entity_type: str, node_name: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
                WHERE n.node_name =~ '(?i)%s'
                RETURN n.node_name, n.node_index
            """ % (
            normalize_node_label(entity_type),
            normalize_node_name(node_name),
        )
        return lookup_node_query
