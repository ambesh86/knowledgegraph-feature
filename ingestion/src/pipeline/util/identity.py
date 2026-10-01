"""Deterministic identity for documents and chunks — mechanism M2.

The single most important property in this pipeline: re-parsing an unchanged
document must reproduce byte-identical identifiers, years later. Everything else
depends on it.

The previous implementation used `uuid.uuid4()` per chunk. That meant every
re-ingest minted new ids, silently orphaning every stored evidence link — a
citation could quietly start pointing at nothing, or at the wrong paragraph, and
nothing in the system would notice. Deterministic ids remove that failure class
rather than mitigating it.

The same id is the Neo4j `chunk_id` AND the Milvus primary key. There is no join
map between the two stores, because a join map is precisely the thing that drifts
on re-ingestion.
"""
from __future__ import annotations

import hashlib
import re

_NONWORD = re.compile(r"[^a-z0-9]+")

# 32 hex chars of SHA-1. Collision risk across a corpus of millions of chunks is
# negligible, and short ids keep URLs and Cypher readable.
_ID_LEN = 32


def doc_id_for(source: str, identifier: str) -> str:
    """Stable, filesystem- and URL-safe document id.

    Deliberately human-readable (`pmc13202553`) rather than a hash: it appears in
    S3 prefixes and evidence URLs, and being able to eyeball which paper a path
    refers to is worth more than uniformity.
    """
    raw = identifier.strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    slug = _NONWORD.sub("_", raw).strip("_")
    return slug[:120] or f"{source}_unknown"


def chunk_id_for(doc_id: str, ordinal: int, element_id: str) -> str:
    """Deterministic chunk id from (document, position, parser element).

    All three components are needed:
      * `doc_id`   — scopes the id to its document.
      * `ordinal`  — distinguishes chunks the parser labels identically.
      * `element_id` — the parser's own handle for the element (page + block
        index), so a chunk keeps its id even if unrelated chunks are added or
        removed elsewhere in the document.
    """
    seed = f"{doc_id}:{ordinal}:{element_id}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:_ID_LEN]


def element_id_for(page: int, block_index: int, kind: str) -> str:
    """The parser's native handle for a page element.

    Position-based rather than content-based on purpose: a chunk whose wording is
    corrected in a revised PDF should keep its identity, because it is still the
    same passage in the same place.
    """
    return f"p{page}-{kind}{block_index}"


def content_hash(text: str) -> str:
    """SHA-256 of the chunk's verbatim text — mechanism M1.

    Two jobs. It lets the loader skip unchanged content cheaply, and it lets any
    stored answer be checked against the exact text that backed it: if the hash
    still matches, the evidence is provably the same bytes it was when cited.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def document_hash(data: bytes) -> str:
    """SHA-256 of the source PDF, for skip-unchanged and replayability."""
    return hashlib.sha256(data).hexdigest()
