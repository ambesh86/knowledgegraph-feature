import csv
import logging
from argparse import Namespace
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    lookup organization name to id
    """

    start_time = time.perf_counter()
    args = build_args()
    input_file = Path(args.input_file)
    mappings_file = Path(args.mappings_file)
    lookup_all_entries(input_file=input_file, mappings_file=mappings_file)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    logger.info(f"Elapsed time: {elapsed_time:.4f} seconds")


def lookup_all_entries(input_file: Path, mappings_file: Path):
    entries = load_input_file(input_file=input_file)
    logger.info(f"loaded {len(entries)} original organization names")
    mappings = load_mappings_file(mappings_file=mappings_file)
    logger.info(f"loaded {len(mappings)} organization mappings")
    lookup_map = build_name_to_id_lookup(mappings=mappings)

    missing_entry_count = 0
    for original_entry in entries:
        normalized_entry = original_entry.upper()
        if normalized_entry not in lookup_map:
            logger.warning(f"missing entry for {normalized_entry}")
            missing_entry_count += 1
            continue
        else:
            org_id = lookup_map[normalized_entry]
            logger.info(f"{original_entry} -> {org_id}")

    logger.info(f"looked up {len(entries)}")
    logger.info(f"missing entries {missing_entry_count}")


def load_input_file(
    input_file: Path,
) -> list[str]:
    entries = []
    logger.info(f"reading file {input_file}")
    with open(input_file, "r") as file:
        lines = file.readlines()
        for line in lines:
            entries.append(line.strip())
    return entries


def load_mappings_file(
    mappings_file: Path,
) -> list[dict[str, str]]:
    mappings = []
    logger.info(f"reading file {mappings_file}")
    with open(mappings_file, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            mappings.append(row)
    return mappings


def build_name_to_id_lookup(mappings: list[dict[str, str]]) -> dict[str, str]:
    return {
        element["organization_name"]: element["organization_id"] for element in mappings
    }


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="organization lookup script")
    parser.add_argument(
        "--input-file",
        type=str,
        default="./resources/data/organization/organizations.txt",
        required=False,
        help="file of organizations names",
    )

    parser.add_argument(
        "--mappings-file",
        type=str,
        default="./output/export/organization/org_mappings.csv",
        required=False,
        help="file with organization mappings and organization ids",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
