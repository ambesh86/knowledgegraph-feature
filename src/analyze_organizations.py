import logging
from argparse import Namespace
from pathlib import Path
import time

from dotenv import load_dotenv

from organization.conf.conf import organization_resolution_orchestrator
from organization.writer.checkpoint_file_name_generator import (
    CheckpointFilenameGenerator,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    analyze the a list of organizations, resolve organization aliases, and store the data in checkpoint files
    """
    load_dotenv()

    args = build_args()
    resource_file = Path(args.resource_file)
    checkpoint_dir = Path(args.checkpoint_basedir)
    _load_and_analyze_organizations(
        resource_file=resource_file, checkpoint_dir=checkpoint_dir
    )


def _load_and_analyze_organizations(resource_file: Path, checkpoint_dir: Path) -> None:
    start_time = time.time()
    organizations = _read_organizations(organizations_path=resource_file)
    orchestator = organization_resolution_orchestrator()
    checkpoint_filename_generator = CheckpointFilenameGenerator(
        checkpoint_root=checkpoint_dir, data_type_prefix="organization"
    )
    orchestator.analyze_organizations(
        organizations=organizations,
        checkpoint_filename_generator=checkpoint_filename_generator,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(
        f"Analyzed {len(organizations)} unique organization name(s) in elapsed time: {elapsed_time:.6f} seconds"
    )


def _read_organizations(organizations_path: Path) -> set[str]:
    organizations = set()
    with open(organizations_path, "r") as file:
        lines = file.readlines()
        for line in lines:
            name = line.strip()
            logger.debug(f"{name}")
            organizations.add(name)
    logger.info(
        f"read {len(organizations)} unique organization names from {organizations_path}"
    )
    return organizations


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="analyze organization names. Store the data in checkpoint files"
    )
    parser.add_argument(
        "--resource-file",
        type=str,
        default="./resources/data/organization/organizations.txt",
        required=False,
        help="files of organization names to analyze, the file should contain a list of names one name per line",
    )
    parser.add_argument(
        "--checkpoint-basedir",
        type=str,
        default="./output/checkpoint",
        required=False,
        help="directory to write checkpoint file",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
