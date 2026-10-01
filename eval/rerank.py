"""Cross-encoder reranking over the fused evidence list.

Why rerank at all when fusion already ranks: RRF ranks by *position in two
retrievers*, and neither retriever ever sees the question and the passage
together. Milvus compares two independently-embedded vectors; Neo4j's full-text
index scores term overlap. Both are bi-encoders in effect — cheap, and blind to
whether a passage actually answers the question.

A cross-encoder reads the query and the passage in one pass, so it can tell
"table listing p values for rat proteomics accessions" from "table listing
patient counts per study" when both mention the same words. That distinction is
exactly what a table-cell lookup turns on, and it is invisible to RRF.

Reranking is applied AFTER fusion, not instead of it: fusion's job is recall
across two stores, the reranker's job is precision within what recall found.

`cohere` calls Cohere's hosted rerank endpoint and needs `COHERE_API_KEY`.
`lexical` is a dependency-free fallback that scores exact overlap of the
question's quoted spans against the passage — much weaker than a real
cross-encoder, but it needs no key and makes the harness runnable anywhere.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

COHERE_URL = "https://api.cohere.com/v2/rerank"
COHERE_MODEL = os.environ.get("COHERE_RERANK_MODEL", "rerank-v3.5")
# Cohere charges per document and truncates long ones anyway; passages beyond
# this are tables whose head already carries the header row we match on.
_MAX_DOC_CHARS = 4000


class RerankUnavailable(RuntimeError):
    pass


def _doc_text(hit: dict) -> str:
    return (hit.get("text") or hit.get("name") or "")[:_MAX_DOC_CHARS]


def cohere(query: str, hits: list[dict], top_k: int) -> list[dict]:
    key = os.environ.get("COHERE_API_KEY", "").strip()
    if not key:
        raise RerankUnavailable(
            "COHERE_API_KEY is not set — cannot rerank with Cohere. "
            "Set it in docker.env or the environment, or use --rerank lexical."
        )
    docs = [_doc_text(h) for h in hits]
    if not docs:
        return hits
    body = json.dumps(
        {"model": COHERE_MODEL, "query": query, "documents": docs, "top_n": min(top_k, len(docs))}
    ).encode()
    req = urllib.request.Request(
        COHERE_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raise RerankUnavailable(f"Cohere rerank failed: {e.code} {e.read()[:300]!r}") from e
    out = []
    for r in payload.get("results", []):
        hit = dict(hits[r["index"]])
        hit["rerank_score"] = r.get("relevance_score")
        out.append(hit)
    return out


# The question quotes the row label and the column header. A passage that
# contains both quoted spans verbatim is almost certainly the right table.
_QUOTED = re.compile(r'"([^"]+)"')


def lexical(query: str, hits: list[dict], top_k: int) -> list[dict]:
    spans = [s.lower() for s in _QUOTED.findall(query) if len(s) >= 3]
    if not spans:
        return hits[:top_k]

    def score(h: dict) -> tuple[int, float]:
        text = _doc_text(h).lower()
        return (sum(1 for s in spans if s in text), float(h.get("rrf_score") or 0.0))

    return sorted(hits, key=score, reverse=True)[:top_k]


REGISTRY = {
    "none": None,
    # Handled inside eugene_ws (`?rerank=true`), not here — see harness.run.
    "service": None,
    "cohere": cohere,
    "lexical": lexical,
}


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(f"unknown reranker {name!r}; have {list(REGISTRY)}")
    return REGISTRY[name]
