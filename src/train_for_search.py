import logging
from argparse import Namespace

from dotenv import find_dotenv, load_dotenv

from tpp.conf.conf import similarity_search_orchestrator
from tpp.conf.training_conf import tpp_patent_train_orchestrator


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    project, train and index embeddings in the euGENE graph
    """
    load_env()

    args = build_args()

    dimension_size = args.dimension_size
    train_orchestrator = tpp_patent_train_orchestrator()
    train_orchestrator.train_for_search(embedding_dimension=dimension_size)
    similarity_orchestrator = similarity_search_orchestrator()
    similarity_orchestrator.project_for_similarity_search()


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="project, train and index embeddings in the euGENE graph"
    )
    parser.add_argument(
        "--dimension-size",
        type=int,
        default=512,
        required=False,
        help="dimension size to use for training and indexing embeddings",
    )

    return parser.parse_args()


def load_env() -> None:
    # Attempt to find the .env file, but don't raise an error if it's not found
    dotenv_path = find_dotenv(raise_error_if_not_found=False)
    logger.info(".env file {dotenv_path}")

    if dotenv_path:
        load_dotenv(dotenv_path, verbose=True)
    else:
        logger.warning(".env file not found")


if __name__ == "__main__":
    main()
