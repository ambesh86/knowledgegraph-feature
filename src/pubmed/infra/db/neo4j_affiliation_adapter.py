import itertools
import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from pubmed.infra.db.const import (
    PUBMED_ARTICLE_AFFILIATION_NODE_TYPE,
    PUBMED_ARTICLE_EXTRACTION_REL_TYPE,
    PUBMED_ARTICLE_NODE_TYPE,
)
from graph.util.util import ensure_connection, get_or_default_list
from pubmed.model.affiliation import Affiliation

logger = logging.getLogger(__name__)


class Neo4jAffiliationAdapter:
    """
    Adapter to perform operations on pubmed affiliation nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert(self, pmcid: str, affiliation: Affiliation) -> str | None:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                node_id = self._upsert(
                    tx=tx,
                    pmcid=pmcid,
                    affiliation=affiliation,
                )

        logger.debug(f"merged pmcid: {pmcid} affiliation: {affiliation.affiliation_id}")
        return node_id

    def _upsert(
        self, tx: Transaction, pmcid: str, affiliation: Affiliation
    ) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert = """
            MATCH (doc:`%s` { pmcid: $pmcid })
            MERGE (affiliation:`%s` {
                affiliation_id: $affiliation_id
            })
            ON MATCH
                SET affiliation.location = $location,
                    affiliation.emails = $emails,
                    affiliation.refresh_date = datetime()
            ON CREATE
                SET affiliation.location = $location,
                    affiliation.emails = $emails,
                    affiliation.refresh_date = datetime(),
                    affiliation.affiliation_id = $affiliation_id,
                    affiliation.is_pubmed = true
            """ % (
            PUBMED_ARTICLE_NODE_TYPE,
            PUBMED_ARTICLE_AFFILIATION_NODE_TYPE,
        )

        link_article_upsert = """
            MERGE (doc)-[article_rel:`%s` { is_pubmed: true }]-(affiliation)
            """ % (
            PUBMED_ARTICLE_EXTRACTION_REL_TYPE
        )

        upsert_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [upsert],
                        [link_article_upsert],
                        [
                            "RETURN doc.pmcid, affiliation.affiliation_id, affiliation.refresh_date"
                        ],
                    ]
                )
            )
        )

        logger.debug(f"upsert: {upsert_tx}")
        try:
            record = tx.run(
                upsert_tx,
                {
                    "pmcid": pmcid,
                    "affiliation_id": affiliation.affiliation_id,
                    "location": affiliation.location,
                    "emails": get_or_default_list(affiliation.emails),
                },
            ).single()
            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["affiliation.affiliation_id"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert, exception)
            raise
