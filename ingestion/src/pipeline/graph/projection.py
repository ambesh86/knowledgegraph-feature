"""Project the Neo4j evidence graph into networkx for centrality computation.

Only the evidence-bearing subgraph is projected, not the whole 133k-node graph.
Centrality is meant to answer "which passage is structurally important to this
corpus of evidence" — dragging in every PrimeKG protein-protein edge would swamp
that signal with biology unrelated to any document we can cite.

Projected shape:

    (:paper)-[:has_chunk]->(:paper_chunk)
    (:paper)-[:mentions]->(:drug|:disease)
    (:drug|:disease)-[:evaluated_in|:featured_in]->(:clinical_trial)

The graph is treated as undirected. Centrality here measures structural
importance, not link direction — and `has_chunk` pointing one way shouldn't make
a passage a sink.
"""
from __future__ import annotations

import logging

import networkx as nx
from neo4j import Query

logger = logging.getLogger(__name__)

# Each entry: (cypher, description). Kept as separate literal queries rather than
# one generated string so the projection is auditable — you can read exactly what
# is and isn't included.
_PROJECTION_QUERIES: list[tuple[str, str]] = [
    (
        "MATCH (p:paper)-[:has_chunk]->(c:paper_chunk) "
        "RETURN p.doc_id AS a, c.chunk_id AS b, 'has_chunk' AS rel",
        "paper → passage",
    ),
    (
        "MATCH (p:paper)-[:mentions]->(e) WHERE e:drug OR e:disease "
        "RETURN p.doc_id AS a, toString(e.node_index) AS b, 'mentions' AS rel",
        "paper → entity",
    ),
    (
        "MATCH (e)-[r:evaluated_in|featured_in]->(t:clinical_trial) "
        "WHERE e:drug OR e:disease "
        "RETURN toString(e.node_index) AS a, toString(t.node_index) AS b, type(r) AS rel",
        "entity → trial",
    ),
]


def build(driver, include_trials: bool = True) -> nx.Graph:
    """Read the evidence subgraph out of Neo4j into an undirected networkx graph."""
    g = nx.Graph()
    queries = _PROJECTION_QUERIES if include_trials else _PROJECTION_QUERIES[:2]

    for cypher, label in queries:
        try:
            records, _, _ = driver.execute_query(Query(cypher))  # type: ignore[arg-type]
        except Exception as e:
            logger.warning(f"projection '{label}' failed: {e}")
            continue
        added = 0
        for r in records:
            a, b = r["a"], r["b"]
            if not a or not b:
                continue
            g.add_edge(a, b, rel=r["rel"])
            added += 1
        logger.info(f"  projected {added} edges ({label})")

    logger.info(f"projection: {g.number_of_nodes()} nodes / {g.number_of_edges()} edges")
    return g
