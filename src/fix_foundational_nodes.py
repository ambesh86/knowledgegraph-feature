from argparse import ArgumentParser
import logging

from dotenv import load_dotenv

from foundation.conf.conf import foundational_node_fix_orchestrator


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    update eugene foundational graph nodes
    """

    parser = gen_arg_parser()
    args = parser.parse_args()

    load_dotenv()

    if args.fix_nodes:
        fix_nodes(args.fix_nodes)


def fix_nodes(labels: list[str]) -> None:
    logger.info(f"fixing labels {labels}")
    orchestrator = foundational_node_fix_orchestrator()
    orchestrator.fix_all(labels)


def gen_arg_parser() -> ArgumentParser:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Updated existing foundational graph nodes. Adds embeddings"
    )
    parser.add_argument(
        "--fix-nodes", nargs="+", type=str, required=False, help="node labels to update"
    )
    return parser


if __name__ == "__main__":
    main()
