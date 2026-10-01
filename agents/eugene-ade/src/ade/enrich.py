"""Domain enrichment — tagging chunks with the entities they mention.

The reference pipeline stamps every chunk with `carrier`, `policy_type`,
`jurisdiction`, `document_category`. That is what makes its structured retrieval
possible: a SPARQL query can demand `?chunk ev:carrier "chubb"` as a mandatory
triple and filter thousands of chunks down to dozens before any ranking happens.

Our domain equivalent is drugs, diseases and therapeutic areas. Without these
tags the graph retriever can only match full text, which is exactly the recall
problem hybrid retrieval exists to fix — "BAFF inhibitor" and "telitacicept"
never match lexically even though one is an instance of the other.

The vocabulary is read from the graph itself (7,957 drugs, 17,080 diseases)
rather than hardcoded, so it stays in step with whatever has been ingested.
Matching is word-boundary exact on a normalized form: a chunk mentioning
"Rituximab" gets tagged, one mentioning "rituximab-adjacent" does not.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any

logger = logging.getLogger(__name__)

_PAREN = re.compile(r"\([^)]*\)")
_NONWORD = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")

# Short names generate false positives inside ordinary prose ("Iron", "Oxygen",
# "Gold"), so the vocabulary excludes them. A missed tag is recoverable; a wrong
# one silently pollutes structured filtering.
_MIN_TERM_LEN = 6
# Cap per chunk: a references section can name forty drugs without being *about*
# any of them.
_MAX_TAGS = 8

_lock = threading.Lock()
_vocab: dict[str, list[tuple[str, str]]] | None = None


def _normalize(text: str) -> str:
    s = (text or "").lower().strip()
    s = _PAREN.sub(" ", s)
    s = _NONWORD.sub(" ", s)
    return _WS.sub(" ", s).strip()


def _load_vocab() -> dict[str, list[tuple[str, str]]]:
    """Build {label: [(normalized_name, canonical_name)]} from the graph."""
    global _vocab
    if _vocab is not None:
        return _vocab
    with _lock:
        if _vocab is not None:
            return _vocab
        out: dict[str, list[tuple[str, str]]] = {"drug": [], "disease": []}
        try:
            from neo4j import GraphDatabase, Query

            drv = GraphDatabase.driver(
                os.environ.get("NEO4J_URI", "bolt://neo4j:7687"),
                auth=(
                    os.environ.get("NEO4J_USERNAME", "neo4j"),
                    os.environ.get("NEO4J_PASSWORD", "eugene_local_2024"),
                ),
            )
            with drv:
                for label, cypher in (
                    ("drug", "MATCH (n:drug) WHERE n.node_name IS NOT NULL RETURN n.node_name AS name"),
                    ("disease", "MATCH (n:disease) WHERE n.node_name IS NOT NULL RETURN n.node_name AS name"),
                ):
                    recs, _, _ = drv.execute_query(Query(cypher))  # type: ignore[arg-type]
                    seen: set[str] = set()
                    for r in recs:
                        norm = _normalize(r["name"])
                        if len(norm) >= _MIN_TERM_LEN and norm not in seen:
                            seen.add(norm)
                            out[label].append((norm, r["name"]))
            logger.info(
                f"enrichment vocabulary: {len(out['drug'])} drugs, {len(out['disease'])} diseases"
            )
        except Exception as e:
            # Enrichment is additive. A graph that is down must not stop
            # extraction — the chunks are still valid, just untagged.
            logger.warning(f"could not load enrichment vocabulary: {e}")
        _vocab = out
        return _vocab


def tag_chunk(text: str) -> dict[str, Any]:
    """Return the drug/disease entities a chunk mentions."""
    vocab = _load_vocab()
    if not text or not any(vocab.values()):
        return {}
    hay = f" {_normalize(text)} "

    drugs: list[str] = []
    diseases: list[str] = []
    for label, bucket in (("drug", drugs), ("disease", diseases)):
        for norm, canonical in vocab.get(label, []):
            # Space-padded containment == word-boundary match, without paying for
            # a regex per term across 25k terms.
            if f" {norm} " in hay:
                bucket.append(canonical)
                if len(bucket) >= _MAX_TAGS:
                    break

    out: dict[str, Any] = {}
    if drugs:
        out["drugs"] = drugs
    if diseases:
        out["diseases"] = diseases
    return out


def document_areas(chunks: list[dict[str, Any]], top_n: int = 3) -> list[str]:
    """The therapeutic areas a document is actually about.

    Derived from tag frequency across chunks rather than from the title alone: a
    review names many conditions, but the ones it keeps returning to are its
    subject.
    """
    counts: dict[str, int] = {}
    for c in chunks:
        # Skip table cells: an adverse-event table names a dozen incidental
        # conditions, and counting each cell made a paper about IgA nephropathy
        # report its areas as "tonsillitis, nasopharyngitis". Prose mentions
        # reflect what a document is about; table cells reflect what it tabulates.
        if c.get("chunk_type") == "table_cell":
            continue
        for d in (c.get("diseases") or []):
            counts[d] = counts.get(d, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]
