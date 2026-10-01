import itertools
import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.model.summary import Summary
from graph.util.util import ensure_connection, get_or_default
from patent.pgpub.infra.db.const import (
    USPTO_PGPUB_NODE_TYPE,
    USPTO_PGPUB_SUMMARY_FINDING_NODE_TYPE,
    USPTO_PGPUB_SUMMARY_FINDING_REL_TYPE,
    USPTO_PGPUB_SUMMARY_NODE_TYPE,
    USPTO_PGPUB_SUMMARY_REL_TYPE,
)

logger = logging.getLogger(__name__)


class Neo4jPgpubSummaryAdapter:
    """
    Adapter to perform operations uspto pgpub summary node in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert_summary(self, application_number: str, summary: Summary) -> str | None:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                summary_id = self._upsert_summary(
                    tx=tx, application_number=application_number, summary=summary
                )

        logger.info(f"merged {application_number} summary id: {summary_id}")

    def _upsert_summary(
        self, tx: Transaction, application_number: str, summary: Summary
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
            MATCH (application:`%s` { application_number_text: $application_number })
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
                    summary.is_uspto = true,
                    summary.title = $title,
                    summary.summary = $summary,
                    summary.rating = $rating,
                    summary.rating_explanation = $rating_explanation,
                    summary.level = $level,
                    summary.refresh_date = datetime()
            """ % (
            USPTO_PGPUB_NODE_TYPE,
            USPTO_PGPUB_SUMMARY_NODE_TYPE,
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
                USPTO_PGPUB_SUMMARY_FINDING_NODE_TYPE,
                finding.id,
                finding.summary,
                finding.explanation,
            )
            finding_upserts.append(finding_upsert)
            relationship_upsert = (
                "MERGE (summary)-[rel%s:`%s` { is_uspto: true }]-(finding%s) "
                % (
                    finding_count,
                    USPTO_PGPUB_SUMMARY_FINDING_REL_TYPE,
                    finding_count,
                )
            )
            summary_relationship_upserts.append(relationship_upsert)
            finding_count += 1

        link_article_upsert = """
            MERGE (application)-[article_rel:`%s` { is_uspto: true }]-(summary)
            """ % (
            USPTO_PGPUB_SUMMARY_REL_TYPE
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
                            "RETURN application.application_number_text, summary.summary_id, summary.refresh_date"
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
                    "application_number": application_number,
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
