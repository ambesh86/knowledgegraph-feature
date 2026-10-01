#!/usr/bin/env python3
"""Batch-download ClinicalTrials.gov studies for Eugene's research themes.

Replaces the recursive, pageSize=25 path in `src/clinicaltrail/` (which duplicates
a CSV header per page and blows the stack on large pulls). This one:

  * uses API v2 JSON (richer than the CSV projection, and `nextPageToken` is in
    the body rather than a header),
  * pages with a `while` loop at the API max `pageSize=1000`,
  * retries with exponential backoff on 429 / 5xx,
  * deduplicates by NCT id across themes (a study can match several),
  * is resumable — an existing output file is loaded and only new studies fetched.

Themes mirror `agents/eugene-agent-ui-next/lib/atlas/areas.ts` so the ingested
trials line up with the focus areas the Atlas intelligence feed already uses.

Usage:
    python3 bin/ctgov/download_ctgov.py --months 12 --out dumps/ct_import/ctgov_raw.json
    python3 bin/ctgov/download_ctgov.py --theme hematology --months 12
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("ctgov")

API = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000  # API maximum
MAX_RETRIES = 5
BACKOFF_BASE_S = 2.0
# ClinicalTrials.gov asks that automated clients identify themselves.
USER_AGENT = "Eugene-KG/1.0 (biomedical knowledge graph; +https://csl.com)"

# Research themes, mirroring lib/atlas/areas.ts. `cond` drives query.cond
# (condition/disease) and `intr` drives query.intr (intervention/drug); a theme
# may use either or both.
THEMES: dict[str, dict[str, str]] = {
    "hematology": {
        "cond": "hemophilia OR von Willebrand disease OR bleeding disorder",
        "intr": "factor VIII OR factor IX OR gene therapy OR emicizumab",
    },
    "nephrology": {
        "cond": "IgA nephropathy OR C3 glomerulopathy OR glomerular disease",
        "intr": "complement inhibitor OR C3 inhibitor",
    },
    "immunology": {
        "cond": "primary immunodeficiency OR CIDP OR chronic inflammatory demyelinating polyneuropathy",
        "intr": "immunoglobulin OR subcutaneous immunoglobulin",
    },
    "oncology": {
        "cond": "lymphoma OR multiple myeloma",
        "intr": "bispecific antibody OR CAR-T OR chimeric antigen receptor",
    },
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"accept": "application/json", "User-Agent": USER_AGENT})
    return s


def _get_with_retry(sess: requests.Session, params: dict) -> dict[str, Any]:
    """GET with exponential backoff on throttling and transient server errors."""
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = sess.get(API, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = BACKOFF_BASE_S * (2**attempt)
                logger.warning(
                    f"HTTP {resp.status_code} — backing off {wait:.0f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                continue
            # 4xx other than 429 is a request bug; retrying won't help.
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        except requests.RequestException as e:
            last = e
            wait = BACKOFF_BASE_S * (2**attempt)
            logger.warning(f"{type(e).__name__}: {e} — retry in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"exhausted {MAX_RETRIES} retries; last error: {last}")


def _date_filter(months: int) -> str:
    """`filter.advanced` clause restricting StartDate to the last `months`."""
    today = dt.date.today()
    start = today - dt.timedelta(days=int(months * 30.44))
    return f"AREA[StartDate]RANGE[{start.isoformat()},{today.isoformat()}]"


def fetch_theme(
    sess: requests.Session, theme: str, months: int, max_studies: int | None
) -> Iterator[dict]:
    """Yield every study matching `theme` within the date window, page by page."""
    spec = THEMES[theme]
    base = {
        "pageSize": PAGE_SIZE,
        "filter.advanced": _date_filter(months),
        "countTotal": "true",
    }
    # Condition and intervention are queried separately and unioned by the
    # caller's dedup — combining them in one request ANDs them, which is far too
    # narrow (it would require a trial to match both the disease and the drug list).
    for field, key in (("cond", "query.cond"), ("intr", "query.intr")):
        term = spec.get(field)
        if not term:
            continue
        params = dict(base)
        params[key] = term
        token: str | None = None
        page = 0
        fetched = 0
        while True:
            if token:
                params["pageToken"] = token
            payload = _get_with_retry(sess, params)
            studies = payload.get("studies", []) or []
            if page == 0 and payload.get("totalCount") is not None:
                logger.info(
                    f"  [{theme}/{field}] totalCount={payload['totalCount']}"
                )
            for st in studies:
                yield st
            fetched += len(studies)
            page += 1
            logger.info(
                f"  [{theme}/{field}] page {page}: +{len(studies)} (running {fetched})"
            )
            token = payload.get("nextPageToken")
            if not token or not studies:
                break
            if max_studies and fetched >= max_studies:
                logger.info(f"  [{theme}/{field}] hit --max-studies cap")
                break
            time.sleep(0.2)  # be polite to a free public API


def nct_of(study: dict) -> str:
    return (
        study.get("protocolSection", {})
        .get("identificationModule", {})
        .get("nctId", "")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        default="dumps/ct_import/ctgov_raw.json",
        help="output JSON file (one object: {nct_id: study})",
    )
    ap.add_argument("--months", type=int, default=12, help="lookback window")
    ap.add_argument(
        "--theme",
        action="append",
        choices=sorted(THEMES),
        help="restrict to one or more themes (default: all)",
    )
    ap.add_argument(
        "--max-studies",
        type=int,
        default=None,
        help="cap per theme/field — for smoke tests",
    )
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Resumable: keep whatever we already have and only add new NCT ids.
    studies: dict[str, dict] = {}
    if out.exists():
        try:
            studies = json.loads(out.read_text())
            logger.info(f"resuming — {len(studies)} studies already in {out}")
        except Exception as e:
            logger.warning(f"could not read existing {out} ({e}); starting fresh")

    themes = args.theme or sorted(THEMES)
    sess = _session()
    logger.info(
        f"themes={themes} window={args.months}mo filter={_date_filter(args.months)}"
    )

    for theme in themes:
        before = len(studies)
        logger.info(f"── {theme} ──")
        for st in fetch_theme(sess, theme, args.months, args.max_studies):
            nct = nct_of(st)
            if not nct:
                continue
            # Record which theme(s) surfaced this study — carried into the graph.
            existing = studies.get(nct)
            if existing:
                th = set(existing.get("_eugene_themes", []))
                th.add(theme)
                existing["_eugene_themes"] = sorted(th)
            else:
                st["_eugene_themes"] = [theme]
                studies[nct] = st
        logger.info(f"── {theme}: +{len(studies) - before} new (total {len(studies)})")

    out.write_text(json.dumps(studies, indent=None))
    logger.info(f"wrote {len(studies)} unique studies → {out} ({out.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
