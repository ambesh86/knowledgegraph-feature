import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from annotation.timer_annotation import log_time
from centree.conf.conf import (
    csv_loader,
)
from infra.util.file_util import list_data_files
from centree.model.stage0_project import Stage0Project

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    print a centree rdcode from the projects csv files
    """
    load_dotenv()

    args = build_args()
    projects_csv_dir = Path(args.projects_csv_dir)
    projects = _load_projects(lookup_dir=projects_csv_dir)
    _print_rdcodes(projects=projects)


@log_time
def _load_projects(lookup_dir: Path) -> list[Stage0Project]:
    logger.info(f"loading centree projects from dir: {lookup_dir}")
    loader = csv_loader()
    csv_file_names = list_data_files(data_dir=lookup_dir, file_extensions={".csv"})
    projects = []
    for csv_file in csv_file_names:
        logger.info(f"loading centree projects from file: {csv_file}")
        projects.extend(loader.load(file_path=Path(csv_file)))
    logger.info(f"total centree projects loaded: {len(projects)}")
    return projects


@log_time
def _print_rdcodes(projects: list[Stage0Project]):
    projects.sort(key=lambda x: x.eln_rd_codes[0] if x.eln_rd_codes else "")
    for project in projects:
        if project.eln_rd_codes is None or len(project.eln_rd_codes) == 0:
            continue
        for rdcode in project.eln_rd_codes:
            if rdcode is None:
                continue
            rdcode = rdcode.strip()
            if rdcode == "":
                continue
            print(f"{rdcode},{project.primary_label}")


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="convert centree projects json file into csv")
    parser.add_argument(
        "--projects-csv-dir",
        type=str,
        default="./output/export/centree/projects",
        required=False,
        help="directory to read data file",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
