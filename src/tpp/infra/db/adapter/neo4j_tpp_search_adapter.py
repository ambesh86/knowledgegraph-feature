import itertools
import logging
from typing import Callable

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from patent.pgpub.infra.db.const import (
    USPTO_PGPUB_EMBEDDINGS_INDEX_NAME,
    USPTO_PGPUB_GRAPH_EMBEDDINGS_INDEX_NAME,
)
from foundation.conf.const import EMBEDDINGS_FIELD_NAME, GRAPH_EMBEDDINGS_FIELD_NAME
from tpp.model.question_type_enum import QuestionTypeEnum
from tpp.infra.db.model.tpp_search_result import TppSearchResult

logger = logging.getLogger(__name__)


class Neo4jTppSearchAdapter:
    """
    Adapter to perform searches on a target product profile (tpp) in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_by_tpp(self, tpp_id: str | None) -> list[TppSearchResult] | None:
        if tpp_id is None:
            return None

        return self._wrap_tx(query=self._find_by_tpp, tpp_id=tpp_id)

    def find_by_tpp_question(
        self, tpp_id: str | None, question_type: QuestionTypeEnum
    ) -> list[TppSearchResult] | None:
        if tpp_id is None:
            return None

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                application_numbers = self._find_by_tpp_question(
                    tx, tpp_id, question_type
                )

        if application_numbers is None:
            return None
        logger.info(f"found {len(application_numbers)} application_number(s)")
        return application_numbers

    def find_by_tpp_and_graph_embeddings(
        self, tpp_id: str | None
    ) -> list[TppSearchResult] | None:
        if tpp_id is None:
            return None

        return self._wrap_tx(
            query=self._find_by_tpp_and_graph_embeddings, tpp_id=tpp_id
        )

    def _find_by_tpp(
        self, tx: Transaction, tpp_id: str
    ) -> list[TppSearchResult] | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        search_by_tpp_id = self._generate_find_by_tpp_id_query()
        search_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [search_by_tpp_id],
                    ]
                )
            )
        )

        logger.debug(f"search: {search_tx}")
        try:
            records = tx.run(
                search_tx,
                {
                    "node_id": tpp_id,
                },
            )
            if records is None:
                return None

            logger.info(f"cypher response: {records}")

            return self._convert_results(records)
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search_by_tpp_id, exception)
            raise

    def _find_by_tpp_question(
        self, tx: Transaction, tpp_id: str, question_type: QuestionTypeEnum
    ) -> list[TppSearchResult] | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        search_by_tpp_question = self._generate_find_by_tpp_question_query(
            question_type=question_type
        )
        search_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [search_by_tpp_question],
                    ]
                )
            )
        )

        logger.debug(f"search: {search_tx}")
        try:
            records = tx.run(
                search_tx,
                {
                    "node_id": tpp_id,
                },
            )
            if records is None:
                return None

            logger.info(f"cypher response: {records}")

            return self._convert_results(records)
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search_by_tpp_question, exception)
            raise

    def _find_by_tpp_and_graph_embeddings(
        self, tx: Transaction, tpp_id: str
    ) -> list[TppSearchResult] | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        search_by_tpp_id = self._generate_find_by_tpp_id_and_graph_embeddings_query()
        search_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [search_by_tpp_id],
                    ]
                )
            )
        )

        logger.debug(f"search: {search_tx}")
        try:
            records = tx.run(
                search_tx,
                {
                    "node_id": tpp_id,
                },
            )
            if records is None:
                return None

            logger.info(f"cypher response: {records}")

            return self._convert_results(records)
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search_by_tpp_id, exception)
            raise

    def _generate_find_by_tpp_id_query(self, limit: int = 200) -> str:
        return """
            MATCH (tpp:csl_tpp { node_id: $node_id })
            CALL db.index.vector.queryNodes('%s', %s, tpp.%s)
            YIELD node, score
            RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims
            """ % (
            USPTO_PGPUB_EMBEDDINGS_INDEX_NAME,
            limit,
            EMBEDDINGS_FIELD_NAME,
        )

    def _generate_find_by_tpp_question_query(
        self, question_type: QuestionTypeEnum, limit: int = 200
    ) -> str:
        return """
            MATCH (tpp:csl_tpp { node_id: $node_id })-[:has_associated_question]-(tpp_question:csl_tpp_question { question_type: '%s'})
            CALL db.index.vector.queryNodes('%s', %s, tpp_question.%s)
            YIELD node, score
            RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims
            """ % (
            question_type.name.upper(),
            USPTO_PGPUB_EMBEDDINGS_INDEX_NAME,
            limit,
            EMBEDDINGS_FIELD_NAME,
        )

    def _generate_find_by_tpp_id_and_graph_embeddings_query(
        self, limit: int = 200
    ) -> str:
        return """
            MATCH (tpp:csl_tpp { node_id: $node_id })
            CALL db.index.vector.queryNodes('%s', %s, tpp.%s)
            YIELD node, score
            RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;
        """ % (
            USPTO_PGPUB_GRAPH_EMBEDDINGS_INDEX_NAME,
            limit,
            GRAPH_EMBEDDINGS_FIELD_NAME,
        )

    def _wrap_tx(
        self,
        query: Callable[
            [Transaction, str],
            list[TppSearchResult] | None,
        ],
        tpp_id: str,
    ) -> list[TppSearchResult] | None:
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                application_numbers = query(tx, tpp_id)

        if application_numbers is None:
            return None
        logger.info(f"found {len(application_numbers)} application_number(s)")
        return application_numbers

    def _convert_results(self, records) -> list[TppSearchResult]:
        results = []
        for record in records:
            logger.debug(f"{record}")
            application_no = record["patent_application_no"]
            score = float(record["score"])
            tpp_description = record["tpp_description"]
            abstract = record["patent_abstract"]
            claims = record["patent_claims"]
            results.append(
                TppSearchResult(
                    score=score,
                    application_no=application_no,
                    product_description=tpp_description,
                    abstract=abstract,
                    claims=claims,
                )
            )
        return results
