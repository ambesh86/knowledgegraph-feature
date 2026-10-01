import logging

from argparse import Namespace
from dotenv import load_dotenv

from patent.conf.orchestator import patent_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    download uspto patent applications, store and link the data in the euGENE graph
    """
    load_dotenv()

    args = build_args()
    max_applications = args.max_applications
    with_linking = args.linking

    orchestrator = patent_orchestrator()
    orchestrator.process(max_applications, with_analysis_and_linking=with_linking)


def build_args() -> Namespace:
    import argparse
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Download recent USPTO medical pregrant patent applications. Store and link the data into euGENE"
    )
    parser.add_argument(
        "--max-applications",
        type=int,
        default=25,
        required=False,
        help="max number of patents to load",
    )
    parser.add_argument(
        "--linking",
        action=argparse.BooleanOptionalAction,
        help="should analyze text and link pgpub to base euGENE graph",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
