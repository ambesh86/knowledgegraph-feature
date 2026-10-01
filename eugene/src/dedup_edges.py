import csv
import logging
from model.edge import Edge

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    the edges file is loading bidirectional edges, we only want one direction
    """
    csv_path = "./edges.csv"
    edges = _load_edges(csv_path)
    logger.info(f"loaded {len(edges)} to inspect for deduplication...")
    filtered = _dedup(edges=edges)
    logger.info(f"after filtered {len(filtered)}")
    _write(filtered, "./edges_dedup.csv")
    logger.info(f"deduplication finished...")


def _write(edges: list[Edge], output_path: str, headers=str):
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            ["relation:TYPE", "display_relation", "x_index:START_ID", "y_index:END_ID"]
        )
        for edge in edges:
            relation = edge.relation
            display_relation = edge.display_relation
            x_index = edge.x_index
            y_index = edge.y_index
            writer.writerow([relation, display_relation, x_index, y_index])


def _load_edges(path) -> list[Edge]:
    edges = []
    with open(path, mode="r") as csv_in:
        reader = csv.DictReader(csv_in)
        for row in reader:
            # relation,display_relation,x_index,y_index
            relation = row["relation"]
            display_relation = row["display_relation"]
            x_index = row["x_index"]
            y_index = row["y_index"]
            edge = Edge(
                x_index=x_index,
                y_index=y_index,
                relation=relation,
                display_relation=display_relation,
            )
            edges.append(edge)
    return edges


def _dedup(edges: list[Edge]) -> list[Edge]:
    seen = set()
    filtered = []
    for edge in edges:
        key = _gen_key(edge)
        if key not in seen:
            seen.add(key)
            filtered.append(edge)
    return filtered


def _gen_key(edge: Edge) -> str:
    source = min(edge.x_index, edge.y_index)
    target = max(edge.x_index, edge.y_index)
    return "{relation}:{display_relation} {source}-{target}".format(
        relation=edge.relation,
        display_relation=edge.display_relation,
        source=source,
        target=target,
    )


if __name__ == "__main__":
    main()
