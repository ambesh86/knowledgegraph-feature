"""Embed Neo4j graph entities into the Milvus corpus collection.

The `pubmed` collection only ever held 8 hardcoded seed summaries, so vector
search had nothing meaningful to contribute and fusion was pointless. This
service populates a real corpus straight from the graph — so the vector store and
the graph describe the SAME entities, which is the precondition for fusing their
results.

Documents are built per node label:

  clinical_trial : title + conditions + interventions + sponsor + status + phase
  drug / disease : the entity name (short, but makes fuzzy entity resolution work
                   when the user's phrasing doesn't match the canonical name)

Run inside the container (needs pymilvus + sentence-transformers):

    docker exec eugene-ws python -m foundation.vector.corpus_ingest_service \\
        --labels clinical_trial --batch 256
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)

CORPUS_COLLECTION = "eugene_corpus"
# Labels we know how to turn into a useful document. Order is stable so the
# synthetic integer ids assigned below are reproducible across runs.
SUPPORTED_LABELS = ("clinical_trial", "drug", "disease", "paper_chunk")


def _doc_for(label: str, props: dict) -> str:
    """Render a node into the text that gets embedded."""
    name = props.get("node_name") or ""
    if label == "paper_chunk":
        # The passage itself is the retrievable unit — embedding a truncated
        # node_name would defeat the point of extracting full text.
        return props.get("text") or name
    if label != "clinical_trial":
        return name
    parts = [name]
    for key, prefix in (
        ("conditions", "Conditions"),
        ("interventions", "Interventions"),
        ("sponsor", "Sponsor"),
        ("status", "Status"),
        ("phase", "Phase"),
    ):
        val = props.get(key)
        if val:
            parts.append(f"{prefix}: {val}")
    return ". ".join(p for p in parts if p)


def ingest(labels: list[str], batch: int = 256, limit: int | None = None) -> dict:
    """(Re)build the corpus collection from the graph. Returns per-label counts."""
    from pymilvus import MilvusClient

    from foundation.conf.conf import _neo4j_driver
    from foundation.vector.vector_search_service import vector_search_service

    svc = vector_search_service()
    client: MilvusClient = svc._get_client()  # reuse the configured milvus-lite handle

    if client.has_collection(CORPUS_COLLECTION):
        logger.info(f"dropping existing '{CORPUS_COLLECTION}' for a clean rebuild")
        client.drop_collection(CORPUS_COLLECTION)
    client.create_collection(
        collection_name=CORPUS_COLLECTION,
        dimension=384,  # all-MiniLM-L6-v2
        metric_type="IP",  # vectors are normalized, so IP == cosine
        auto_id=False,
    )

    driver = _neo4j_driver()
    counts: dict[str, int] = {}
    next_id = 0

    for label in labels:
        if label not in SUPPORTED_LABELS:
            logger.warning(f"skipping unsupported label {label!r}")
            continue
        # Literal per label — the driver requires LiteralString and the label
        # must never come from interpolated input.
        query = {
            "clinical_trial": (
                "MATCH (n:clinical_trial) RETURN n.node_id AS node_id, "
                "n.node_index AS node_index, n.node_name AS node_name, "
                "n.conditions AS conditions, n.interventions AS interventions, "
                "n.sponsor AS sponsor, n.status AS status, n.phase AS phase, "
                "n.url AS url"
            ),
            "drug": (
                "MATCH (n:drug) RETURN n.node_id AS node_id, "
                "n.node_index AS node_index, n.node_name AS node_name, "
                "null AS conditions, null AS interventions, null AS sponsor, "
                "null AS status, null AS phase, null AS url"
            ),
            "disease": (
                "MATCH (n:disease) RETURN n.node_id AS node_id, "
                "n.node_index AS node_index, n.node_name AS node_name, "
                "null AS conditions, null AS interventions, null AS sponsor, "
                "null AS status, null AS phase, null AS url"
            ),
            # `chunk_id` doubles as node_index so the fusion dedup key and the
            # evidence renderer both resolve from the same value.
            "paper_chunk": (
                "MATCH (p:paper)-[:has_chunk]->(n:paper_chunk) "
                "RETURN n.chunk_id AS node_id, n.chunk_id AS node_index, "
                "n.node_name AS node_name, n.text AS text, n.doc_id AS doc_id, "
                "n.page AS page, n.chunk_type AS chunk_type, p.title AS paper_title, "
                "null AS conditions, null AS interventions, null AS sponsor, "
                "null AS status, null AS phase, p.url AS url"
            ),
        }[label]

        from neo4j import Query

        records, _, _ = driver.execute_query(Query(query))  # type: ignore[arg-type]
        if limit:
            records = records[:limit]
        logger.info(f"[{label}] {len(records)} nodes to embed")

        buf: list[dict] = []
        written = 0
        for rec in records:
            props = dict(rec)
            text = _doc_for(label, props)
            if not text.strip():
                continue
            buf.append({"props": props, "text": text})
            if len(buf) >= batch:
                next_id = _flush(client, svc, buf, label, next_id)
                written += len(buf)
                buf = []
                logger.info(f"[{label}] embedded {written}/{len(records)}")
        if buf:
            next_id = _flush(client, svc, buf, label, next_id)
            written += len(buf)
        counts[label] = written
        logger.info(f"[{label}] done — {written} documents")

    total = int(client.get_collection_stats(CORPUS_COLLECTION).get("row_count", 0))
    logger.info(f"corpus '{CORPUS_COLLECTION}' now holds {total} rows")
    return {"collection": CORPUS_COLLECTION, "per_label": counts, "rows": total}


def _flush(client, svc, buf: list[dict], label: str, next_id: int) -> int:
    vectors = svc._embed([b["text"] for b in buf])
    rows = []
    for b, vec in zip(buf, vectors):
        p = b["props"]
        rows.append(
            {
                "id": next_id,
                "vector": vec,
                "doc_id": str(p.get("node_id") or ""),
                "node_index": str(p.get("node_index") or ""),
                "label": label,
                "name": (p.get("node_name") or "")[:500],
                "text": b["text"][:2000],
                "url": p.get("url") or "",
                # Carried so a retrieved passage can prove itself. Named
                # `ade_doc_id`, NOT `doc_id`: `doc_id` above already means "the
                # graph node's id" for every other label, and reusing the key
                # would silently overwrite it for the whole corpus.
                "ade_doc_id": p.get("doc_id") or "",
                "page": p.get("page") if p.get("page") is not None else -1,
                "paper_title": (p.get("paper_title") or "")[:300],
            }
        )
        next_id += 1
    client.insert(collection_name=CORPUS_COLLECTION, data=rows)
    return next_id


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--labels",
        default="clinical_trial",
        help=f"comma-separated node labels to embed (of {','.join(SUPPORTED_LABELS)})",
    )
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--limit", type=int, default=None, help="cap per label (smoke tests)")
    args = ap.parse_args()

    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    result = ingest(labels=labels, batch=args.batch, limit=args.limit)
    print(result)
    return 0


if __name__ == "__main__":
    # Allow `python -m foundation.vector.corpus_ingest_service` from /app/src.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.exit(main())
