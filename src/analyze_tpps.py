import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from infra.util.file_util import list_data_files
from tpp.conf.conf import tpp_orchestrator, tpp_patent_train_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    analyze the resources directory for tpp pptx files, parse them, and store and link the data in the euGENE graph
    """
    load_dotenv()

    args = build_args()
    resources_directory = args.resources_directory
    with_linking = args.linking

    orchestator = tpp_orchestrator()
    files = [Path(el) for el in list_data_files(resources_directory, {".pptx"})]
    orchestator.process_and_move(files=files, with_analysis_and_linking=with_linking)

    if args.train_embeddings:
        train_orchestrator = tpp_patent_train_orchestrator()
        train_orchestrator.train_for_search(embedding_dimension=512)


def build_args() -> Namespace:
    import argparse
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="analyze a directory for tpp pptx files. Store and link the data into euGENE"
    )
    parser.add_argument(
        "--resources-directory",
        type=str,
        default="./resources/data/tpp",
        required=False,
        help="directory of pptx tpp files to parse and load",
    )
    parser.add_argument(
        "--linking",
        action=argparse.BooleanOptionalAction,
        help="analyze tpp text and link results to base euGENE graph",
    )
    parser.add_argument(
        "--train-embeddings",
        action=argparse.BooleanOptionalAction,
        help="train and index tpp embeddings to search against uspto pregrant patents",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
