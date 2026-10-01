"""Resolve a literature identifier to a downloadable PDF.

Why Europe PMC and not PubMed: PubMed indexes abstracts, and the overwhelming
majority of its records have no freely downloadable PDF. Europe PMC mirrors
PubMed *and* exposes `fullTextUrlList` with per-document PDF links plus an
open-access flag. Measured on a real query during design: 8/8 results carried a
PDF link and 6/8 were open access — via PubMed alone that number would have been
near zero.

A paywalled paper is a NORMAL outcome here, not an error. `PdfUnavailable` carries
a human-readable reason and the publisher link so the UI can say "no open-access
PDF — read at publisher" instead of showing a failure.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

_EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_UA = (
    "Eugene-ADE/1.0 (CSL Behring biomedical knowledge graph; "
    "+https://github.com/aisemanticexpert/knowledgegraph)"
)
_TIMEOUT_S = 45
# Papers are typically 1-10 MB. The cap stops a mis-resolved link from streaming
# something unbounded into memory.
_MAX_PDF_BYTES = 60 * 1024 * 1024

_session = requests.Session()
_session.headers.update({"User-Agent": _UA})


class PdfUnavailable(RuntimeError):
    """No open-access PDF exists for this record — an expected, explainable outcome."""

    def __init__(self, reason: str, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.metadata = metadata or {}


@dataclass
class FetchResult:
    pdf: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


def doc_id_for(source: str, ident: str) -> str:
    """Deterministic, filesystem- and URL-safe document id.

    Deterministic on purpose: re-ingesting the same paper must hit the same S3
    prefix so the pipeline is idempotent and evidence links stay stable forever.
    """
    raw = f"{ident}".strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    slug = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return slug[:120] or f"{source}_unknown"


def _epmc_query(ident: str) -> str:
    """Build a Europe PMC query for whichever identifier flavour we were given."""
    v = ident.strip()
    if re.fullmatch(r"(?i)PMC\d+", v):
        return f"PMCID:{v.upper()}"
    if re.fullmatch(r"\d{5,9}", v):
        return f"EXT_ID:{v} AND SRC:MED"  # PMID
    if v.lower().startswith("10."):
        return f'DOI:"{v}"'
    return v  # free text — last resort


def _select_record(records: list[dict]) -> dict:
    """Prefer an open-access record; otherwise take the first."""
    for r in records:
        if r.get("isOpenAccess") == "Y":
            return r
    return records[0]


def _pdf_urls(record: dict) -> list[str]:
    urls: list[str] = []
    for entry in (record.get("fullTextUrlList", {}) or {}).get("fullTextUrl", []) or []:
        if entry.get("documentStyle") == "pdf" and entry.get("url"):
            # Open-access links first — they are the ones that actually serve bytes.
            if entry.get("availabilityCode") == "OA":
                urls.insert(0, entry["url"])
            else:
                urls.append(entry["url"])
    pmcid = record.get("pmcid")
    if pmcid:
        # Europe PMC's render endpoint — verified during design to return real PDF
        # bytes when the article is in the OA subset.
        fallback = f"https://europepmc.org/articles/{pmcid}?pdf=render"
        if fallback not in urls:
            urls.append(fallback)
    return urls


def _metadata_of(record: dict, pdf_url: str = "") -> dict[str, Any]:
    return {
        "title": record.get("title", ""),
        "authors": record.get("authorString", ""),
        "year": str(record.get("pubYear", "") or ""),
        "journal": (record.get("journalInfo", {}) or {}).get("journal", {}).get("title", ""),
        "doi": record.get("doi", ""),
        "pmid": record.get("pmid", ""),
        "pmcid": record.get("pmcid", ""),
        "is_open_access": record.get("isOpenAccess") == "Y",
        "source_db": record.get("source", ""),
        "pdf_url": pdf_url,
        "publisher_url": f"https://doi.org/{record['doi']}" if record.get("doi") else "",
        "europepmc_url": (
            f"https://europepmc.org/article/{record.get('source', 'MED')}/{record.get('id', '')}"
        ),
    }


def _download_pdf(url: str) -> bytes:
    resp = _session.get(url, timeout=_TIMEOUT_S, stream=True, allow_redirects=True)
    resp.raise_for_status()
    buf = bytearray()
    for block in resp.iter_content(chunk_size=64 * 1024):
        buf.extend(block)
        if len(buf) > _MAX_PDF_BYTES:
            raise PdfUnavailable(f"PDF exceeds {_MAX_PDF_BYTES // 1024 // 1024} MB cap")
    data = bytes(buf)
    # Content-Type lies often enough (publishers return HTML paywall pages with a
    # PDF content type) that the magic bytes are the only trustworthy check.
    if not data.startswith(b"%PDF-"):
        raise PdfUnavailable(
            f"{url} did not return a PDF (got {data[:16]!r}) — likely a paywall page"
        )
    return data


def fetch_pdf(source: str, ident: str) -> FetchResult:
    """Resolve `(source, ident)` to PDF bytes plus bibliographic metadata.

    Raises PdfUnavailable when the record exists but has no reachable open PDF.
    """
    if source == "url":
        return FetchResult(pdf=_download_pdf(ident), metadata={"pdf_url": ident})

    params = {
        "query": _epmc_query(ident),
        "format": "json",
        "pageSize": 5,
        "resultType": "core",
    }
    resp = _session.get(_EPMC_SEARCH, params=params, timeout=_TIMEOUT_S)
    resp.raise_for_status()
    records = (resp.json().get("resultList", {}) or {}).get("result", []) or []
    if not records:
        raise PdfUnavailable(f"No Europe PMC record found for {source}:{ident}")

    record = _select_record(records)
    meta = _metadata_of(record)
    urls = _pdf_urls(record)
    if not urls:
        raise PdfUnavailable(
            "This record has no open-access PDF. It may be paywalled — "
            "use the publisher link to read it.",
            metadata=meta,
        )

    last: Exception | None = None
    for url in urls:
        try:
            pdf = _download_pdf(url)
            logger.info(f"fetched {len(pdf)} bytes from {url}")
            return FetchResult(pdf=pdf, metadata=_metadata_of(record, url))
        except Exception as e:
            last = e
            logger.info(f"pdf attempt failed for {url}: {e}")
    raise PdfUnavailable(
        f"No downloadable PDF among {len(urls)} candidate link(s): {last}", metadata=meta
    )
