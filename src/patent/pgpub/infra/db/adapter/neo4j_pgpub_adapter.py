import itertools
import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.util import (
    ensure_connection,
    get_or_default_list,
    get_or_default_ndarray,
    get_or_default_set,
)
from patent.pgpub.model.pgpub import Pgpub
from patent.application.infra.db.const import USPTO_APPLICATION_NODE_TYPE
from patent.pgpub.infra.db.const import (
    USPTO_PGPUB_NODE_TYPE,
    USPTO_PGPUB_PATENT_REL_TYPE,
)

logger = logging.getLogger(__name__)


class Neo4jPgpubAdapter:
    """
    Adapter to perform operations on uspto patent pgpub associated documents nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert(self, pgpub: Pgpub) -> str | None:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                node_id = self._upsert(
                    tx=tx,
                    pgpub=pgpub,
                )

        logger.info(f"upserted pgpub document: {pgpub.application_number_text}")
        return node_id

    def _upsert(self, tx: Transaction, pgpub: Pgpub) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert = """
            MERGE (pgpub:`%s` {
                application_number_text: $application_number_text
            })
            ON MATCH
                SET pgpub.file_location_uri = $file_location_uri,
                    pgpub.file_create_dtg = $file_create_dtg,
                    pgpub.refresh_date = datetime(),
                    pgpub.abstract = $abstract,
                    pgpub.description = $description,
                    pgpub.claims = $claims,
                    pgpub.organizations = $organizations,
                    pgpub.chemical_compound_synonyms = $chemical_compound_synonyms,
                    pgpub.embeddings = $embeddings
            ON CREATE
                SET pgpub.file_location_uri = $file_location_uri,
                    pgpub.file_create_dtg = $file_create_dtg,
                    pgpub.refresh_date = datetime(),
                    pgpub.abstract = $abstract,
                    pgpub.description = $description,
                    pgpub.claims = $claims,
                    pgpub.organizations = $organizations,
                    pgpub.chemical_compound_synonyms = $chemical_compound_synonyms,
                    pgpub.embeddings = $embeddings,
                    pgpub.is_uspto = true
            """ % (
            USPTO_PGPUB_NODE_TYPE
        )

        link_upserts = []
        if (
            pgpub.application_number_text is not None
            and int(pgpub.application_number_text) > 0
        ):
            link_upserts = [
                """
                WITH pgpub
                MATCH (application:`%s` { application_number_text: $application_number_text })
                ON MATCH
                    SET application.refresh_date = datetime(),
                ON CREATE
                    SET application.refresh_date = datetime(),
                        application.is_uspto = true
                MERGE (application)-[r1:`%s` { is_uspto: true }]-(pgpub)
                """
                % (USPTO_APPLICATION_NODE_TYPE, USPTO_PGPUB_PATENT_REL_TYPE)
            ]

        upsert_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [upsert],
                        link_upserts,
                        ["RETURN pgpub.application_number_text, pgpub.refresh_date"],
                    ]
                )
            )
        )

        logger.debug(f"upsert: {upsert_tx}")
        try:

            record = tx.run(
                upsert_tx,
                {
                    "application_number_text": pgpub.application_number_text,
                    "file_location_uri": pgpub.pgpub_metadata.file_location_uri,
                    "file_create_dtg": pgpub.pgpub_metadata.file_create_dtg,
                    "abstract": pgpub.abstract,
                    "description": "".join(get_or_default_list(pgpub.description)),
                    "claims": get_or_default_list(pgpub.claims),
                    "organizations": get_or_default_set(pgpub.organizations),
                    "chemical_compound_synonyms": get_or_default_set(
                        pgpub.chemical_compound_synonyms
                    ),
                    "embeddings": get_or_default_ndarray(pgpub.embeddings),
                },
            ).single()
            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["pgpub.application_number_text"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert, exception)
            raise
