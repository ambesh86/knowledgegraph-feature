import logging
from argparse import Namespace
from pathlib import Path

from dotenv import load_dotenv

from centree.conf.conf import (
    centree_csv_export_provider,
)
from annotation.timer_annotation import log_time
from centree.model.theraputic_area import TherapeuticArea

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    export a centree projects json file into a projects csv file
    """
    load_dotenv()

    args = build_args()
    projects_json = Path(args.projects_json)
    out_file = Path(args.out)

    therapeutic_areas = _load_therapeutic_areas(lookup_dir=Path(args.therapeutic_areas))
    _convert_projects_file(
        projects_json_file=projects_json,
        out_file=out_file,
        therapeutic_areas=therapeutic_areas,
    )


@log_time
def _load_therapeutic_areas(lookup_dir: Path) -> dict[str, TherapeuticArea]:
    from centree.provider.theraputic_areas_loader import TherepeuticAreasLoader
    from centree.conf.conf import therapeutic_area_mapper

    therapeutic_areas_loader = TherepeuticAreasLoader(
        therapeutic_area_mapper=therapeutic_area_mapper()
    )
    therapeutic_areas = therapeutic_areas_loader.load(lookup_dir=lookup_dir)
    if therapeutic_areas is None:
        raise ValueError("No therapeutic areas lookup values found!")
    logger.info(f"loaded {len(therapeutic_areas.keys())} therapeutic areas")
    return therapeutic_areas


@log_time
def _convert_projects_file(
    projects_json_file: Path,
    out_file: Path,
    therapeutic_areas: dict[str, TherapeuticArea],
) -> None:
    logger.info(f"minimize fields set as: {projects_json_file}")

    csv_export_provider = centree_csv_export_provider(
        therapeutic_areas=therapeutic_areas
    )
    csv_export_provider.export(json_file=projects_json_file, out_file=out_file)
    logger.info(f"Done exporting to {out_file}")


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="convert centree projects json file into csv")
    parser.add_argument(
        "--projects-json",
        type=str,
        default="./resources/data/centree/projects",
        required=False,
        help="directory to read data file",
    )

    parser.add_argument(
        "--therapeutic-areas",
        type=str,
        default="./resources/data/centree/lookup/therapeutic_areas",
        required=False,
        help="directory to read lookup files for therapeutic areas",
    )

    parser.add_argument(
        "--out",
        type=str,
        default="./output/export/centree/projects.csv",
        required=False,
        help="csv file to output converted projects json files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
