import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from organization.conf.conf import (
    organization_export_orchestrator,
)
from annotation.timer_annotation import log_time

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    export the organization resolution checkpoints to a specified csv file
    """
    load_dotenv()

    args = build_args()
    checkpoint_dir = Path(args.checkpoint_basedir)
    out_file = Path(args.out)
    _export_resolution_checkpoint_dir(
        checkpoint_dir=checkpoint_dir,
        out_file=out_file,
        minimize_fields=args.minimize_fields,
    )


@log_time
def _export_resolution_checkpoint_dir(
    checkpoint_dir: Path, out_file: Path, minimize_fields: bool
) -> None:
    logger.info(f"minimize fields set as: {minimize_fields}")
    orchestrator = organization_export_orchestrator()
    ids = orchestrator.export(
        checkpoint_dir=checkpoint_dir,
        out_file=out_file,
        minimize_fields=minimize_fields,
    )
    logger.info(f"Loaded and exported {len(ids)} unique organization(s)")


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

    parser.add_argument(
        "--out",
        type=str,
        default="./output/export/organization/org_names.csv",
        required=False,
        help="csv file to export checkpoint files",
    )

    parser.add_argument(
        "--minimize-fields",
        required=False,
        action="store_true",
        help="just use spelling variations and remove acquisitions",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
