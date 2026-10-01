"""Cached internet-reachability probe.

The product rule is: always prefer live data; fall back to the internal snapshot
ONLY when the internet is genuinely unreachable, and when that happens tell the
user plainly rather than passing stale data off as current.

To do that the agent has to know, before it answers, whether it is online. We
probe once and cache for a short TTL so a burst of turns costs one HTTP call, not
one per turn — and so a probe failure cannot add seconds of latency to every
request.

Deliberately conservative: the probe hits the SAME hosts the external tools use
(NCBI, ClinicalTrials.gov), because "can reach the public internet" is not the
question — "can reach the sources we actually cite" is. A sealed VPC that can
reach example.com but not NCBI must count as offline.
"""
from __future__ import annotations

import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

# Probing the real upstreams, not a generic canary — see module docstring.
_PROBE_URLS = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&retmode=json",
    "https://clinicaltrials.gov/api/v2/version",
)
_TTL_S = float(os.environ.get("EUGENE_CONNECTIVITY_TTL_S", "60"))
_TIMEOUT_S = float(os.environ.get("EUGENE_CONNECTIVITY_TIMEOUT_S", "4"))

_lock = threading.Lock()
_cache: dict[str, float | bool] = {"online": True, "checked_at": 0.0}


def _probe() -> bool:
    for url in _PROBE_URLS:
        try:
            r = requests.get(
                url,
                timeout=_TIMEOUT_S,
                headers={"User-Agent": "Eugene-Agent/2.0 (connectivity probe)"},
            )
            if r.status_code < 500:
                return True
        except requests.RequestException as e:
            logger.debug(f"connectivity probe failed for {url}: {e}")
    return False


def is_online(force: bool = False) -> bool:
    """True if the upstream research sources are reachable. Cached for `_TTL_S`."""
    now = time.time()
    with _lock:
        age = now - float(_cache["checked_at"])
        if not force and age < _TTL_S and _cache["checked_at"]:
            return bool(_cache["online"])

    online = _probe()
    with _lock:
        previous = bool(_cache["online"])
        _cache["online"] = online
        _cache["checked_at"] = time.time()
    if online != previous:
        logger.warning(f"connectivity changed: online={online}")
    return online


def status() -> dict:
    """Current connectivity state without forcing a probe (for health endpoints)."""
    with _lock:
        return {
            "online": bool(_cache["online"]),
            "checked_at": float(_cache["checked_at"]),
            "ttl_s": _TTL_S,
        }
