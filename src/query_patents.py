import logging

from argparse import ArgumentParser
from typing import Any
from dotenv import load_dotenv

from patent.conf.conf import semantic_search_embedding_provider
from tpp.infra.db.model.tpp_search_result import TppSearchResult
from tpp.model.question_type_enum import QuestionTypeEnum
from tpp.conf.conf import tpp_search_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    semantic search for patent applications in the euGENE graph
    """
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()
    if args.query_type:
        args.func(args)
    else:
        parser.print_help()


def find_by_embeddings(include_terms: str, exclude_terms: str) -> None:
    search_orchestrator = tpp_search_orchestrator()
    embedding_provider = semantic_search_embedding_provider()
    merged_embeddings = embedding_provider.to_embedding(
        include_terms=include_terms, exclude_terms=exclude_terms
    )
    results = search_orchestrator.find_patent_applications_by_embedding(
        merged_embeddings
    )
    print_results(results)


def find_by_tpp(tpp_id: str) -> None:
    search_orchestrator = tpp_search_orchestrator()
    results = search_orchestrator.find_patent_applications_by_tpp(tpp_id=tpp_id)
    print_results(results)


def find_by_tpp_and_graph_embeddings(tpp_id: str) -> None:
    search_orchestrator = tpp_search_orchestrator()
    results = search_orchestrator.find_patent_applications_by_tpp_and_graph_embeddings(
        tpp_id=tpp_id
    )
    print_results(results)


def find_by_tpp_question(tpp_id: str, question_type: QuestionTypeEnum) -> None:
    logger.info(f"find_by_tpp_question {tpp_id} {question_type.name}")
    search_orchestrator = tpp_search_orchestrator()
    results = search_orchestrator.find_patent_applications_by_tpp_question(
        tpp_id=tpp_id, tpp_question=question_type
    )
    print_results(results)


def print_results(results: list[TppSearchResult] | None) -> None:
    items = convert_results(results)
    if items is None:
        return None

    for item in items:
        logger.info(f"{item}")


def convert_results(results: list[TppSearchResult] | None) -> list[str] | None:
    if results is None:
        return None

    ids = []
    for result in results:
        ids.append(result.application_no)

    return ids


def build_parser() -> ArgumentParser:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="query patent applications in the euGENE graph")
    subparsers = parser.add_subparsers(
        title="Query Types", dest="query_type", help="types of queries for patents"
    )
    build_embeddings_args(subparsers)
    build_tpp_args(subparsers)
    build_tpp_question_args(subparsers)
    build_tpp_and_graph_embeddings_args(subparsers)

    return parser


def build_embeddings_args(subparsers: Any) -> None:
    embedding_args_parser = subparsers.add_parser(
        "query-embeddings", help="query patents based on embeddings"
    )
    embedding_args_parser.add_argument(
        "--include",
        type=str,
        required=True,
        help="query terms to include in the semantic search",
    )
    embedding_args_parser.add_argument(
        "--exclude",
        type=str,
        required=False,
        help="query terms to exclude in the semantic search",
    )
    embedding_args_parser.set_defaults(
        func=lambda args: find_by_embeddings(args.include, args.exclude)
    )


def build_tpp_args(subparsers: Any) -> None:
    tpp_args_parser = subparsers.add_parser(
        "query-tpp", help="query patents based on a given tpp id"
    )
    tpp_args_parser.add_argument(
        "--tpp-id",
        type=str,
        required=True,
        help="query tpp id to lookup to compare in the semantic search",
    )
    tpp_args_parser.set_defaults(func=lambda args: find_by_tpp(args.tpp_id))


def build_tpp_and_graph_embeddings_args(subparsers: Any) -> None:
    tpp_args_parser = subparsers.add_parser(
        "query-tpp-and-graph-embeddings",
        help="query patents based on a given tpp id and using a merged sentence and graph embeddings",
    )
    tpp_args_parser.add_argument(
        "--tpp-id",
        type=str,
        required=True,
        help="query tpp id to lookup to compare in the graph embeddings search",
    )
    tpp_args_parser.set_defaults(
        func=lambda args: find_by_tpp_and_graph_embeddings(args.tpp_id)
    )


def build_tpp_question_args(subparsers: Any) -> None:
    tpp_question_args_parser = subparsers.add_parser(
        "query-tpp-question",
        help="query patents based on a given tpp id and a specific question",
    )
    tpp_question_args_parser.add_argument(
        "--tpp-id",
        type=str,
        required=True,
        help="query tpp id to lookup to compare in the semantic search",
    )
    tpp_question_args_parser.add_argument(
        "--question",
        type=str,
        required=True,
        help="query tpp question type to lookup",
        choices=[
            QuestionTypeEnum.INDICATION.name.lower(),
            QuestionTypeEnum.CONTRAINDICATION.name.lower(),
            QuestionTypeEnum.MECHANISM_OF_ACTION.name.lower(),
            QuestionTypeEnum.ROUTE_OF_ADMINISTRATION.name.lower(),
            QuestionTypeEnum.EFFICACY.name.lower(),
            QuestionTypeEnum.SAFTEY_AND_TOLERABILITY.name.lower(),
            QuestionTypeEnum.COST_OF_GOODS_SOLD.name.lower(),
        ],
    )
    tpp_question_args_parser.set_defaults(
        func=lambda args: find_by_tpp_question(
            args.tpp_id, QuestionTypeEnum[args.question.upper()]
        )
    )


if __name__ == "__main__":
    main()
