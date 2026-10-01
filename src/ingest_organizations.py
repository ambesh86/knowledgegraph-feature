import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from organization.conf.conf import (
    organization_ingest_orchestrator,
)
from annotation.timer_annotation import log_time

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    ingest the organization resolutions and store and link the data in the euGENE graph
    """
    load_dotenv()

    args = build_args()
    checkpoint_dir = Path(args.checkpoint_basedir)
    _ingest_resolution_checkpoint_dir(checkpoint_dir=checkpoint_dir)


@log_time
def _ingest_resolution_checkpoint_dir(checkpoint_dir: Path) -> None:
    orchestrator = organization_ingest_orchestrator()
    ids = orchestrator.ingest(checkpoint_dir=checkpoint_dir)
    logger.info(f"Loaded and ingested {len(ids)} unique organization(s)")


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="organization resolution json files. Store and link the data into euGENE"
    )
    parser.add_argument(
        "--checkpoint-basedir",
        type=str,
        default="./output/checkpoint/organization",
        required=False,
        help="directory to read checkpoint files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
