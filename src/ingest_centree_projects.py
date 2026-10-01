import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from annotation.timer_annotation import log_time
from centree.conf.conf import csv_loader, neo4j_centree_project_ingest_adapter

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    ingest the centree projects and store in the euGENE graph
    """
    load_dotenv()

    args = build_args()
    projects_dir = Path(args.centree_projects_file)
    _ingest_projects_dir(projects_dir=projects_dir)


@log_time
def _ingest_projects_dir(projects_dir: Path) -> None:
    project_loader = csv_loader()
    ingest_adapter = neo4j_centree_project_ingest_adapter()
    projects = project_loader.load(
        file_path=projects_dir,
    )

    ids = []
    for project in projects:
        id = ingest_adapter.upsert_project(project)
        ids.append(id)
    logger.info(f"Loaded and ingested {len(ids)} unique projects(s)")


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="centree project json files. Store the data into euGENE"
    )
    parser.add_argument(
        "--centree-projects-file",
        type=str,
        default="./output/export/centree/projects/centree_projects.csv",
        required=False,
        help="directory to read centree project files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
