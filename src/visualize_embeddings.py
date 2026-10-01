import logging

from argparse import Namespace
from dotenv import load_dotenv

from foundation.conf.conf import list_embeddings_provider
from foundation.model.foundational_node_enum import FoundationalNodeEnum


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    generate tsv needed to visualize embeddings stored in the euGENE graph
    """
    load_dotenv()

    args = build_args()
    node_labels = []
    for label in args.include:
        node_labels.append(string_to_enum(label))
    generate_tsv(
        graph_embeddings=args.graph_embeddings,
        sentence_embeddings=args.sentence_embeddings,
        labels=node_labels,
    )


def generate_tsv(
    graph_embeddings: bool,
    sentence_embeddings: bool,
    labels: list[FoundationalNodeEnum],
) -> None:
    list_provider = list_embeddings_provider()
    if graph_embeddings:
        list_provider.write_all_graph_embeddings_by_labels(labels=labels)
    if sentence_embeddings:
        list_provider.write_all_sentence_embeddings_by_labels(labels=labels)


def build_args() -> Namespace:
    import argparse
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="generate tsv to visualize embeddings stored into euGENE"
    )
    parser.add_argument(
        "--graph-embeddings",
        action=argparse.BooleanOptionalAction,
        help="generate tsv for graph embeddings",
    )
    parser.add_argument(
        "--sentence-embeddings",
        action=argparse.BooleanOptionalAction,
        help="generate tsv for sentence embeddings",
    )
    parser.add_argument(
        "--include",
        nargs="+",
        type=str,
        required=False,
        help="node labels to include in tsv",
    )
    return parser.parse_args()


def string_to_enum(label: str):
    try:
        return FoundationalNodeEnum[label.upper()]
    except KeyError:
        raise ValueError(f"'{label}' is not a valid FoundationalNodeEnum")


if __name__ == "__main__":
    main()
