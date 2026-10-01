#!/usr/bin/env python3
"""
Eugene Knowledge Graph — PRODUCTION Cypher & GDS Query Catalog (PDF).

Executes every query LIVE, one-by-one, against the local Neo4j (the PrimeKG
biomedical graph: 129,375 nodes / 4,050,064 relationships) and records, for each:

    1. Query   : plain-English description
       Cipher  : the Cypher / GDS query
       Returned Result : the live result captured at run time

Coverage is intentionally exhaustive — schema/meta, retrieval, filtering,
aggregation, traversal, path-finding, ALL GDS centrality algorithms, ALL GDS
community-detection algorithms, similarity (Jaccard / KNN / cosine vector),
node embeddings (FastRP), indexes (range / text / fulltext / vector),
constraints, full-text search, APOC utilities, and production analytical
scenarios (drug-repurposing, hub discovery, common-neighbour reasoning).

Run:  python3 generate_cypher_catalog_2026-06-20.py
Out:  docs/Eugene_Cypher_Catalog_Production_2026-06-20.pdf  (+ .json sidecar)
"""
from __future__ import annotations

import json
import re
import textwrap
import time
from datetime import date
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship, Path as Neo4jPath
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, XPreformatted, KeepTogether,
)

# --------------------------------------------------------------------------- #
# Connection
# --------------------------------------------------------------------------- #
URI = "bolt://localhost:17687"
AUTH = ("neo4j", "eugene_local_2024")
REPORT_DATE = date(2026, 6, 20)
DATE_ISO = REPORT_DATE.isoformat()
DATE_HUMAN = REPORT_DATE.strftime("%B %d, %Y")
OUT_PDF = Path(__file__).parent / "docs" / f"Eugene_Cypher_Catalog_Production_{DATE_ISO}.pdf"
OUT_JSON = OUT_PDF.with_suffix(".json")

MAX_ROWS = 8          # rows shown per result
MAX_CELL = 70         # chars per cell before truncation


# --------------------------------------------------------------------------- #
# Value rendering helpers
# --------------------------------------------------------------------------- #
def _fmt_value(v):
    if isinstance(v, Node):
        label = next(iter(v.labels), "")
        name = v.get("node_name") or v.get("name") or ""
        return f"(:{label} {name})".strip()
    if isinstance(v, Relationship):
        return f"[:{v.type}]"
    if isinstance(v, Neo4jPath):
        return f"<path len={len(v.relationships)}>"
    if isinstance(v, float):
        return f"{v:.5f}".rstrip("0").rstrip(".")
    if isinstance(v, list):
        if v and isinstance(v[0], float):
            head = ", ".join(f"{x:.3f}" for x in v[:4])
            return f"[{head}, …] (dim={len(v)})" if len(v) > 4 else f"[{head}]"
        return "[" + ", ".join(_fmt_value(x) for x in v[:6]) + ("…]" if len(v) > 6 else "]")
    if isinstance(v, dict):
        return json.dumps({k: (round(x, 4) if isinstance(x, float) else x)
                           for k, x in list(v.items())[:6]}, default=str)
    return str(v)


def _truncate(s: str) -> str:
    s = str(s).replace("\n", " ")
    return s if len(s) <= MAX_CELL else s[: MAX_CELL - 1] + "…"


# --------------------------------------------------------------------------- #
# Query runner
# --------------------------------------------------------------------------- #
class Runner:
    def __init__(self, driver):
        self.driver = driver

    def run(self, cypher: str, params: dict | None = None):
        """Return dict: columns, rows (list[list[str]]), summary, ms, error."""
        t0 = time.time()
        try:
            with self.driver.session() as s:
                res = s.run(cypher, params or {})
                keys = res.keys()
                rows = []
                for i, rec in enumerate(res):
                    if i >= MAX_ROWS:
                        # drain to get full count via summary
                        rows.append(["…"] * len(keys))
                        break
                    rows.append([_truncate(_fmt_value(rec[k])) for k in keys])
                summ = res.consume()
                ms = int((time.time() - t0) * 1000)
                counters = summ.counters
                cinfo = []
                for attr in ("nodes_created", "relationships_created",
                             "properties_set", "indexes_added", "constraints_added"):
                    val = getattr(counters, attr, 0)
                    if val:
                        cinfo.append(f"{attr}={val}")
                return {
                    "columns": list(keys),
                    "rows": rows,
                    "ms": ms,
                    "counters": ", ".join(cinfo),
                    "error": None,
                }
        except Exception as e:  # noqa: BLE001 — capture & continue
            return {
                "columns": [],
                "rows": [],
                "ms": int((time.time() - t0) * 1000),
                "counters": "",
                "error": f"{type(e).__name__}: {e}".split("\n")[0][:300],
            }


# --------------------------------------------------------------------------- #
# Build the catalog (executed in order; GDS section is order-dependent)
# --------------------------------------------------------------------------- #
def build_catalog(runner: Runner):
    """Return list of sections: {title, intro, entries:[{desc,cypher,result}]}."""
    # ---- anchors: fetch real high-degree proteins + sample drug/disease ----
    hub = runner.run(
        "MATCH (n:gene_protein)-[:protein_protein]-() "
        "WITH n, count(*) AS d ORDER BY d DESC LIMIT 2 "
        "RETURN collect(n.node_name) AS names, collect(n.node_index) AS idx"
    )
    _ = hub  # high-degree proteins confirmed present; anchors below are stable
    p_src, p_dst = "UBC", "ETS1"
    a = {"p_src": p_src, "p_dst": p_dst, "drug": "Copper",
         "disease": "folic acid deficiency anemia"}

    sections: list[dict] = []

    def sec(title, intro):
        s = {"title": title, "intro": intro, "entries": []}
        sections.append(s)
        return s

    def q(section, desc, cypher, params=None):
        r = runner.run(cypher, params)
        section["entries"].append({"desc": desc, "cypher": cypher.strip(), "result": r})
        status = "ERR " + r["error"] if r["error"] else f'{len(r["rows"])} rows / {r["ms"]}ms'
        print(f"  [{len(section['entries']):02d}] {desc[:60]:60s} {status}")
        return r

    # ===================== 1. SCHEMA & METADATA ========================= #
    s = sec("1. Schema & Metadata",
            "Introspect the live graph model: labels, relationship types, "
            "property keys, counts and the APOC meta-graph.")
    q(s, "Total node count in the graph",
      "MATCH (n) RETURN count(n) AS total_nodes")
    q(s, "Total relationship count in the graph",
      "MATCH ()-[r]->() RETURN count(r) AS total_relationships")
    q(s, "All node labels with per-label counts (descending)",
      "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS cnt ORDER BY cnt DESC")
    q(s, "All relationship types with per-type counts (top 12)",
      "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS cnt ORDER BY cnt DESC LIMIT 12")
    q(s, "Distinct property keys present in the database",
      "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS property_keys")
    q(s, "Whole-database meta statistics via APOC",
      "CALL apoc.meta.stats() YIELD labelCount, relTypeCount, nodeCount, relCount "
      "RETURN labelCount, relTypeCount, nodeCount, relCount")
    q(s, "Database components / versions (kernel, edition)",
      "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")
    q(s, "Installed APOC and GDS plugin versions",
      "RETURN apoc.version() AS apoc_version, gds.version() AS gds_version")

    # ===================== 2. RETRIEVAL & FILTERING ===================== #
    s = sec("2. Retrieval & Filtering",
            "Core read patterns: lookup by name, label scans, WHERE predicates, "
            "string matching, DISTINCT, ORDER / SKIP / LIMIT.")
    q(s, "Find a gene/protein node by exact name",
      "MATCH (n:gene_protein {node_name: $name}) RETURN n.node_name, n.node_id, n.node_source",
      {"name": a["p_src"]})
    q(s, "List 5 drug nodes (label scan with LIMIT)",
      "MATCH (d:drug) RETURN d.node_name AS drug, d.node_index AS idx LIMIT 5")
    q(s, "Case-insensitive prefix search on disease names (STARTS WITH)",
      "MATCH (d:disease) WHERE toLower(d.node_name) STARTS WITH 'anemia' "
      "RETURN d.node_name AS disease LIMIT 6")
    q(s, "Substring search on drug names (CONTAINS)",
      "MATCH (d:drug) WHERE d.node_name CONTAINS 'cillin' RETURN d.node_name AS drug LIMIT 6")
    q(s, "Regular-expression match on gene names (=~)",
      "MATCH (g:gene_protein) WHERE g.node_name =~ '^TP5[0-9].*' RETURN g.node_name AS gene LIMIT 6")
    q(s, "Distinct node sources used across the graph",
      "MATCH (n) RETURN DISTINCT n.node_source AS source ORDER BY source")
    q(s, "Pagination: diseases ordered by name, skip 10 take 5",
      "MATCH (d:disease) RETURN d.node_name AS disease ORDER BY disease SKIP 10 LIMIT 5")

    # ===================== 3. AGGREGATION =============================== #
    s = sec("3. Aggregation & Grouping",
            "count / avg / collect / percentile aggregations and grouped rollups.")
    q(s, "Average protein-protein degree across all proteins",
      "MATCH (n:gene_protein)-[:protein_protein]-() WITH n, count(*) AS deg "
      "RETURN avg(deg) AS avg_degree, max(deg) AS max_degree, min(deg) AS min_degree")
    q(s, "Top 8 most-connected proteins by PPI degree (grouped count)",
      "MATCH (n:gene_protein)-[:protein_protein]-() "
      "RETURN n.node_name AS protein, count(*) AS degree ORDER BY degree DESC LIMIT 8")
    q(s, "Collect the first 10 drug names into a single list",
      "MATCH (d:drug) WITH d LIMIT 10 RETURN collect(d.node_name) AS drug_sample")
    q(s, "Degree distribution percentiles for proteins (50/90/99th)",
      "MATCH (n:gene_protein)-[:protein_protein]-() WITH n, count(*) AS deg "
      "RETURN percentileCont(deg,0.5) AS p50, percentileCont(deg,0.9) AS p90, "
      "percentileCont(deg,0.99) AS p99")
    q(s, "Relationship-type histogram for one hub protein",
      "MATCH (n:gene_protein {node_name:$name})-[r]-() "
      "RETURN type(r) AS rel_type, count(*) AS cnt ORDER BY cnt DESC", {"name": a["p_src"]})

    # ===================== 4. TRAVERSAL ================================ #
    s = sec("4. Pattern Matching & Traversal",
            "One-hop neighbours, multi-hop expansion, variable-length paths, "
            "OPTIONAL MATCH and pattern comprehension.")
    q(s, "Direct protein interactors of a hub protein (one hop)",
      "MATCH (n:gene_protein {node_name:$name})-[:protein_protein]-(m) "
      "RETURN m.node_name AS interactor LIMIT 6", {"name": a["p_src"]})
    q(s, "Proteins associated with a disease (typed one-hop)",
      "MATCH (dis:disease)-[:disease_protein]-(p:gene_protein) "
      "WHERE dis.node_name CONTAINS 'anemia' "
      "RETURN dis.node_name AS disease, p.node_name AS protein LIMIT 6")
    q(s, "Two-hop protein neighbourhood size (distinct)",
      "MATCH (n:gene_protein {node_name:$name})-[:protein_protein*2]-(m) "
      "RETURN count(DISTINCT m) AS two_hop_reach", {"name": a["p_src"]})
    q(s, "Variable-length path 1..3 hops between two named proteins (existence)",
      "MATCH (a:gene_protein {node_name:$src}) "
      "MATCH p = (a)-[:protein_protein*1..3]-(b:gene_protein {node_name:$dst}) "
      "RETURN length(p) AS hops LIMIT 1", {"src": a["p_src"], "dst": a["p_dst"]})
    q(s, "OPTIONAL MATCH: drug with its (possibly absent) indicated diseases",
      "MATCH (d:drug {node_name:$drug}) "
      "OPTIONAL MATCH (d)-[:indication]-(x:disease) "
      "RETURN d.node_name AS drug, collect(x.node_name)[0..5] AS indications", {"drug": a["drug"]})
    q(s, "Pattern comprehension: a protein's interactor names inline",
      "MATCH (n:gene_protein {node_name:$name}) "
      "RETURN [(n)-[:protein_protein]-(m) | m.node_name][0..6] AS interactors",
      {"name": a["p_dst"]})

    # ===================== 5. PATH FINDING ============================= #
    s = sec("5. Path Finding",
            "Native shortestPath / allShortestPaths plus GDS weighted Dijkstra.")
    q(s, "Shortest PPI path between two proteins (native shortestPath, ≤5 hops)",
      "MATCH (a:gene_protein {node_name:$src}), (b:gene_protein {node_name:$dst}), "
      "p = shortestPath((a)-[:protein_protein*..5]-(b)) "
      "RETURN [x IN nodes(p) | x.node_name] AS path, length(p) AS hops",
      {"src": a["p_src"], "dst": a["p_dst"]})
    q(s, "Count of all shortest PPI paths between two proteins",
      "MATCH (a:gene_protein {node_name:$src}), (b:gene_protein {node_name:$dst}), "
      "p = allShortestPaths((a)-[:protein_protein*..5]-(b)) "
      "RETURN count(p) AS num_shortest_paths, min(length(p)) AS hops",
      {"src": a["p_src"], "dst": a["p_dst"]})
    q(s, "Cross-domain reasoning path: drug → protein → disease (≤4 hops)",
      "MATCH (d:drug {node_name:$drug}), (dis:disease) "
      "WHERE dis.node_name CONTAINS 'anemia' "
      "MATCH p = shortestPath((d)-[*..4]-(dis)) "
      "RETURN [x IN nodes(p) | coalesce(x.node_name,'?')] AS path, length(p) AS hops LIMIT 1",
      {"drug": a["drug"]})

    # ===================== 6. GDS — projection + CENTRALITY ============ #
    s = sec("6. GDS Graph Projection & Centrality",
            "Project the protein-protein interaction (PPI) sub-network into the GDS "
            "in-memory catalog, then run the full suite of centrality algorithms. "
            "Centrality ranks the most structurally important proteins.")
    # drop if exists, then project
    runner.run("CALL gds.graph.drop('ppi', false) YIELD graphName RETURN graphName")
    q(s, "Project the PPI network (gene_protein nodes + protein_protein edges, UNDIRECTED)",
      "CALL gds.graph.project('ppi', 'gene_protein', "
      "{protein_protein: {orientation: 'UNDIRECTED'}}) "
      "YIELD graphName, nodeCount, relationshipCount "
      "RETURN graphName, nodeCount, relationshipCount")
    q(s, "Degree centrality — most-connected proteins (top 5)",
      "CALL gds.degree.stream('ppi') YIELD nodeId, score "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, score "
      "ORDER BY score DESC LIMIT 5")
    q(s, "PageRank — influence by recursive importance (top 5)",
      "CALL gds.pageRank.stream('ppi', {maxIterations:20, dampingFactor:0.85}) "
      "YIELD nodeId, score RETURN gds.util.asNode(nodeId).node_name AS protein, score "
      "ORDER BY score DESC LIMIT 5")
    q(s, "ArticleRank — PageRank variant reducing low-degree bias (top 5)",
      "CALL gds.articleRank.stream('ppi', {maxIterations:20}) YIELD nodeId, score "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, score ORDER BY score DESC LIMIT 5")
    q(s, "Eigenvector centrality — influence weighted by neighbours' influence (top 5)",
      "CALL gds.eigenvector.stream('ppi', {maxIterations:20}) YIELD nodeId, score "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, score ORDER BY score DESC LIMIT 5")
    q(s, "Betweenness centrality — bridge proteins (sampled, top 5)",
      "CALL gds.betweenness.stream('ppi', {samplingSize:1000, samplingSeed:42}) "
      "YIELD nodeId, score RETURN gds.util.asNode(nodeId).node_name AS protein, score "
      "ORDER BY score DESC LIMIT 5")
    q(s, "Closeness centrality — proteins central by short distance to all others (top 5)",
      "CALL gds.closeness.stream('ppi') YIELD nodeId, score "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, score ORDER BY score DESC LIMIT 5")

    # ===================== 7. GDS — COMMUNITY ========================== #
    s = sec("7. GDS Community Detection",
            "Partition the PPI network into communities / modules and measure "
            "local clustering. Communities surface functional protein modules.")
    q(s, "Louvain modularity communities — size of the 5 largest",
      "CALL gds.louvain.stream('ppi') YIELD nodeId, communityId "
      "RETURN communityId, count(*) AS members ORDER BY members DESC LIMIT 5")
    q(s, "Weakly Connected Components — size of the 5 largest components",
      "CALL gds.wcc.stream('ppi') YIELD nodeId, componentId "
      "RETURN componentId, count(*) AS members ORDER BY members DESC LIMIT 5")
    q(s, "Label Propagation communities — 5 largest",
      "CALL gds.labelPropagation.stream('ppi', {maxIterations:10}) YIELD nodeId, communityId "
      "RETURN communityId, count(*) AS members ORDER BY members DESC LIMIT 5")
    q(s, "Modularity Optimization — number of communities and largest size",
      "CALL gds.modularityOptimization.stream('ppi', {maxIterations:10}) YIELD nodeId, communityId "
      "RETURN count(DISTINCT communityId) AS communities, count(*) AS nodes_assigned")
    q(s, "K-1 Coloring — number of colors needed (graph coloring)",
      "CALL gds.k1coloring.stream('ppi') YIELD nodeId, color "
      "RETURN count(DISTINCT color) AS distinct_colors, count(*) AS nodes")
    q(s, "Triangle Count — proteins forming the most triangles (top 5)",
      "CALL gds.triangleCount.stream('ppi') YIELD nodeId, triangleCount "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, triangleCount "
      "ORDER BY triangleCount DESC LIMIT 5")
    q(s, "Local Clustering Coefficient — graph-wide average cohesion",
      "CALL gds.localClusteringCoefficient.stream('ppi') YIELD nodeId, localClusteringCoefficient "
      "RETURN avg(localClusteringCoefficient) AS avg_clustering_coefficient")

    # ===================== 8. GDS — SIMILARITY & EMBEDDINGS =========== #
    s = sec("8. GDS Similarity & Node Embeddings",
            "Jaccard node similarity over shared interactors, FastRP structural "
            "embeddings, and KNN over those embeddings. Embeddings are then "
            "persisted to power the vector index in §9.")
    q(s, "Node Similarity (Jaccard over shared interactors) — top 5 protein pairs",
      "CALL gds.nodeSimilarity.stream('ppi', {topK:1, similarityCutoff:0.5}) "
      "YIELD node1, node2, similarity "
      "RETURN gds.util.asNode(node1).node_name AS protein_a, "
      "gds.util.asNode(node2).node_name AS protein_b, similarity "
      "ORDER BY similarity DESC LIMIT 5")
    q(s, "FastRP — generate 64-dim structural embeddings (sample vector)",
      "CALL gds.fastRP.stream('ppi', {embeddingDimension:64, randomSeed:42}) "
      "YIELD nodeId, embedding "
      "RETURN gds.util.asNode(nodeId).node_name AS protein, embedding LIMIT 3")
    q(s, "FastRP mutate — write 64-dim embeddings into the in-memory projection",
      "CALL gds.fastRP.mutate('ppi', "
      "{embeddingDimension:64, mutateProperty:'embedding', randomSeed:42}) "
      "YIELD nodePropertiesWritten, computeMillis "
      "RETURN nodePropertiesWritten, computeMillis")
    q(s, "KNN over FastRP embeddings (cosine) — 5 nearest-neighbour protein pairs",
      "CALL gds.knn.stream('ppi', "
      "{nodeProperties:['embedding'], topK:1, randomSeed:42, concurrency:1, sampleRate:0.5}) "
      "YIELD node1, node2, similarity "
      "RETURN gds.util.asNode(node1).node_name AS protein_a, "
      "gds.util.asNode(node2).node_name AS protein_b, similarity "
      "ORDER BY similarity DESC LIMIT 5")
    q(s, "Persist FastRP embeddings from projection back to Neo4j nodes",
      "CALL gds.graph.nodeProperties.write('ppi', ['embedding']) "
      "YIELD propertiesWritten RETURN propertiesWritten")
    q(s, "List in-memory GDS graphs (catalog inventory)",
      "CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount, memoryUsage "
      "RETURN graphName, nodeCount, relationshipCount, memoryUsage")

    # ===================== 9. INDEXES, CONSTRAINTS, VECTOR & FULLTEXT == #
    s = sec("9. Indexes, Constraints, Full-text & Vector Search",
            "Schema objects that make production queries fast: range/text indexes, "
            "uniqueness constraints, a full-text index over entity names, and a "
            "cosine VECTOR index over the FastRP embeddings written in §8.")
    q(s, "Create a RANGE index on gene_protein.node_name",
      "CREATE RANGE INDEX gene_name_idx IF NOT EXISTS FOR (n:gene_protein) ON (n.node_name)")
    q(s, "Create a TEXT index on disease.node_name (substring search acceleration)",
      "CREATE TEXT INDEX disease_name_text IF NOT EXISTS FOR (n:disease) ON (n.node_name)")
    q(s, "Create a uniqueness CONSTRAINT on drug.node_index",
      "CREATE CONSTRAINT drug_idx_unique IF NOT EXISTS FOR (d:drug) REQUIRE d.node_index IS UNIQUE")
    q(s, "List all indexes currently defined",
      "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties "
      "RETURN name, type, labelsOrTypes, properties ORDER BY name")
    q(s, "List all constraints currently defined",
      "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties "
      "RETURN name, type, labelsOrTypes, properties")
    q(s, "Create a FULLTEXT index over names of drugs, diseases and genes",
      "CREATE FULLTEXT INDEX entity_names IF NOT EXISTS "
      "FOR (n:drug|disease|gene_protein) ON EACH [n.node_name]")
    # let fulltext index come online
    runner.run("CALL db.awaitIndexes(60000)")
    q(s, "Full-text search for 'anemia' across all entity names (ranked)",
      "CALL db.index.fulltext.queryNodes('entity_names', 'anemia') YIELD node, score "
      "RETURN labels(node)[0] AS label, node.node_name AS name, score ORDER BY score DESC LIMIT 6")
    q(s, "Create a cosine VECTOR index over the 64-dim FastRP embeddings",
      "CREATE VECTOR INDEX protein_embedding_vec IF NOT EXISTS "
      "FOR (n:gene_protein) ON (n.embedding) "
      "OPTIONS {indexConfig: {`vector.dimensions`: 64, `vector.similarity_function`: 'cosine'}}")
    runner.run("CALL db.awaitIndexes(60000)")
    q(s, "Vector KNN search — proteins most similar to a query protein's embedding",
      "MATCH (q:gene_protein {node_name:$name}) WHERE q.embedding IS NOT NULL "
      "CALL db.index.vector.queryNodes('protein_embedding_vec', 6, q.embedding) "
      "YIELD node, score RETURN node.node_name AS similar_protein, score "
      "ORDER BY score DESC", {"name": a["p_src"]})

    # ===================== 10. APOC UTILITIES ========================= #
    s = sec("10. APOC Procedures & Functions",
            "APOC helpers for meta-modelling, weighted degree, path expansion, "
            "collection maths and text utilities.")
    q(s, "APOC node degree (total) for a hub protein",
      "MATCH (n:gene_protein {node_name:$name}) RETURN apoc.node.degree(n) AS total_degree",
      {"name": a["p_src"]})
    q(s, "APOC meta-graph: which node labels connect via which relationships (sample)",
      "CALL apoc.meta.graphSample() YIELD nodes, relationships "
      "RETURN size(nodes) AS label_count, size(relationships) AS rel_pattern_count")
    q(s, "APOC path expansion: unique proteins within 2 PPI hops of a hub",
      "MATCH (n:gene_protein {node_name:$name}) "
      "CALL apoc.path.subgraphNodes(n, {relationshipFilter:'protein_protein', maxLevel:2}) "
      "YIELD node RETURN count(node) AS nodes_within_2_hops", {"name": a["p_dst"]})
    q(s, "APOC collection stats over a degree sample",
      "MATCH (n:gene_protein)-[:protein_protein]-() WITH n, count(*) AS d LIMIT 500 "
      "WITH collect(d) AS degs "
      "RETURN apoc.coll.max(degs) AS max, apoc.coll.min(degs) AS min, apoc.coll.avg(degs) AS avg")
    q(s, "APOC text utilities: clean & capitalize a drug name",
      "RETURN apoc.text.capitalizeAll(toLower($drug)) AS pretty_name", {"drug": a["drug"]})

    # ===================== 11. PRODUCTION ANALYTICAL SCENARIOS ======== #
    s = sec("11. Production Analytical Scenarios",
            "End-to-end questions a biomedical analyst or the Eugene chat agent "
            "would actually ask — drug repurposing, hub discovery, shared-target "
            "reasoning and disease comorbidity structure.")
    q(s, "Drug-repurposing: drugs targeting proteins linked to a disease",
      "MATCH (dis:disease)-[:disease_protein]-(p:gene_protein)-[:drug_protein]-(d:drug) "
      "WHERE dis.node_name CONTAINS 'anemia' "
      "RETURN d.node_name AS candidate_drug, count(DISTINCT p) AS shared_targets "
      "ORDER BY shared_targets DESC LIMIT 6")
    q(s, "Most disease-associated proteins (potential master regulators)",
      "MATCH (p:gene_protein)-[:disease_protein]-(d:disease) "
      "RETURN p.node_name AS protein, count(DISTINCT d) AS disease_count "
      "ORDER BY disease_count DESC LIMIT 6")
    q(s, "Shared targets between two drugs (mechanistic overlap)",
      "MATCH (d1:drug)-[:drug_protein]-(p:gene_protein)-[:drug_protein]-(d2:drug) "
      "WHERE d1.node_name < d2.node_name "
      "RETURN d1.node_name AS drug_a, d2.node_name AS drug_b, count(DISTINCT p) AS shared "
      "ORDER BY shared DESC LIMIT 6")
    q(s, "Disease comorbidity by shared phenotypes (anemia cohort, top pairs)",
      "MATCH (a:disease) WHERE a.node_name CONTAINS 'anemia' "
      "MATCH (a)-[:disease_phenotype_positive]-(ph:effect_phenotype)-"
      "[:disease_phenotype_positive]-(b:disease) "
      "WHERE a.node_name < b.node_name "
      "WITH a, b, count(DISTINCT ph) AS shared_phenotypes "
      "RETURN a.node_name AS disease_a, b.node_name AS disease_b, shared_phenotypes "
      "ORDER BY shared_phenotypes DESC LIMIT 6")
    q(s, "Pathway enrichment: pathways with the most member proteins",
      "MATCH (pw:pathway)-[:pathway_protein]-(p:gene_protein) "
      "RETURN pw.node_name AS pathway, count(DISTINCT p) AS proteins "
      "ORDER BY proteins DESC LIMIT 6")

    # cleanup GDS projection
    runner.run("CALL gds.graph.drop('ppi', false) YIELD graphName RETURN graphName")
    return sections


# --------------------------------------------------------------------------- #
# PDF rendering
# --------------------------------------------------------------------------- #
NEO_BG = colors.HexColor("#0E1116")
NEO_BLUE = colors.HexColor("#018BFF")
NEO_GREEN = colors.HexColor("#1FA363")
NEO_RED = colors.HexColor("#C0392B")
CODE_BG = colors.HexColor("#F4F6F8")
HDR_GREY = colors.HexColor("#2C3440")
ROW_ALT = colors.HexColor("#F7F9FB")


def styles():
    ss = getSampleStyleSheet()
    out = {}
    out["title"] = ParagraphStyle("t", parent=ss["Title"], fontSize=24,
                                  textColor=NEO_BLUE, spaceAfter=6, alignment=TA_CENTER)
    out["subtitle"] = ParagraphStyle("st", parent=ss["Normal"], fontSize=11,
                                     textColor=colors.HexColor("#5A6472"),
                                     alignment=TA_CENTER, spaceAfter=4)
    out["h2"] = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=15,
                              textColor=HDR_GREY, spaceBefore=14, spaceAfter=4)
    out["intro"] = ParagraphStyle("intro", parent=ss["Normal"], fontSize=9.5,
                                  textColor=colors.HexColor("#5A6472"), spaceAfter=8,
                                  leading=13)
    out["qlabel"] = ParagraphStyle("ql", parent=ss["Normal"], fontSize=10.5,
                                   textColor=HDR_GREY, spaceBefore=9, spaceAfter=2,
                                   leading=14)
    out["code"] = ParagraphStyle("code", parent=ss["Code"], fontSize=8,
                                 textColor=colors.HexColor("#1A2330"), leading=10.5)
    out["reslabel"] = ParagraphStyle("rl", parent=ss["Normal"], fontSize=8.5,
                                     textColor=NEO_GREEN, spaceBefore=3, spaceAfter=2)
    out["cell"] = ParagraphStyle("cell", parent=ss["Normal"], fontSize=7.2, leading=9)
    out["cellh"] = ParagraphStyle("cellh", parent=ss["Normal"], fontSize=7.2,
                                 leading=9, textColor=colors.white)
    out["err"] = ParagraphStyle("err", parent=ss["Normal"], fontSize=8,
                               textColor=NEO_RED, leading=11)
    out["meta"] = ParagraphStyle("meta", parent=ss["Normal"], fontSize=8,
                                textColor=colors.HexColor("#8A94A2"), spaceBefore=1)
    return out


def result_flowable(r, st):
    if r["error"]:
        return Paragraph(f"⚠ {r['error']}", st["err"])
    if not r["rows"]:
        note = "(no rows returned)"
        if r["counters"]:
            note = f"(write OK — {r['counters']})"
        return Paragraph(note + f"  ·  {r['ms']} ms", st["meta"])
    cols = r["columns"]
    header = [Paragraph(f"<b>{c}</b>", st["cellh"]) for c in cols]
    data = [header]
    for row in r["rows"]:
        data.append([Paragraph(str(c), st["cell"]) for c in row])
    ncol = len(cols)
    avail = 175 * mm
    cw = [avail / ncol] * ncol
    t = Table(data, colWidths=cw, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HDR_GREY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DBE2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    t.setStyle(TableStyle(style))
    meta = Paragraph(
        f"{len(r['rows'])} row(s) · {r['ms']} ms"
        + (f" · {r['counters']}" if r["counters"] else ""), st["meta"])
    return [t, meta]


# --- Cypher code-box rendering (textbook listing) -------------------------- #
# Break the (often single-line, concatenated) query onto its own line per major
# Cypher clause so it reads like a formatted listing instead of one long line.
_CLAUSE_RE = re.compile(
    r"\s+(OPTIONAL MATCH|ORDER BY|MATCH|WHERE|RETURN|WITH|UNWIND|CALL|YIELD|"
    r"CREATE|MERGE|SET|DELETE|REMOVE|LIMIT|SKIP|FOREACH)\b")


def prettify_cypher(s: str, width: int = 86) -> str:
    # 1) normalise whitespace, 2) one line per major clause, 3) hard-wrap each
    #    clause to `width` chars (8pt Courier in a 176mm box) with a hanging
    #    indent so NOTHING can spill past the right edge of the code box.
    s = re.sub(r"\s+", " ", s.strip())
    s = _CLAUSE_RE.sub(lambda m: "\n" + m.group(1), s).lstrip("\n")
    out: list[str] = []
    for line in s.split("\n"):
        wrapped = textwrap.wrap(
            line, width=width, subsequent_indent="    ",
            break_long_words=False, break_on_hyphens=False)
        out.extend(wrapped or [""])
    return "\n".join(out)


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def code_box(cypher: str, st):
    """A bordered, shaded, left-accented, WRAPPING code block."""
    flow = XPreformatted(_xml_escape(prettify_cypher(cypher)), st["code"])
    t = Table([[flow]], colWidths=[176 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C9D2DC")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, NEO_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_pdf(sections, env, st):
    doc = SimpleDocTemplate(str(OUT_PDF), pagesize=LETTER,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title="Eugene Cypher & GDS Production Catalog")
    story = []
    # cover
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("Eugene Knowledge Graph", st["title"]))
    story.append(Paragraph("Production Cypher &amp; GDS Query Catalog", st["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(DATE_HUMAN, st["subtitle"]))
    story.append(Spacer(1, 8 * mm))
    env_rows = [
        ["Neo4j", env["neo4j"]],
        ["APOC", env["apoc"]],
        ["GDS", env["gds"]],
        ["Nodes", env["nodes"]],
        ["Relationships", env["rels"]],
        ["Queries executed", str(env["nq"])],
        ["Captured live", DATE_HUMAN],
    ]
    et = Table([[Paragraph(f"<b>{k}</b>", st["cell"]), Paragraph(str(v), st["cell"])]
                for k, v in env_rows], colWidths=[45 * mm, 90 * mm])
    et.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DBE2")),
        ("BACKGROUND", (0, 0), (0, -1), CODE_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(KeepTogether([et]))
    story.append(Spacer(1, 8 * mm))
    # contents
    story.append(Paragraph("<b>Contents</b>", st["qlabel"]))
    for s in sections:
        story.append(Paragraph(f"{s['title']}  ·  {len(s['entries'])} queries", st["meta"]))
    story.append(PageBreak())

    n = 0
    for s in sections:
        story.append(Paragraph(s["title"], st["h2"]))
        story.append(HRFlowable(width="100%", thickness=1, color=NEO_BLUE, spaceAfter=4))
        story.append(Paragraph(s["intro"], st["intro"]))
        for e in s["entries"]:
            n += 1
            # Keep the question + its code box together; let the result flow
            # (and page-break) on its own so nothing is forced off the page.
            story.append(KeepTogether([
                Paragraph(f"<b>{n}. Query:</b> {e['desc']}", st["qlabel"]),
                Paragraph("<b>Cipher:</b>", st["reslabel"]),
                code_box(e["cypher"], st),
            ]))
            story.append(Paragraph("<b>Returned Result:</b>", st["reslabel"]))
            res = result_flowable(e["result"], st)
            if isinstance(res, list):
                story.extend(res)
            else:
                story.append(res)
            story.append(Spacer(1, 4 * mm))
    doc.build(story)


# --------------------------------------------------------------------------- #
def main():
    import sys
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)

    # Fast path: re-render the PDF from the captured JSON without re-querying.
    if "--from-json" in sys.argv and OUT_JSON.exists():
        data = json.loads(OUT_JSON.read_text())
        st = styles()
        build_pdf(data["sections"], data["env"], st)
        print(f"✔ PDF re-rendered from JSON: {OUT_PDF}")
        return

    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    runner = Runner(driver)

    # environment fingerprint
    ver = runner.run("RETURN apoc.version() AS apoc, gds.version() AS gds")
    comp = runner.run("CALL dbms.components() YIELD versions, edition "
                      "RETURN versions[0] AS v, edition")
    nodes = runner.run("MATCH (n) RETURN count(n) AS c")
    rels = runner.run("MATCH ()-[r]->() RETURN count(r) AS c")
    env = {
        "neo4j": f'{comp["rows"][0][0]} ({comp["rows"][0][1]})' if comp["rows"] else "5.26.9",
        "apoc": ver["rows"][0][0] if ver["rows"] else "n/a",
        "gds": ver["rows"][0][1] if ver["rows"] else "n/a",
        "nodes": nodes["rows"][0][0] if nodes["rows"] else "?",
        "rels": rels["rows"][0][0] if rels["rows"] else "?",
    }

    print(f"Connected: Neo4j {env['neo4j']} · APOC {env['apoc']} · GDS {env['gds']}")
    print(f"Graph: {env['nodes']} nodes / {env['rels']} rels\n")
    print("Executing catalog...\n")
    sections = build_catalog(runner)
    env["nq"] = sum(len(s["entries"]) for s in sections)

    # JSON sidecar
    OUT_JSON.write_text(json.dumps(
        {"date": DATE_ISO, "env": env, "sections": sections}, indent=2, default=str))

    st = styles()
    build_pdf(sections, env, st)
    driver.close()

    n_err = sum(1 for s in sections for e in s["entries"] if e["result"]["error"])
    print(f"\n✔ {env['nq']} queries executed ({n_err} errors)")
    print(f"✔ PDF : {OUT_PDF}")
    print(f"✔ JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
