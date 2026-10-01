import csv
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


NODE_INDEX = "node_index:ID"
NODE_ID = "node_id"
NODE_LABEL = "node_label:LABEL"
NODE_NAME = "node_name"
NODE_SOURCE = "node_source"
MONDO_ID = "MONDO_ID"
MONDO_NAME = "MONDO_NAME"
FOR_CLINICAL_TRIAL = "for_clinical_trial"


def main():
    """
    fix node index number and headers
    """
    in_path = "./clinicaltrial_nodes_v1.csv"
    out_path = "./clinicaltrial_nodes_v1_fixed.csv"
    rows = _load(in_path)
    logger.info(f"loaded {len(rows)} rows")
    fixed = _fix_rows(rows)
    logger.info(f"fixed {len(fixed)} rows")
    _write(fixed, out_path)
    logger.info(f"done.")


def _load(path) -> list[dict]:
    rows = []
    with open(path, mode="r") as csv_in:
        reader = csv.DictReader(csv_in)
        for row in reader:
            # node_index:ID,node_id,:LABEL,node_name,node_source,MONDO_ID,MONDO_NAME
            rows.append(row)
    return rows


def _write(rows: list[dict], output_path: str):
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                NODE_INDEX,
                NODE_ID,
                NODE_LABEL,
                NODE_NAME,
                NODE_SOURCE,
                MONDO_ID,
                MONDO_NAME,
                FOR_CLINICAL_TRIAL,
            ]
        )
        for row in rows:
            node_index = row[NODE_INDEX]
            node_id = row[NODE_ID]
            node_label = row[NODE_LABEL]
            node_name = row[NODE_NAME]
            node_source = row[NODE_SOURCE]
            mondo_id = row[MONDO_ID]
            mondo_name = row[MONDO_NAME]
            writer.writerow(
                [
                    node_index,
                    node_id,
                    node_label,
                    node_name,
                    node_source,
                    mondo_id,
                    mondo_name,
                    "true",
                ]
            )


def _fix_rows(rows: list[dict]) -> list[dict]:
    for row in rows:
        row[NODE_INDEX] = _fix_id(row[NODE_INDEX])
        row[NODE_LABEL] = _fix_label(row[NODE_LABEL])
    return rows


def _fix_label(label: str) -> str:
    return label.lower()


def _fix_id(id: str) -> int:
    """
    add 200k to the ids so they are unique to the existing drugs/diseases node index ids
    """
    id = int(id)
    if id < 200_000:
        return id + 200_000
    else:
        return id


if __name__ == "__main__":
    main()
