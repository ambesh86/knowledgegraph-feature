import logging

from numpy import ndarray

from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)

from tpp.infra.db.adapter.neo4j_tpp_search_adapter import Neo4jTppSearchAdapter
from tpp.infra.db.model.tpp_search_result import TppSearchResult
from tpp.model.question_type_enum import QuestionTypeEnum

logger = logging.getLogger(__name__)


class TppSearchOrchestrator:
    """
    class to orchestrator all the steps to parse, analyze and store tpp files
    """

    def __init__(
        self,
        neo4j_pgpub_search_adapter: Neo4jPgpubSearchAdapter,
        neo4j_tpp_search_adapter: Neo4jTppSearchAdapter,
    ):
        self.neo4j_pgpub_search_adapter = neo4j_pgpub_search_adapter
        self.neo4j_tpp_search_adapter = neo4j_tpp_search_adapter

    def find_patent_applications_by_embedding(
        self, embeddings: ndarray
    ) -> list[TppSearchResult] | None:
        if embeddings is None:
            return None

        results = self.neo4j_pgpub_search_adapter.find_by_embeddings(
            embeddings=embeddings
        )
        if results is None:
            return None

        tpp_results = []
        for result in results:
            logger.info(f"{result.score} {result.application_no}")
            current_tpp_result = TppSearchResult(
                score=result.score, application_no=result.application_no
            )
            tpp_results.append(current_tpp_result)

        return tpp_results

    def find_patent_applications_by_tpp(
        self, tpp_id: str
    ) -> list[TppSearchResult] | None:
        if tpp_id is None:
            return None

        results = self.neo4j_tpp_search_adapter.find_by_tpp(tpp_id=tpp_id)
        return results

    def find_patent_applications_by_tpp_and_graph_embeddings(
        self, tpp_id: str
    ) -> list[TppSearchResult] | None:
        if tpp_id is None:
            return None

        results = self.neo4j_tpp_search_adapter.find_by_tpp_and_graph_embeddings(
            tpp_id=tpp_id
        )
        return results

    def find_patent_applications_by_tpp_question(
        self, tpp_id: str, tpp_question: QuestionTypeEnum
    ) -> list[TppSearchResult] | None:
        if tpp_id is None or tpp_question is None:
            return None

        results = self.neo4j_tpp_search_adapter.find_by_tpp_question(
            tpp_id=tpp_id, question_type=tpp_question
        )
        return results
