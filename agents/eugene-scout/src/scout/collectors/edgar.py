"""SEC EDGAR full-text search collector.

This is the corporate-disclosure leg of the PDF's source list, and the only one that
names a *company* directly rather than leaving attribution to inference. An 8-K
mentioning a target indication is a material event; an S-1 is a company going public,
which is the financing moment the use case is explicitly hunting for.

Endpoint and response shape verified live 2026-08-08 (docs/SOURCE_CONTRACTS.md §4).
Unlike Europe PMC, EDGAR's date range **is** honoured, so the window is pushed
upstream as `startdt`/`enddt` — but `base.freshest` still filters locally, because a
collector that trusts an upstream filter it cannot verify is a collector waiting to
regress.

SEC requires a contact-bearing User-Agent and asks for <=10 req/s. Both are handled in
`base.py` (`cfg.user_agent()` and the `efts.sec.gov` rate limiter).
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from scout.areas import Area
from scout.collectors.base import BaseCollector, http_get_json
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, parse_date
from scout.text import matched_keywords

_ENDPOINT = "https://efts.sec.gov/LATEST/search-index"

# Forms worth surfacing to a BD team, and nothing else. Periodic reports (10-K/10-Q)
# are excluded: they mention every indication a company touches, every quarter, which
# floods the Radar with restatements of things it already knows.
_FORMS = "8-K,S-1,S-1/A,424B4,SC 13D,DEF 14A"

# "SANGAMO THERAPEUTICS, INC  (SGMO)  (CIK 0001001233)" — ticker is absent for private
# and foreign filers, so it is optional and the pattern degrades to name-only.
_DISPLAY_NAME = re.compile(
    r"^(?P<name>.+?)\s{2,}(?:\((?P<ticker>[A-Z.\-]{1,6})\)\s{2,})?\(CIK (?P<cik>\d+)\)$"
)

# SIC codes for the industries a biotech partner actually lives in. EDGAR full-text
# search matches any filing containing the phrase, which without this filter means a
# bank's risk disclosure mentioning "hemophilia" ranks alongside a biotech's trial
# readout.
_BIOTECH_SICS = frozenset({
    "2836",  # Biological Products (except diagnostic substances)
    "8731",  # Commercial Physical & Biological Research
    "2834",  # Pharmaceutical Preparations
    "2835",  # In Vitro & In Vivo Diagnostic Substances
    "8000",  # Health Services
})


class EdgarCollector(BaseCollector):
    source = SourceId.EDGAR

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        start = today - dt.timedelta(days=settings.window_days)
        params = {
            "q": area.edgar_query(),
            "forms": _FORMS,
            "startdt": start.isoformat(),
            "enddt": today.isoformat(),
        }
        data = http_get_json(_ENDPOINT, params, session=self._session)
        hits: list[dict[str, Any]] = ((data.get("hits") or {}).get("hits")) or []

        signals = []
        for hit in hits:
            signal = self._to_signal(hit, area)
            if signal is not None:
                signals.append(signal)
        return signals, _ENDPOINT

    def _to_signal(self, hit: dict[str, Any], area: Area) -> RawSignal | None:
        src = hit.get("_source") or {}
        doc_id = str(hit.get("_id") or "").strip()
        if not doc_id:
            return None

        sics = [str(s) for s in (src.get("sics") or [])]
        if sics and not (_BIOTECH_SICS & set(sics)):
            return None

        display = [str(d) for d in (src.get("display_names") or [])]
        name, ticker, cik = _parse_display_name(display[0] if display else "")
        if not name:
            # Every EDGAR filing has a filer. No parseable name means the record is
            # malformed, and a corporate signal with no company is not a signal.
            return None

        form = str(src.get("form") or (src.get("root_forms") or [""])[0] or "")
        filed = parse_date(src.get("file_date"))
        adsh = str(src.get("adsh") or "")
        cik = cik or (str((src.get("ciks") or [""])[0]) or "")

        title = f"{name} filed {form}" if form else f"{name} — SEC filing"
        summary = (
            f"{form} filed {filed.isoformat() if filed else 'recently'} by {name}"
            f"{f' ({ticker})' if ticker else ''}, matching {area.label}."
        )

        return RawSignal(
            source=self.source,
            external_id=doc_id,
            title=title,
            summary=summary,
            url=_document_url(cik, adsh, doc_id),
            published=filed,
            company_name=name,
            stage=form or None,
            # EDGAR full-text search does not return the document body, only metadata.
            # Claiming a keyword matched when we never saw the text would be a
            # fabricated citation, so the match is recorded as the query that found it.
            keywords=matched_keywords(area.keywords, name, area.label),
            payload={
                "doc_id": doc_id,
                "accession": adsh,
                "cik": cik,
                "ticker": ticker,
                "company": name,
                "form": form,
                "root_forms": src.get("root_forms"),
                "file_date": src.get("file_date"),
                "period_ending": src.get("period_ending"),
                "sics": sics,
                "biz_states": src.get("biz_states"),
                "matched_query": area.edgar_query(),
            },
        )


def _parse_display_name(display: str) -> tuple[str | None, str | None, str | None]:
    m = _DISPLAY_NAME.match(display.strip())
    if not m:
        # Some filers carry no CIK suffix at all. Take the whole string as the name
        # rather than dropping an otherwise-valid filing.
        cleaned = display.strip()
        return (cleaned or None), None, None
    return m.group("name").strip(), m.group("ticker"), m.group("cik")


def _document_url(cik: str, adsh: str, doc_id: str) -> str:
    """Build a link to the filed document.

    `_id` is "<accession>:<filename>"; the Archives path wants the accession with its
    dashes stripped and the CIK without leading zeros. When either is missing we fall
    back to the filing index, which is always reachable — a link to the right company's
    filing list beats a 404 that looks precise.
    """
    filename = doc_id.split(":", 1)[1] if ":" in doc_id else ""
    cik_int = cik.lstrip("0") if cik else ""
    accession = adsh.replace("-", "")
    if cik_int and accession and filename:
        return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{filename}"
    if cik_int and accession:
        return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/"
    if cik_int:
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_int}&type=&dateb=&owner=include&count=40"
    return "https://www.sec.gov/edgar/search/"
