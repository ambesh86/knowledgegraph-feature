import itertools
import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.util import (
    ensure_connection,
    get_or_default_int,
    get_or_default_set,
)
from patent.application.infra.db.const import (
    USPTO_APPLICATION_PATENT_REL_TYPE,
    USPTO_APPLICATION_NODE_TYPE,
)
from patent.application.model.application import Application

logger = logging.getLogger(__name__)


class Neo4jApplicationAdapter:
    """
    Adapter to perform operations on uspto application nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert(self, application: Application) -> str | None:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                node_id = self._upsert(
                    tx=tx,
                    application=application,
                )

        logger.info(f"upserted application: {application.application_number_text}")
        return node_id

    def _upsert(self, tx: Transaction, application: Application) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert = """
            MERGE (application:`%s` {
                application_number_text: $application_number_text
            })
            ON MATCH
                SET application.invention_title = $invention_title,
                    application.first_applicant_name = $first_applicant_name,
                    application.refresh_date = datetime(),
                    application.applicants = $applicants,
                    application.application_status_description_text = $application_status_description_text,
                    application.application_status_code = $application_status_code,
                    application.customer_number = $customer_number,
                    application.application_type_code = $application_type_code,
                    application.application_type_label_name = $application_type_label_name,
                    application.cpc_classifications = $cpc_classifications,
                    application.application_status_date = $application_status_date,
                    application.effective_filing_date = $effective_filing_date,
                    application.filing_date = $filing_date,
                    application.patent_number = $patent_number,
                    application.grant_date = $grant_date
            ON CREATE
                SET application.invention_title = $invention_title,
                    application.first_applicant_name = $first_applicant_name,
                    application.refresh_date = datetime(),
                    application.applicants = $applicants,
                    application.application_status_description_text = $application_status_description_text,
                    application.application_status_code = $application_status_code,
                    application.customer_number = $customer_number,
                    application.application_type_code = $application_type_code,
                    application.application_type_label_name = $application_type_label_name,
                    application.cpc_classifications = $cpc_classifications,
                    application.application_status_date = $application_status_date,
                    application.effective_filing_date = $effective_filing_date,
                    application.filing_date = $filing_date,
                    application.patent_number = $patent_number,
                    application.grant_date = $grant_date,
                    application.is_uspto = true
            """ % (
            USPTO_APPLICATION_NODE_TYPE
        )

        link_upserts = []
        if application.patent_number is not None and application.patent_number > 0:
            link_upserts = [
                """
                WITH application
                MATCH (patent:patent { patent_no: $patent_number })
                MERGE (patent)-[r1:`%s` { is_uspto: true }]-(application)
                """
                % (USPTO_APPLICATION_PATENT_REL_TYPE)
            ]

        upsert_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [upsert],
                        link_upserts,
                        [
                            "RETURN application.application_number_text, application.refresh_date"
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
                    "application_number_text": application.application_number_text,
                    "invention_title": application.invention_title,
                    "first_applicant_name": application.first_applicant_name,
                    "applicants": get_or_default_set(application.applicants),
                    "application_status_description_text": application.application_status_description_text,
                    "application_status_code": application.application_status_code,
                    "customer_number": application.customer_number,
                    "application_type_code": application.application_type_code,
                    "application_type_label_name": application.application_type_label_name,
                    "cpc_classifications": get_or_default_set(
                        application.cpc_classifications
                    ),
                    "application_status_date": application.application_status_date,
                    "effective_filing_date": application.effective_filing_date,
                    "patent_number": get_or_default_int(application.patent_number),
                    "filing_date": application.filing_date,
                    "grant_date": application.grant_date,
                },
            ).single()
            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["application.application_number_text"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert, exception)
            raise
