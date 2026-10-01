import itertools
import logging
from typing import Callable

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError
from numpy import ndarray

from graph.util.util import (
    ensure_connection,
    get_or_default,
    get_or_default_ndarray,
)
from patent.pgpub.infra.db.const import (
    USPTO_PGPUB_EMBEDDINGS_INDEX_NAME,
    USPTO_PGPUB_NODE_TYPE,
)
from patent.pgpub.infra.db.model.pgpub_embedding_search_result import (
    PgpubEmbeddingSearchResult,
)

logger = logging.getLogger(__name__)


class Neo4jPgpubSearchAdapter:
    """
    Adapter to perform searches on a patent application pgpub (pregrant) in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_by_application_number(self, application_number: str) -> str | None:
        """
        find the pgpub node in the database with the given application_number
        return the application_number if found otherwise return None
        """
        if application_number is None:
            return None
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                return self._find_by_application_number(tx, application_number)

    def find_by_embeddings(
        self, embeddings: ndarray | None
    ) -> list[PgpubEmbeddingSearchResult] | None:
        if embeddings is None:
            return None
        ensure_connection(self.driver)

        return self._wrap_tx(query=self._find_by_embeddings, embeddings=embeddings)

    def _find_by_application_number(
        self, tx: Transaction, application_number: str
    ) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        search_by_id = f"""
        MATCH (node:`{USPTO_PGPUB_NODE_TYPE}`)
        WHERE node.application_number_text = $application_number
        RETURN node.application_number_text as patent_application_no
        """
        logger.debug(f"search: {search_by_id}")
        try:
            record = tx.run(
                search_by_id,
                {
                    "application_number": get_or_default(application_number),
                },
            ).single()
            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["patent_application_no"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search_by_id, exception)
            raise

    def _find_by_embeddings(
        self, tx: Transaction, embeddings: ndarray
    ) -> list[PgpubEmbeddingSearchResult] | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        search_by_embeddings = self._generate_find_by_embeddings_query()
        search_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [search_by_embeddings],
                        [
                            "RETURN score, node.application_number_text as patent_application_no"
                        ],
                    ]
                )
            )
        )

        logger.debug(f"upsert: {search_tx}")
        try:
            records = tx.run(
                search_tx,
                {
                    "embeddings": get_or_default_ndarray(embeddings),
                },
            )
            if records is None:
                return None

            logger.debug(f"cypher response: {records}")

            results = []
            for record in records:
                logger.info(f"{record}")
                application_no = record["patent_application_no"]
                score = float(record["score"]) if "score" in record.keys() else 0.0
                results.append(
                    PgpubEmbeddingSearchResult(
                        score=score, application_no=application_no
                    )
                )
            logger.debug(f"{results}")
            return results
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search_by_embeddings, exception)
            raise

    def _generate_find_by_embeddings_query(self, limit: int = 200) -> str:
        return """
            WITH $embeddings as query
            CALL db.index.vector.queryNodes('%s', %s, query)
            YIELD node, score
            """ % (
            USPTO_PGPUB_EMBEDDINGS_INDEX_NAME,
            limit,
        )

    def _wrap_tx(
        self,
        query: Callable[
            [Transaction, ndarray], list[PgpubEmbeddingSearchResult] | None
        ],
        embeddings: ndarray,
    ) -> list[PgpubEmbeddingSearchResult] | None:
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                application_numbers = query(tx, embeddings)

        if application_numbers is None:
            return None
        logger.info(f"found {len(application_numbers)} application_number(s)")
        return application_numbers
