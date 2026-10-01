import logging

from argparse import Namespace
from pathlib import Path
from dotenv import load_dotenv

from patent.conf.orchestator import patent_orchestrator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    download uspto patent applications, store them on disk
    """
    load_dotenv()

    args = build_args()
    orchestrator = patent_orchestrator()
    orchestrator.download(args.max_applications, prefix_path=args.output)


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Download recent USPTO medical pregrant patent applications. Store on disk"
    )
    parser.add_argument(
        "--max-applications",
        type=int,
        default=25,
        required=False,
        help="max number of patents to load",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/data"),
        required=False,
        help="output directory",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
