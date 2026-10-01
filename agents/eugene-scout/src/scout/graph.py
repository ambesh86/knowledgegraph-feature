"""Entity linkage against Eugene's Neo4j knowledge graph.

This is the use case's "links them to CSL's internal ontology stored in HealthLake",
implemented against the ontology this stack actually has: the graph behind
`eugene_ws`, holding ~7,957 drugs and ~17,080 diseases.

**Linkage is context, not score — and that is a deliberate inversion.**

The obvious implementation would add "is this entity already in our graph?" as a
seventh scoring factor. That would be backwards for this use case. The BD team is
hunting for assets they do *not* already track; a drug absent from the graph is more
likely to be the novel opportunity, not less relevant. Scoring on graph membership
would systematically rank the familiar above the new and quietly defeat the whole
"before it becomes widely known" premise.

So what this produces is an annotation an analyst reads — "this trial concerns
emicizumab, which is already in our competitive map" — while the ranking stays driven
by the six factors in `scoring.py`. The graph tells you *where a signal sits* relative
to what CSL knows. It does not tell you how much it matters.

Degradation is graceful: if `eugene_ws` is unreachable, signals simply carry no graph
annotations. The scan does not slow down and does not fail — a knowledge-graph lookup
is a nice-to-have on top of intelligence that is already complete without it.

The threshold for "unreachable" is deliberately not one failed request. It was, and a
single 14s outlier on an otherwise-healthy endpoint (median ~20ms) was enough to strip
the annotations off an entire due-diligence run. Three consecutive failures is the bar
now; see `_MAX_CONSECUTIVE_FAILURES`. The underlying slowness was a query fan-out in
`eugene_ws` and has been fixed there — this is the second line of defence, not the fix.
"""
from __future__ import annotations

import logging
import threading
import urllib.parse
from typing import Any

import requests

from scout import config as cfg
from scout.models import GraphEntity
from scout.text import normalize

logger = logging.getLogger(__name__)

# One scan looks up the same handful of terms across hundreds of signals — every
# hemophilia trial mentions "hemophilia". Without a cache that is hundreds of
# identical HTTP round trips; with one it is a few dozen.
_CACHE: dict[str, list[GraphEntity]] = {}
_CACHE_LOCK = threading.Lock()

# Bounded so a pathological run cannot grow the cache without limit across a long
# process lifetime. Far above the number of distinct terms a scan actually produces.
_MAX_CACHE = 4096

# Per-signal lookup budget. Entity linkage is an annotation; it must never dominate
# the runtime of the scan it is annotating.
_MAX_TERMS_PER_SIGNAL = 6

# Short by design. This is an optional enrichment on an internal service — waiting
# on it is worse than going without it.
_TIMEOUT_S = 4.0

# How many failures in a row before linkage is given up for the run.
#
# This used to be 1, and one blip cost every annotation in the run. The measured
# behaviour of `/node/find` is heavy-tailed rather than binary: ~20ms at the median
# across 107 observed calls, with a single 14s outlier. Treating that outlier as "the
# graph is down" was wrong — the graph was up, and every subsequent lookup would have
# succeeded in milliseconds.
#
# Consecutive, not cumulative: a service that is genuinely down still costs at most
# three timeouts, while a service that is merely occasionally slow keeps working. The
# counter resets on any success.
_MAX_CONSECUTIVE_FAILURES = 3


class GraphClient:
    """Thin client over the `eugene_ws` node lookup, with caching and a hard
    never-raise contract."""

    def __init__(self, base_url: str | None = None, session: requests.Session | None = None):
        self.base_url = (base_url or cfg.core_api_url()).rstrip("/")
        self._session = session or requests.Session()
        self._available = True  # flipped off after repeated failures, for the run
        self._consecutive_failures = 0
        self._failures = 0  # total, for the run summary

    def lookup(self, term: str) -> list[GraphEntity]:
        """Resolve one term to graph nodes. Returns [] on anything unexpected."""
        key = normalize(term)
        if not key or len(key) < 3:
            return []

        with _CACHE_LOCK:
            cached = _CACHE.get(key)
        if cached is not None:
            return cached

        if not self._available:
            # Return without caching. `_CACHE` is module-level and outlives the run, so
            # storing [] here would record "the graph has no such node" for every term
            # seen while the graph was unreachable — and that wrong answer would then
            # be served to every later run in this process, long after it recovered.
            return []

        entities: list[GraphEntity] = []
        try:
            res = self._session.get(
                f"{self.base_url}/node/find/{urllib.parse.quote(term, safe='')}",
                headers={"Accept": "application/json"},
                timeout=_TIMEOUT_S,
            )
            if res.status_code == 200:
                payload: dict[str, Any] = res.json()
                for row in (payload.get("results") or [])[:3]:
                    node_id, value = row.get("id"), row.get("value")
                    if node_id and value:
                        entities.append(
                            GraphEntity(id=str(node_id), value=str(value), matched_term=term)
                        )
            self._consecutive_failures = 0
        except Exception as e:  # noqa: BLE001
            # A slow response is not a dead service. Tolerate a short run of failures,
            # then give up so a genuinely down graph costs a handful of timeouts rather
            # than one per term.
            self._failures += 1
            self._consecutive_failures += 1
            if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.warning(
                    f"graph lookup failed {self._consecutive_failures}x in a row "
                    f"({type(e).__name__}: {e}); disabling entity linkage for this run"
                )
                self._available = False
            else:
                logger.info(
                    f"graph lookup for {term!r} failed ({type(e).__name__}); "
                    f"continuing ({self._consecutive_failures}/"
                    f"{_MAX_CONSECUTIVE_FAILURES} before linkage is disabled)"
                )
            # Do NOT cache a failed lookup. An empty list here would be indistinguishable
            # from "the graph says no such node", and one slow request would become a
            # permanent wrong answer for that term.
            return []

        with _CACHE_LOCK:
            if len(_CACHE) < _MAX_CACHE:
                _CACHE[key] = entities
        return entities

    def link(self, terms: list[str]) -> list[GraphEntity]:
        """Resolve a signal's candidate terms, de-duplicated, within budget."""
        seen: set[str] = set()
        out: list[GraphEntity] = []
        for term in terms[:_MAX_TERMS_PER_SIGNAL]:
            for entity in self.lookup(term):
                if entity.id not in seen:
                    seen.add(entity.id)
                    out.append(entity)
        return out

    @property
    def available(self) -> bool:
        return self._available


def clear_cache() -> None:
    """Test hook, and a way to force re-resolution after the graph is re-ingested."""
    with _CACHE_LOCK:
        _CACHE.clear()
