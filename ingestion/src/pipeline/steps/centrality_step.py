"""Pipeline step: compute composite centrality and write it back (M4 + M5).

Runnable standalone so ranking can be refreshed without touching the documents:

    python -m pipeline.steps.centrality_step

That independence is the point of M5. Parsing is the expensive stage; ranking is
the cheap one. Decoupling them means the whole corpus can be retuned in seconds
without re-parsing a single PDF, re-chunking, or rebuilding an embedding.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


def _driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(
            os.environ.get("NEO4J_USERNAME", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "eugene_local_2024"),
        ),
    )


def run(include_trials: bool = True) -> dict[str, Any]:
    from pipeline.graph import centrality, projection

    t0 = time.perf_counter()
    driver = _driver()
    try:
        graph = projection.build(driver, include_trials=include_trials)
        if graph.number_of_nodes() == 0:
            return {"status": "empty", "reason": "projection produced no nodes"}

        result = centrality.compute(graph)
        stats = centrality.write_back(driver, result)

        top = sorted(result.composite.items(), key=lambda kv: kv[1], reverse=True)[:10]
        stats["top_nodes"] = [{"id": k, "composite": v} for k, v in top]
        stats["elapsed_s"] = round(time.perf_counter() - t0, 2)
        stats["status"] = "ok"
        return stats
    finally:
        driver.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
