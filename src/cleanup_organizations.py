import logging
import time
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from annotation.timer_annotation import log_time
from organization.conf.conf import (
    organization_resolution_cleanup_orchestrator,
)
from organization.writer.checkpoint_file_name_generator import (
    CheckpointFilenameGenerator,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    cleanup organization resolution checkpoint directory, filters unwanted or bad data
    """
    load_dotenv()

    args = build_args()
    checkpoint_dir = Path(args.checkpoint_basedir)
    output_basedir = args.output_basedir
    _filter_resolution_checkpoint_dir(
        checkpoint_dir=checkpoint_dir,
        output_basedir=output_basedir,
    )


@log_time
def _filter_resolution_checkpoint_dir(
    checkpoint_dir: Path, output_basedir: str
) -> None:
    start_time = time.time()
    checkpoint_filename_generator = CheckpointFilenameGenerator(
        checkpoint_root=checkpoint_dir, data_type_prefix=output_basedir
    )
    orchestrator = organization_resolution_cleanup_orchestrator()
    orchestrator.clean_and_copy_checkpoint(
        checkpoint_paths=[checkpoint_dir],
        checkpoint_filename_generator=checkpoint_filename_generator,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(
        f"Analyzed {checkpoint_dir} in elapsed time: {elapsed_time:.6f} seconds"
    )


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="cleanup and filter bad organization resolution json files. Store clean data to new directory"
    )
    parser.add_argument(
        "--checkpoint-basedir",
        type=str,
        default="./output/checkpoint/organization",
        required=False,
        help="directory to read checkpoint files",
    )

    parser.add_argument(
        "--output-basedir",
        type=str,
        default="filtered-organizations",
        required=False,
        help="directory to read checkpoint files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
