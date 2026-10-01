import csv
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


EDGE_NODE_TYPE = ":TYPE"
EDGE_START_ID = ":START_ID"
EDGE_END_ID = ":END_ID"
EDGE_DISPLAY_RELATION = "display_relation"
FOR_CLINICAL_TRIAL = "for_clinical_trial"

def main():
    """
    fix node index number and headers
    """
    in_path = "./clinicaltrial_edges_v1.csv"
    out_path = "./clinicaltrial_edges_v1_fixed.csv"
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
            # :TYPE,display_relation,:START_ID,:END_ID
            rows.append(row)
    return rows


def _write(edges: list[dict], output_path: str):
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [EDGE_NODE_TYPE, EDGE_DISPLAY_RELATION, EDGE_START_ID, EDGE_END_ID, FOR_CLINICAL_TRIAL]
        )
        for edge in edges:
            node_type = edge[EDGE_NODE_TYPE]
            display_relation = edge[EDGE_DISPLAY_RELATION]
            start_id = edge[EDGE_START_ID]
            end_id = edge[EDGE_END_ID]
            writer.writerow([node_type, display_relation, start_id, end_id, "true"])



def _fix_rows(rows: list[dict]) -> list[dict]:
    for row in rows:
        start_id = _fix_id(row[EDGE_START_ID])
        row[EDGE_START_ID] = start_id
        end_id = _fix_id(row[EDGE_END_ID])
        row[EDGE_END_ID] = end_id
        node_type = _fix_label(row[EDGE_NODE_TYPE])
        row[EDGE_NODE_TYPE] = node_type
        relation = _fix_label(row[EDGE_DISPLAY_RELATION])
        row[EDGE_DISPLAY_RELATION] = relation 
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
