"""External search tools — real web-backed patent and literature lookup.

These are native Strands tools (not MCP) so they live inside the agent process.
They hit stable, scraper-friendly public APIs (NCBI E-utilities, Google Patents
deep links) rather than scraping HTML-rendered sites that block bots.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus

import requests
from strands import tool

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _freshness(dates: list[str], live: bool = True) -> dict[str, Any]:
    """Summarize how recent a result set actually is.

    Every tool attaches this so the model can date its claims from real values
    instead of guessing — and so an old result set is visibly old rather than
    silently presented as "the latest".
    """
    usable = sorted(d for d in dates if d and _YEAR_RE.search(str(d)))
    today = dt.date.today()
    out: dict[str, Any] = {
        "as_of": today.isoformat(),
        "live": live,
        "newest": usable[-1] if usable else None,
        "oldest": usable[0] if usable else None,
    }
    if usable:
        newest_year = int(_YEAR_RE.search(str(usable[-1])).group(0))  # type: ignore[union-attr]
        age = today.year - newest_year
        out["newest_age_years"] = age
        if age >= 2:
            out["stale_warning"] = (
                f"The most recent result is from {newest_year}, about {age} years old. "
                "Tell the user this explicitly — it may not reflect current evidence."
            )
    return out


# A descriptive User-Agent. Many public endpoints (and NCBI's usage policy)
# rate-limit or 403 the default `python-requests/x.y` agent; identifying the
# client makes "full internet access" actually reliable rather than blocked.
_USER_AGENT = (
    "Eugene-Agent/2.0 (CSL Behring biomedical knowledge graph; "
    "+https://github.com/aisemanticexpert/knowledgegraph)"
)
_session = requests.Session()
_session.headers.update(
    {"User-Agent": _USER_AGENT, "Accept": "application/json, text/*;q=0.9"}
)

_PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# NCBI throttles anonymous clients to ~3 requests/second and answers 429 beyond
# that. Each search_pubmed call makes two requests (esearch + esummary), so two
# searches in quick succession can trip it — observed in testing. A short bounded
# retry turns a hard failure into a slight delay; without it the tool returns
# empty and the model is tempted to fall back on remembered literature, which is
# exactly the staleness this work exists to prevent.
_NCBI_RETRIES = 3
_NCBI_BACKOFF_S = 0.6


def _ncbi_get(url: str, params: dict[str, Any]) -> requests.Response:
    last: requests.Response | None = None
    for attempt in range(_NCBI_RETRIES):
        resp = _session.get(url, params=params, timeout=12)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        last = resp
        wait = _NCBI_BACKOFF_S * (2**attempt)
        logger.info(f"NCBI 429 — backing off {wait:.1f}s (attempt {attempt + 1})")
        time.sleep(wait)
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("NCBI request failed after retries")


_PATENTS_GOOGLE_SEARCH = "https://patents.google.com/?q={query}"
_PATENTS_GOOGLE_VIEW = "https://patents.google.com/patent/{id}"


@tool
def search_pubmed(
    query: str,
    max_results: int = 5,
    recent_days: int = 0,
    sort_by_relevance: bool = False,
) -> dict[str, Any]:
    """Search PubMed for biomedical literature — NEWEST FIRST by default.

    Uses NCBI's E-utilities API — free, no API key required, reliable.

    Results are sorted most-recent-first because stale research is misleading in
    a competitive-intelligence setting. Only set `sort_by_relevance=True` when the
    user explicitly wants the seminal / most-cited work rather than the latest.

    Args:
        query: free-text search terms (e.g. "atacicept IgA nephropathy").
        max_results: how many records to return (1-20).
        recent_days: if > 0, restrict to items published within this many days
            (e.g. 365 for the last year). 0 = no date restriction.
        sort_by_relevance: True to rank by relevance instead of date.

    Returns {count, results:[{pmid,title,journal,year,pubdate,authors,url}],
             retrieved_at, freshness{as_of,newest,oldest,stale_warning?}}.
    Use `retrieved_at` / `freshness` to date your claims — do not guess.
    """
    if not query or not query.strip():
        return {"count": 0, "results": [], "error": "empty query"}
    n = max(1, min(int(max_results), 20))
    try:
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": n,
        }
        if not sort_by_relevance:
            # NCBI: sort=date returns most recent first. Without this parameter
            # E-utilities defaults to relevance, which skews heavily to older,
            # highly-cited papers — the root of the "stale results" problem.
            params["sort"] = "date"
        if recent_days and int(recent_days) > 0:
            params["datetype"] = "pdat"
            params["reldate"] = int(recent_days)
        # 1. esearch → PMIDs
        esearch = _ncbi_get(f"{_PUBMED_BASE}/esearch.fcgi", params)
        ids = esearch.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return {"count": 0, "results": []}

        # 2. esummary → metadata
        esum = _ncbi_get(
            f"{_PUBMED_BASE}/esummary.fcgi",
            {"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        summaries = esum.json().get("result", {})

        results = []
        for pmid in ids:
            s = summaries.get(pmid) or {}
            if not isinstance(s, dict):
                continue
            authors = [a.get("name", "") for a in (s.get("authors") or [])][:4]
            pubdate = s.get("pubdate", "") or ""
            results.append(
                {
                    "pmid": pmid,
                    "title": s.get("title", ""),
                    "journal": s.get("fulljournalname") or s.get("source", ""),
                    "year": pubdate.split(" ")[0][:4],
                    "pubdate": pubdate,
                    "authors": authors,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )
        return {
            "count": int(esearch.json().get("esearchresult", {}).get("count", len(ids))),
            "results": results,
            "retrieved_at": _now_iso(),
            "sorted_by": "relevance" if sort_by_relevance else "date (newest first)",
            "freshness": _freshness([r["pubdate"] for r in results], live=True),
        }
    except Exception as exc:
        logger.warning(f"search_pubmed failed: {exc}")
        return {
            "count": 0,
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
            "retrieved_at": _now_iso(),
            "offline_hint": (
                "PubMed was unreachable. Do NOT substitute remembered literature — "
                "tell the user the live search failed and give the date."
            ),
        }


@tool
def search_patents_web(query: str) -> dict[str, Any]:
    """Build a Google Patents search URL and expose simple patent-identifier
    deep links. Google Patents' full text is behind bot protection, so this
    tool returns reliable *links* the user can follow.

    Use this when the user asks "find the latest patent about X" or
    "link to the patent for Y" and the Eugene knowledge graph does not have
    the answer.

    Args:
        query: patent topic, assignee, drug name, etc. (e.g. "emicizumab 2024").

    Returns:
        {search_url, hint, example_direct_view_template}
    """
    q = (query or "").strip()
    if not q:
        return {"error": "empty query"}
    return {
        "search_url": _PATENTS_GOOGLE_SEARCH.format(query=quote_plus(q)),
        "hint": (
            "Google Patents full-text extraction is rate-limited; share this "
            "link with the user so they can open it themselves."
        ),
        "example_direct_view_template": _PATENTS_GOOGLE_VIEW.format(id="US-XXXXXXX-B2"),
    }


_CLINICALTRIALS_BASE = "https://clinicaltrials.gov/api/v2/studies"
_EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@tool
def search_clinical_trials(
    query: str,
    max_results: int = 5,
    recruiting_only: bool = False,
    sort_by_relevance: bool = False,
) -> dict[str, Any]:
    """Search ClinicalTrials.gov for LIVE trial records — MOST RECENTLY UPDATED FIRST.

    Use this for real-time trial questions (recruiting status, recent trials,
    sponsors, phases) that the static Eugene graph may not have. Free, no key.

    Sorted by last-update date so you see the current state of the registry rather
    than whatever the relevance ranker surfaces.

    Args:
        query: free-text terms (e.g. "atacicept IgA nephropathy").
        max_results: how many trials to return (1-20).
        recruiting_only: restrict to actively recruiting studies.
        sort_by_relevance: True to rank by relevance instead of recency.

    Returns {count, results:[{nct_id,title,status,phase,sponsor,conditions,
             start_date,last_update,url}], retrieved_at, freshness}.
    Use `retrieved_at` / `freshness` to date your claims — do not guess.
    """
    if not query or not query.strip():
        return {"count": 0, "results": [], "error": "empty query"}
    n = max(1, min(int(max_results), 20))
    try:
        params: dict[str, Any] = {"query.term": query, "pageSize": n}
        if not sort_by_relevance:
            # API v2 field sort — newest registry activity first.
            params["sort"] = "LastUpdatePostDate:desc"
        if recruiting_only:
            params["filter.overallStatus"] = "RECRUITING"
        resp = _session.get(
            _CLINICALTRIALS_BASE,
            params=params,
            timeout=12,
        )
        resp.raise_for_status()
        studies = resp.json().get("studies", [])
        results = []
        for s in studies:
            ps = s.get("protocolSection", {})
            ident = ps.get("identificationModule", {})
            status = ps.get("statusModule", {})
            design = ps.get("designModule", {})
            sponsor = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
            cond = ps.get("conditionsModule", {}).get("conditions", [])
            nct = ident.get("nctId", "")
            last_update = (
                (status.get("lastUpdatePostDateStruct") or {}).get("date", "") or ""
            )
            results.append({
                "nct_id": nct,
                "title": ident.get("briefTitle", ""),
                "status": status.get("overallStatus", ""),
                "phase": ", ".join(design.get("phases", []) or []),
                "sponsor": sponsor.get("name", ""),
                "conditions": cond,
                "start_date": (status.get("startDateStruct") or {}).get("date", "") or "",
                "last_update": last_update,
                "url": f"https://clinicaltrials.gov/study/{nct}" if nct else "",
            })
        return {
            "count": len(results),
            "results": results,
            "retrieved_at": _now_iso(),
            "sorted_by": "relevance" if sort_by_relevance else "last update (newest first)",
            "freshness": _freshness([r["last_update"] for r in results], live=True),
        }
    except Exception as e:
        logger.warning(f"clinical trials search failed: {e}")
        return {
            "count": 0,
            "results": [],
            "error": str(e),
            "retrieved_at": _now_iso(),
            "offline_hint": (
                "ClinicalTrials.gov was unreachable. Do NOT substitute remembered trial "
                "status — say the live lookup failed and give the date."
            ),
        }


@tool
def search_europepmc(
    query: str,
    max_results: int = 5,
    patents_only: bool = False,
    sort_by_relevance: bool = False,
) -> dict[str, Any]:
    """Search Europe PMC for LIVE literature AND patents — NEWEST FIRST by default.

    Broader than PubMed: indexes papers, preprints, patents and more. Use for
    real-time literature and patent-adjacent lookups.

    Args:
        query: free-text terms (e.g. "atacicept IgA nephropathy").
        max_results: how many records (1-20).
        patents_only: if True, restrict to patent documents (adds 'AND SRC:PAT').
        sort_by_relevance: True to rank by relevance instead of publication date.

    Returns {count, returned, results:[...], retrieved_at, freshness}.
    Use `retrieved_at` / `freshness` to date your claims — do not guess.
    """
    if not query or not query.strip():
        return {"count": 0, "results": [], "error": "empty query"}
    n = max(1, min(int(max_results), 20))
    q = f"{query} AND SRC:PAT" if patents_only else query
    try:
        params: dict[str, Any] = {
            "query": q,
            "format": "json",
            "pageSize": n,
            "resultType": "lite",
        }
        if not sort_by_relevance:
            # Europe PMC sort syntax — publication date descending.
            params["sort"] = "P_PDATE_D desc"
        resp = _session.get(
            _EUROPEPMC_BASE,
            params=params,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("resultList", {}).get("result", [])
        results = []
        for h in hits:
            src = h.get("source", "")
            extid = h.get("id", "")
            if src == "MED":
                url = f"https://europepmc.org/article/MED/{extid}"
            elif src == "PAT":
                url = f"https://europepmc.org/article/PAT/{extid}"
            else:
                url = h.get("doi") and f"https://doi.org/{h['doi']}" or ""
            results.append({
                "id": extid,
                "source": src,
                "title": h.get("title", ""),
                "authors": h.get("authorString", ""),
                "year": h.get("pubYear", ""),
                "journal_or_patent": h.get("journalTitle", "") or h.get("source", ""),
                "url": url,
            })
        return {
            "count": int(data.get("hitCount", len(results))),
            "returned": len(results),
            "results": results,
            "retrieved_at": _now_iso(),
            "sorted_by": "relevance" if sort_by_relevance else "publication date (newest first)",
            "freshness": _freshness([str(r["year"]) for r in results], live=True),
        }
    except Exception as e:
        logger.warning(f"europepmc search failed: {e}")
        return {
            "count": 0,
            "results": [],
            "error": str(e),
            "retrieved_at": _now_iso(),
            "offline_hint": (
                "Europe PMC was unreachable. Do NOT substitute remembered literature — "
                "say the live search failed and give the date."
            ),
        }
