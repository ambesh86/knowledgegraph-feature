#!/usr/bin/env python3
"""Transform downloaded ClinicalTrials.gov studies into Neo4j-loadable CSVs.

Emits two files matching the repo's existing ingest convention
(`eugene/saved_queries/ingest_csv/clinical_trials.cypher`):

  ctgov_nodes.csv   node_index:ID, node_id, node_label:LABEL, node_name, ...
  ctgov_edges.csv   :START_ID, :END_ID, :TYPE, display_relation

Node ids are offset by `--index-offset` (default 900,000) so they cannot collide
with the existing PrimeKG node_index space (currently maxes at 129,374).

LINKAGE is the point of this script. A trial node with no edges is dead weight —
the agent can't traverse to it. We link each trial to the drug / disease nodes
that ALREADY exist in the graph by normalized name match:

    (drug)   -[:evaluated_in]-> (clinical_trial)
    (disease)-[:featured_in]->  (clinical_trial)

Those two relationship types are what the agent's system prompt already tells it
to look for. Match rate is reported at the end — it will not be 100%, because
CT.gov intervention strings ("BIVV001", "rFVIIIFc-VWF-XTEN") often don't appear
verbatim as graph drug names. Unmatched trials are still emitted as nodes so
they remain searchable by name/NCT id.

Usage:
    python3 bin/ctgov/build_ctgov_csv.py \
        --raw dumps/ct_import/ctgov_raw.json --outdir dumps/ct_import
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ctgov-csv")

TRIAL_LABEL = "clinical_trial"
REL_DRUG = "evaluated_in"
REL_DISEASE = "featured_in"

# Intervention names that carry no entity signal — matching on these would link
# hundreds of unrelated trials to the same node.
STOP_TERMS = {
    "placebo", "saline", "normal saline", "standard of care", "best supportive care",
    "control", "no intervention", "observation", "questionnaire", "survey",
    "blood sample", "blood draw", "water", "sham", "sham comparator", "usual care",
    "exercise", "education", "physical therapy", "dietary supplement", "vitamin",
    "oxygen", "air", "glucose", "dextrose", "sodium chloride",
}

_PAREN = re.compile(r"\([^)]*\)")
_NONWORD = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def normalize(name: str) -> str:
    """Lowercase, strip parentheticals/punctuation, collapse whitespace.

    'Hyperemesis Gravidarum (disease)' -> 'hyperemesis gravidarum'
    'Factor VIII, recombinant'         -> 'factor viii recombinant'
    """
    if not name:
        return ""
    s = name.lower().strip()
    s = _PAREN.sub(" ", s)
    s = _NONWORD.sub(" ", s)
    return _WS.sub(" ", s).strip()


def load_graph_names(uri: str, user: str, pwd: str) -> tuple[dict, dict]:
    """Build {normalized_name: node_index} maps for existing drug and disease nodes."""
    drugs: dict[str, str] = {}
    diseases: dict[str, str] = {}

    def collect(records, target: dict[str, str], label: str) -> None:
        for r in records:
            key = normalize(r["name"])
            # Keep the first occurrence — stable across runs given the same DB.
            if key and key not in target and key not in STOP_TERMS:
                target[key] = str(r["idx"])
        logger.info(f"loaded {len(target)} {label} names from graph")

    # Queries are inlined as literals rather than built from the label — the
    # driver's typing requires LiteralString, and it keeps the label out of
    # string interpolation entirely.
    with GraphDatabase.driver(uri, auth=(user, pwd)) as drv:
        recs, _, _ = drv.execute_query(
            "MATCH (n:drug) WHERE n.node_name IS NOT NULL AND n.node_index IS NOT NULL "
            "RETURN n.node_name AS name, n.node_index AS idx"
        )
        collect(recs, drugs, "drug")
        recs, _, _ = drv.execute_query(
            "MATCH (n:disease) WHERE n.node_name IS NOT NULL AND n.node_index IS NOT NULL "
            "RETURN n.node_name AS name, n.node_index AS idx"
        )
        collect(recs, diseases, "disease")
    return drugs, diseases


def _get(study: dict, *path, default=None):
    cur = study
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def flatten_study(study: dict) -> dict:
    """Pull the fields we graph from the API v2 protocolSection."""
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {}) or {}
    status = ps.get("statusModule", {}) or {}
    design = ps.get("designModule", {}) or {}
    spon = _get(ps, "sponsorCollaboratorsModule", "leadSponsor", default={}) or {}
    conds = _get(ps, "conditionsModule", "conditions", default=[]) or []
    arms = _get(ps, "armsInterventionsModule", "interventions", default=[]) or []

    nct = ident.get("nctId", "")
    interventions = []
    for iv in arms:
        nm = (iv or {}).get("name")
        if nm:
            interventions.append(nm)

    return {
        "nct_id": nct,
        "title": ident.get("briefTitle", "") or ident.get("officialTitle", ""),
        "status": status.get("overallStatus", ""),
        "start_date": _get(status, "startDateStruct", "date", default="") or "",
        "completion_date": _get(status, "completionDateStruct", "date", default="") or "",
        "phase": ", ".join(design.get("phases", []) or []),
        "study_type": design.get("studyType", ""),
        "enrollment": str(_get(design, "enrollmentInfo", "count", default="") or ""),
        "sponsor": spon.get("name", ""),
        "conditions": conds,
        "interventions": interventions,
        "themes": study.get("_eugene_themes", []),
        "url": f"https://clinicaltrials.gov/study/{nct}" if nct else "",
    }


NODE_HEADER = [
    "node_index:ID", "node_id", "node_label:LABEL", "node_name", "node_source",
    "nct_id", "title", "status", "phase", "study_type", "enrollment",
    "sponsor", "start_date", "completion_date", "conditions", "interventions",
    "themes", "url", "for_clinical_trial",
]
EDGE_HEADER = [":START_ID", ":END_ID", ":TYPE", "display_relation"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default="dumps/ct_import/ctgov_raw.json")
    ap.add_argument("--outdir", default="dumps/ct_import")
    ap.add_argument("--index-offset", type=int, default=900_000)
    ap.add_argument("--neo4j-uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:17687"))
    ap.add_argument("--neo4j-user", default=os.environ.get("NEO4J_USERNAME", "neo4j"))
    ap.add_argument("--neo4j-pass", default=os.environ.get("NEO4J_PASSWORD", "eugene_local_2024"))
    args = ap.parse_args()

    raw = Path(args.raw)
    if not raw.exists():
        logger.error(f"{raw} not found — run download_ctgov.py first")
        return 1
    studies = json.loads(raw.read_text())
    logger.info(f"loaded {len(studies)} studies from {raw}")

    drugs, diseases = load_graph_names(args.neo4j_uri, args.neo4j_user, args.neo4j_pass)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    nodes_path = outdir / "ctgov_nodes.csv"
    edges_path = outdir / "ctgov_edges.csv"

    stats = Counter()
    # Dedup edges — a trial listing "Factor VIII" in two arms must not create two
    # identical relationships.
    seen_edges: set[tuple[str, str, str]] = set()

    with nodes_path.open("w", newline="", encoding="utf-8") as nf, \
         edges_path.open("w", newline="", encoding="utf-8") as ef:
        nw = csv.writer(nf)
        ew = csv.writer(ef)
        nw.writerow(NODE_HEADER)
        ew.writerow(EDGE_HEADER)

        # Sorted by NCT id so node_index assignment is deterministic across runs.
        for i, (_nct, study) in enumerate(sorted(studies.items())):
            s = flatten_study(study)
            if not s["nct_id"]:
                stats["skipped_no_nct"] += 1
                continue
            idx = str(args.index_offset + i)
            nw.writerow([
                idx,
                s["nct_id"],                 # node_id == NCT id: stable, human-meaningful
                TRIAL_LABEL,
                s["title"][:500],            # node_name is what name-search matches on
                "ClinicalTrials.gov",
                s["nct_id"], s["title"][:500], s["status"], s["phase"],
                s["study_type"], s["enrollment"], s["sponsor"],
                s["start_date"], s["completion_date"],
                "; ".join(s["conditions"])[:1000],
                "; ".join(s["interventions"])[:1000],
                "; ".join(s["themes"]),
                s["url"],
                "true",
            ])
            stats["nodes"] += 1

            # ── linkage ──────────────────────────────────────────────────────
            for iv in s["interventions"]:
                key = normalize(iv)
                if not key or key in STOP_TERMS:
                    continue
                target = drugs.get(key)
                if target:
                    e = (target, idx, REL_DRUG)
                    if e not in seen_edges:
                        seen_edges.add(e)
                        ew.writerow([target, idx, REL_DRUG, "evaluated in"])
                        stats["edges_drug"] += 1
            for cond in s["conditions"]:
                key = normalize(cond)
                if not key:
                    continue
                target = diseases.get(key)
                if target:
                    e = (target, idx, REL_DISEASE)
                    if e not in seen_edges:
                        seen_edges.add(e)
                        ew.writerow([target, idx, REL_DISEASE, "featured in"])
                        stats["edges_disease"] += 1

    linked = len({e[1] for e in seen_edges})
    logger.info(f"wrote {stats['nodes']} nodes → {nodes_path}")
    logger.info(
        f"wrote {stats['edges_drug'] + stats['edges_disease']} edges → {edges_path} "
        f"(drug={stats['edges_drug']}, disease={stats['edges_disease']})"
    )
    pct = 100.0 * linked / max(stats["nodes"], 1)
    logger.info(f"LINKAGE: {linked}/{stats['nodes']} trials ({pct:.1f}%) connect to an existing graph node")
    if pct < 5:
        logger.warning("linkage is very low — check normalize() and the graph name maps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
