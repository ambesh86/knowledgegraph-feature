import csv
import logging
from pathlib import Path
from typing import Optional

from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.relationship_mapper import RelationshipMapper
from infra.util.file_util import list_data_files

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

rel_mapper = RelationshipMapper()
entities_mapper = EntityMapper()


def main():
    data_root = Path("./output")
    data_dirs = [
        "eb9fa170776163c7800d97c5709bb122",
        "01681224922d6072340533cd82bedc4b",
        "0223be7bb7cfc12ffab1529a7f30222a",
        "0fccb6e52d957dbcadedcb75da16fd0a",
        "19e024b4954abfc429b19754155fada9",
        "3b0d53965cc7d53b6d0bcf8e4e3b4a66",
        "5cb17ba0e0a201abc979aac1bca9d67c.leiden",
        "6546cfe5d088c20582d6c92e4a3bfd88",
        "ba533502204a4ecb4e5dc61977cc93d2",
        "bd0c11b505f8450a061d354f7add39f2",
        "d5f059cea400c9f3a5ba5ba883f4a31a",
        "eb9fa170776163c7800d97c5709bb122",
    ]
    dirs = [(data_root / x) for x in data_dirs]
    for dir in dirs:
        relationship_file = find_relationship_file(dir)
        if relationship_file is not None:
            fix_file(relationship_file)
        else:
            logger.info(f"No relationship found in {dir}")


def fix_file(relationship_file: str) -> str:
    is_header = True
    with open(relationship_file, newline="") as csv_in:
        reader = csv.reader(csv_in, delimiter=",")
        outfile_name = relationship_file.replace(".csv", ".fixed.csv")
        with open(outfile_name, "w") as csv_out:
            csv_writer = csv.writer(csv_out, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                if is_header:
                    csv_writer.writerow(row)
                    is_header = False
                    continue
                csv_writer.writerow(fix_row(row))


def fix_row(row: list[str]) -> str:
    """
    todo: check this might have been broken during a refactor
    """
    row[3] = rel_mapper.map_relation(row[3])
    return row


def find_relationship_file(data_dir: Path) -> Optional[str]:
    logger.debug(f"reading {data_dir}")
    files = list_data_files(data_dir, {".csv"})
    rel_files = [f for f in files if f.endswith("relationships.csv")]
    for rel_file in rel_files:
        logger.debug(rel_file)
    return rel_files[0] if len(rel_files) > 0 else None


if __name__ == "__main__":
    main()
