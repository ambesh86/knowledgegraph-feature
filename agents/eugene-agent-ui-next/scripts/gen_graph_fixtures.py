#!/usr/bin/env python3
"""
Generate real KnowledgeGraph fixtures from the loaded Neo4j (PrimeKG biomedical
graph) so the Next.js UI can be developed / demoed / visual-tested with genuine,
densely-connected data — no agent backend required.

Each fixture is a `ContextGraph` ({nodes, rels}) matching lib/types.ts, with
per-node `provenance` chains so the Evidence tab is populated too. Loaded in the
app via the `?demo=<name>` query param (see lib/demoSeed.ts).

Produces three sizes around a biomedical question
("which drugs could treat folic-acid-deficiency anaemia?"):
  • answer.json — ~30 nodes  : a realistic single-answer reasoning graph
  • dense.json  — ~160 nodes : multi-category, dense — the "lots of data" test
  • huge.json   — ~450 nodes : stress test for layout + node-cap behaviour

Run:  python3 scripts/gen_graph_fixtures.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from neo4j import GraphDatabase

URI = "bolt://localhost:17687"
AUTH = ("neo4j", "eugene_local_2024")
OUT = Path(__file__).resolve().parent.parent / "public" / "fixtures"
ROOT_DISEASE = "schizophrenia"
NOW = int(time.time() * 1000)


def cat(label: str) -> str:
    return (label or "UNKNOWN").upper()


class Builder:
    """Accumulates nodes + rels with provenance, dedup by id."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.rels: dict[str, dict] = {}

    def node(self, n, layer, source, parents, cypher):
        nid = str(n["idx"])
        if nid in self.nodes:
            self.nodes[nid]["weight"] = round(self.nodes[nid]["weight"] + 0.5, 2)
            return nid
        self.nodes[nid] = {
            "id": nid,
            "caption": n["name"],
            "category": cat(n["label"]),
            "labels": [n["label"]],
            "weight": {0: 4.5, 1: 3.0, 2: 2.0, 3: 1.4}.get(layer, 1.0),
            "properties": {
                "node_index": nid,
                "node_id": str(n.get("node_id", nid)),
                "node_name": n["name"],
                "node_type": n["label"],
                "node_source": n.get("source", "PrimeKG"),
            },
            "provenance": [{
                "source": source,
                "toolName": {
                    "user_query": None,
                    "tool_call": "find_nodes_by_relationship",
                    "user_expand": "expand_node",
                }.get(source),
                "parentNodeIds": [str(p) for p in parents],
                "cypherHint": cypher,
                "timestamp": NOW,
            }],
        }
        return nid

    def rel(self, frm, to, rtype):
        rid = f"{frm}->{to}:{rtype}"
        if rid in self.rels:
            return
        self.rels[rid] = {
            "id": rid,
            "from": str(frm),
            "to": str(to),
            "type": rtype,
            "caption": rtype.replace("_", " "),
        }

    def dump(self):
        return {
            "nodes": list(self.nodes.values()),
            "rels": list(self.rels.values()),
        }


def fetch(session, cypher, **params):
    return [r.data() for r in session.run(cypher, **params)]


def build(session, caps: dict) -> dict:
    b = Builder()

    # ── Layer 0: the disease in question (root of every evidence chain) ──
    root = fetch(session,
        "MATCH (d:disease) WHERE d.node_name = $name RETURN "
        "d.node_index AS idx, d.node_name AS name, 'disease' AS label, "
        "d.node_id AS node_id, d.node_source AS source LIMIT 1", name=ROOT_DISEASE)
    if not root:
        raise SystemExit(f"root disease not found: {ROOT_DISEASE}")
    d = root[0]
    did = b.node(d, 0, "user_query", [],
                 f"MATCH (d:disease {{node_name:'{ROOT_DISEASE}'}}) RETURN d")

    # ── Layer 1: proteins associated with the disease ──
    proteins = fetch(session,
        "MATCH (d:disease {node_index:$idx})-[:disease_protein]-(p:gene_protein) "
        "WITH p, count{(p)-[:protein_protein]-()} AS deg ORDER BY deg DESC "
        "RETURN p.node_index AS idx, p.node_name AS name, 'gene_protein' AS label, "
        "p.node_id AS node_id, p.node_source AS source LIMIT $lim",
        idx=d["idx"], lim=caps["proteins"])
    pid_list = []
    for p in proteins:
        pid = b.node(p, 1, "tool_call", [did],
                     f"MATCH (d)-[:disease_protein]-(p) WHERE d.node_index='{did}' RETURN p")
        b.rel(did, pid, "disease_protein")
        pid_list.append(pid)

    # ── Layer 1b: phenotypes of the disease ──
    phenos = fetch(session,
        "MATCH (d:disease {node_index:$idx})-[:disease_phenotype_positive]-(e:effect_phenotype) "
        "RETURN e.node_index AS idx, e.node_name AS name, 'effect_phenotype' AS label, "
        "e.node_id AS node_id, e.node_source AS source LIMIT $lim",
        idx=d["idx"], lim=caps["phenotypes"])
    for e in phenos:
        eid = b.node(e, 1, "tool_call", [did],
                     "MATCH (d)-[:disease_phenotype_positive]-(e) RETURN e")
        b.rel(did, eid, "disease_phenotype_positive")

    # ── Layer 2: drugs that target those proteins (the actual answer) ──
    if pid_list:
        drugs = fetch(session,
            "MATCH (p:gene_protein)-[:drug_protein]-(dr:drug) "
            "WHERE p.node_index IN $pids "
            "RETURN dr.node_index AS idx, dr.node_name AS name, 'drug' AS label, "
            "dr.node_id AS node_id, dr.node_source AS source, "
            "p.node_index AS via LIMIT $lim",
            pids=pid_list, lim=caps["drugs"])
        for dr in drugs:
            drid = b.node(dr, 2, "user_expand", [dr["via"]],
                          f"MATCH (p)-[:drug_protein]-(dr) WHERE p.node_index='{dr['via']}' RETURN dr")
            b.rel(dr["via"], drid, "drug_protein")

    # ── Layer 2b: pathways of those proteins ──
    if pid_list:
        pathways = fetch(session,
            "MATCH (p:gene_protein)-[:pathway_protein]-(pw:pathway) "
            "WHERE p.node_index IN $pids "
            "RETURN pw.node_index AS idx, pw.node_name AS name, 'pathway' AS label, "
            "pw.node_id AS node_id, pw.node_source AS source, p.node_index AS via LIMIT $lim",
            pids=pid_list, lim=caps["pathways"])
        for pw in pathways:
            pwid = b.node(pw, 2, "tool_call", [pw["via"]],
                          "MATCH (p)-[:pathway_protein]-(pw) RETURN pw")
            b.rel(pw["via"], pwid, "pathway_protein")

    # ── Layer 2c: anatomy where those proteins are expressed ──
    if pid_list and caps.get("anatomy"):
        anat = fetch(session,
            "MATCH (p:gene_protein)-[:anatomy_protein_present]-(an:anatomy) "
            "WHERE p.node_index IN $pids "
            "RETURN an.node_index AS idx, an.node_name AS name, 'anatomy' AS label, "
            "an.node_id AS node_id, an.node_source AS source, p.node_index AS via LIMIT $lim",
            pids=pid_list, lim=caps["anatomy"])
        for an in anat:
            anid = b.node(an, 3, "tool_call", [an["via"]],
                          "MATCH (p)-[:anatomy_protein_present]-(an) RETURN an")
            b.rel(an["via"], anid, "anatomy_protein_present")

    # ── Layer 3: protein-protein interactions among the selected proteins ──
    if len(pid_list) > 1:
        ppi = fetch(session,
            "MATCH (a:gene_protein)-[:protein_protein]-(b:gene_protein) "
            "WHERE a.node_index IN $pids AND b.node_index IN $pids "
            "AND a.node_index < b.node_index "
            "RETURN a.node_index AS a, b.node_index AS b LIMIT $lim",
            pids=pid_list, lim=caps["ppi"])
        for e in ppi:
            b.rel(e["a"], e["b"], "protein_protein")

    return b.dump()


CAPS = {
    "answer": {"proteins": 7, "phenotypes": 6, "drugs": 12, "pathways": 6,
               "anatomy": 0, "ppi": 8},
    "dense":  {"proteins": 22, "phenotypes": 14, "drugs": 70, "pathways": 30,
               "anatomy": 24, "ppi": 60},
    "huge":   {"proteins": 45, "phenotypes": 30, "drugs": 220, "pathways": 80,
               "anatomy": 70, "ppi": 160},
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    with driver.session() as s:
        for name, caps in CAPS.items():
            g = build(s, caps)
            (OUT / f"{name}.json").write_text(json.dumps(g, separators=(",", ":")))
            cats = {}
            for n in g["nodes"]:
                cats[n["category"]] = cats.get(n["category"], 0) + 1
            print(f"✔ {name:7s} {len(g['nodes']):>4} nodes / {len(g['rels']):>4} rels  "
                  f"{dict(sorted(cats.items(), key=lambda x:-x[1]))}")
    driver.close()


if __name__ == "__main__":
    main()
