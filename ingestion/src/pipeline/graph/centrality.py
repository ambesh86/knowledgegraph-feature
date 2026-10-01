"""Composite centrality over the evidence graph — mechanisms M4 and M5.

HippoRAG established that graph centrality is a strong retrieval signal. Two
extensions here:

**Seven metrics, not one.** Each answers a different question about a passage:
PageRank finds globally authoritative text; betweenness finds the bridging
passages that connect one line of reasoning to another; harmonic behaves sensibly
when the corpus forms disconnected islands (which it does — papers on unrelated
diseases share no edges).

**A self-renormalizing composite.** Several of these metrics are computationally
infeasible on a large graph. The usual response is to drop them silently or
approximate. Instead a node-count guard skips them and the composite renormalizes
over whichever metrics actually ran, so the score keeps the same meaning and the
same 0–1 range whether the corpus holds 1,000 nodes or 100,000. Above the
threshold, (PageRank 0.28, degree 0.16, betweenness 0.16) renormalize to
(0.467, 0.267, 0.267) with no manual intervention.

M5: scores are written back onto the existing nodes as replaceable properties.
Old values are deleted before new ones land, so a refresh is repeatable and never
accumulates stale scores. The consequence is the useful part — ranking can be
retuned across the whole corpus without re-parsing a single PDF.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

import networkx as nx

logger = logging.getLogger(__name__)

# Weights from the research brief. They must sum to 1.0 when every metric runs;
# the renormalization below preserves the contract when some are skipped.
WEIGHTS: dict[str, float] = {
    "pagerank": 0.28,
    "degree": 0.16,
    "betweenness": 0.16,
    "closeness": 0.12,
    "harmonic": 0.12,
    "eigenvector": 0.10,
    "katz": 0.06,
}

# Node-count ceilings above which a metric is skipped. Betweenness is O(nm) even
# with Brandes; eigenvector and Katz need repeated matrix operations that stop
# converging usefully at scale.
GUARDS: dict[str, int] = {
    "pagerank": 10_000_000,   # power iteration, effectively always affordable
    "degree": 10_000_000,     # O(m)
    "betweenness": int(os.environ.get("CENTRALITY_BETWEENNESS_MAX", "4000")),
    "closeness": int(os.environ.get("CENTRALITY_CLOSENESS_MAX", "4000")),
    "harmonic": int(os.environ.get("CENTRALITY_HARMONIC_MAX", "4000")),
    "eigenvector": int(os.environ.get("CENTRALITY_EIGENVECTOR_MAX", "4000")),
    "katz": int(os.environ.get("CENTRALITY_KATZ_MAX", "4000")),
}


# Above this node count, betweenness is estimated from sampled pivots rather than
# computed exactly. Fixed seed so a refresh is reproducible — an unstable ranking
# would undermine the replayability the whole design is built on.
_PIVOT_MIN = int(os.environ.get("CENTRALITY_PIVOT_MIN", "1500"))
_PIVOTS = int(os.environ.get("CENTRALITY_PIVOTS", "400"))
_SEED = 42


@dataclass
class CentralityResult:
    scores: dict[str, dict[str, float]]   # metric -> {node_id: score}
    composite: dict[str, float]           # node_id -> composite 0..1
    active_metrics: list[str]
    skipped_metrics: list[str]
    effective_weights: dict[str, float]
    node_count: int
    edge_count: int
    # Metrics computed by sampling rather than exactly. Reported so a consumer
    # never mistakes an estimate for an exact score.
    approximate: list[str] = field(default_factory=list)


def _normalize(values: dict[str, float]) -> dict[str, float]:
    """Scale to 0–1 so metrics on different scales can be blended.

    A degenerate spread (every node equal) maps to 0.0 rather than 1.0: if a
    metric cannot discriminate, it should contribute nothing, not maximum score
    to everyone.
    """
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    span = hi - lo
    if span <= 0:
        return {k: 0.0 for k in values}
    return {k: (v - lo) / span for k, v in values.items()}


def _safe(name: str, fn: Callable[[], dict[str, float]]) -> dict[str, float] | None:
    """Run one metric, converting non-convergence into a skip rather than a crash."""
    try:
        return fn()
    except Exception as e:
        # PowerIterationFailedConvergence is routine on sparse/disconnected
        # graphs — a skipped metric is a normal outcome the composite handles.
        logger.warning(f"centrality metric '{name}' failed ({type(e).__name__}: {e}); skipping")
        return None


def compute(graph: nx.Graph) -> CentralityResult:
    """Compute all affordable metrics and blend them into a renormalized composite."""
    n, m = graph.number_of_nodes(), graph.number_of_edges()
    logger.info(f"centrality over {n} nodes / {m} edges")

    raw: dict[str, dict[str, float]] = {}
    skipped: list[str] = []

    # Betweenness is O(nm) even with Brandes, and networkx runs it in pure Python.
    # Above `_PIVOT_MIN` we estimate it from `_PIVOTS` sampled source nodes
    # (Brandes & Pich 2007) instead of all-pairs. That is an APPROXIMATION and is
    # reported as one in the result — measured on 3,483 nodes, exact betweenness
    # alone exceeded ten minutes, which is not a sensible cost for a signal that
    # is then blended at weight 0.16.
    use_pivots = n > _PIVOT_MIN
    pivots = min(_PIVOTS, n) if use_pivots else None

    plan: list[tuple[str, Callable[[], dict[str, float]]]] = [
        ("pagerank", lambda: nx.pagerank(graph, alpha=0.85)),
        ("degree", lambda: nx.degree_centrality(graph)),
        ("betweenness", lambda: nx.betweenness_centrality(graph, k=pivots, seed=_SEED)),
        ("closeness", lambda: nx.closeness_centrality(graph)),
        ("harmonic", lambda: nx.harmonic_centrality(graph)),
        ("eigenvector", lambda: nx.eigenvector_centrality(graph, max_iter=500, tol=1e-6)),
        ("katz", lambda: nx.katz_centrality(graph, alpha=0.005, beta=1.0, max_iter=1000)),
    ]

    for name, fn in plan:
        if n > GUARDS[name]:
            skipped.append(name)
            logger.info(f"  skip {name}: {n} nodes exceeds guard {GUARDS[name]}")
            continue
        got = _safe(name, fn)
        if got is None:
            skipped.append(name)
            continue
        raw[name] = _normalize(got)

    active = list(raw.keys())
    if not active:
        logger.warning("no centrality metric ran; composite is empty")
        return CentralityResult({}, {}, [], skipped, {}, n, m)

    # THE self-renormalization: weights are rescaled over surviving metrics so the
    # composite still spans 0–1 and still means "structural importance", whatever
    # the corpus size.
    total = sum(WEIGHTS[k] for k in active)
    effective = {k: WEIGHTS[k] / total for k in active}
    if skipped:
        logger.info(
            f"renormalized weights over {len(active)} active metrics: "
            + ", ".join(f"{k}={v:.3f}" for k, v in effective.items())
        )

    composite: dict[str, float] = {}
    for node in graph.nodes():
        composite[node] = round(
            sum(effective[k] * raw[k].get(node, 0.0) for k in active), 6
        )

    return CentralityResult(
        scores=raw,
        approximate=["betweenness"] if use_pivots and "betweenness" in active else [],
        composite=composite,
        active_metrics=active,
        skipped_metrics=skipped,
        effective_weights=effective,
        node_count=n,
        edge_count=m,
    )


# ---------------------------------------------------------------------------
# M5 — write back as replaceable properties
# ---------------------------------------------------------------------------
PROPERTY_PREFIX = "centrality_"
COMPOSITE_PROPERTY = "centrality_composite"

ALL_PROPERTIES = [f"{PROPERTY_PREFIX}{m}" for m in WEIGHTS] + [COMPOSITE_PROPERTY]


def write_back(driver, result: CentralityResult, batch: int = 5000) -> dict[str, Any]:
    """Replace centrality properties on the graph. Idempotent by construction.

    Old properties are removed first: without that, a metric skipped on this run
    would leave last run's value behind, and the composite would silently be
    blended from scores of different vintages.
    """
    from neo4j import Query

    removes = ", ".join(f"n.{p}" for p in ALL_PROPERTIES)
    driver.execute_query(
        Query(f"MATCH (n) WHERE n.{COMPOSITE_PROPERTY} IS NOT NULL REMOVE {removes}")  # type: ignore[arg-type]
    )

    rows = [
        {
            "id": node,
            "composite": score,
            **{f"{PROPERTY_PREFIX}{m}": result.scores[m].get(node, 0.0) for m in result.active_metrics},
        }
        for node, score in result.composite.items()
    ]

    written = 0
    sets = ", ".join(
        f"n.{PROPERTY_PREFIX}{m} = row.{PROPERTY_PREFIX}{m}" for m in result.active_metrics
    )
    assign = f"SET n.{COMPOSITE_PROPERTY} = row.composite" + (f", {sets}" if sets else "")

    # Two LABELLED lookups, not one unlabelled OR.
    #
    # The previous form — `MATCH (n) WHERE n.chunk_id = row.id OR n.doc_id = row.id`
    # — could not use any index: no label to scope it, and an OR across two
    # properties defeats index selection anyway. Neo4j fell back to a full scan of
    # every node in the graph, per row. Measured: 7,639 rows took 2,436 seconds.
    # Splitting into label-scoped equality matches lets each hit
    # `paper_chunk(chunk_id)` and `paper(doc_id)` directly.
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        for cypher in (
            "UNWIND $rows AS row MATCH (n:paper_chunk {chunk_id: row.id}) " + assign,
            "UNWIND $rows AS row MATCH (n:paper {doc_id: row.id}) " + assign,
        ):
            driver.execute_query(Query(cypher), rows=chunk)  # type: ignore[arg-type]
        written += len(chunk)

    logger.info(f"wrote centrality onto {written} nodes")
    return {
        "nodes_scored": written,
        "active_metrics": result.active_metrics,
        "skipped_metrics": result.skipped_metrics,
        "approximate_metrics": result.approximate,
        "effective_weights": {k: round(v, 4) for k, v in result.effective_weights.items()},
        "graph_nodes": result.node_count,
        "graph_edges": result.edge_count,
    }
