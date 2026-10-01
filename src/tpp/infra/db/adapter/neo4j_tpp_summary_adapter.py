import itertools
import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.model.summary import Summary
from graph.util.util import ensure_connection, get_or_default
from tpp.infra.db.const import (
    TPP_NODE_PRIMARY_KEY,
    TPP_NODE_TYPE,
    TPP_SUMMARY_FINDING_NODE_TYPE,
    TPP_SUMMARY_FINDING_REL_TYPE,
    TPP_SUMMARY_NODE_TYPE,
    TPP_SUMMARY_REL_TYPE,
)

logger = logging.getLogger(__name__)


class Neo4jTppSummaryAdapter:
    """
    Adapter to perform operations uspto pgpub summary node in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert_summary(self, tpp_id: str, summary: Summary) -> str | None:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                summary_id = self._upsert_summary(tx=tx, tpp_id=tpp_id, summary=summary)

        logger.info(f"merged tpp {tpp_id} and summary id: {summary_id}")

    def _upsert_summary(
        self, tx: Transaction, tpp_id: str, summary: Summary
    ) -> str | None:
        """
        upsert given summary and findings objects, link it to the existing node identified by application_id
        return the new summary id
        """

        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        # TODO: refactor this to reuse summary related query and param building

        upsert = """
            MATCH (tpp:`%s` { %s: $tpp_id })
            MERGE (summary:`%s` {
                summary_id: $summary_id
            })
            ON MATCH
                SET summary.title = $title,
                    summary.summary = $summary,
                    summary.rating = $rating,
                    summary.rating_explanation = $rating_explanation,
                    summary.level = $level,
                    summary.refresh_date = datetime()
            ON CREATE
                SET summary.summary_id = $summary_id,
                    summary.is_csl = true,
                    summary.title = $title,
                    summary.summary = $summary,
                    summary.rating = $rating,
                    summary.rating_explanation = $rating_explanation,
                    summary.level = $level,
                    summary.refresh_date = datetime()
            """ % (
            TPP_NODE_TYPE,
            TPP_NODE_PRIMARY_KEY,
            TPP_SUMMARY_NODE_TYPE,
        )
        finding_upserts = []
        summary_relationship_upserts = []
        finding_count = 1
        for finding in summary.findings:
            finding_upsert = """
                MERGE (finding%s:`%s` {
                        finding_id: "%s",
                        summary: "%s",
                        explanation: "%s" 
                }) 
                """ % (
                finding_count,
                TPP_SUMMARY_FINDING_NODE_TYPE,
                finding.id,
                finding.summary,
                finding.explanation,
            )
            finding_upserts.append(finding_upsert)
            relationship_upsert = (
                "MERGE (summary)-[rel%s:`%s` { is_csl: true }]-(finding%s) "
                % (
                    finding_count,
                    TPP_SUMMARY_FINDING_REL_TYPE,
                    finding_count,
                )
            )
            summary_relationship_upserts.append(relationship_upsert)
            finding_count += 1

        link_article_upsert = """
            MERGE (tpp)-[article_rel:`%s` { is_csl: true }]-(summary)
            """ % (
            TPP_SUMMARY_REL_TYPE
        )

        upsert_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [upsert],
                        finding_upserts,
                        summary_relationship_upserts,
                        [link_article_upsert],
                        [
                            "RETURN tpp.node_id, summary.summary_id, summary.refresh_date"
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
                    "tpp_id": tpp_id,
                    "summary_id": summary.id,
                    "level": get_or_default(summary.level),
                    "title": get_or_default(summary.title),
                    "summary": get_or_default(summary.summary),
                    "rating": get_or_default(summary.rating),
                    "rating_explanation": get_or_default(summary.rating_explanation),
                },
            ).single()
            logger.debug(f"cypher response: {record}")

            if record is None:
                return None
            return record["summary.summary_id"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert, exception)
            raise
