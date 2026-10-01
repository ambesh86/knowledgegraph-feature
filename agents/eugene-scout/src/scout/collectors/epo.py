"""EPO Open Patent Services (OPS) collector — European and PCT filings.

The use case names "patent APIs (USPTO/EPO)". `patents.py` covers the USPTO half;
this is the EPO half, adding EP and WO filings that a US-only search never sees. For a
BD team evaluating partners headquartered outside the US, that gap is material — a
European biotech often files EP/PCT first and US later, so USPTO alone sees the
opportunity months after a European competitor could.

**Status: implemented, unit-tested, and shipped DISABLED because it is unverified.**

EPO OPS requires an OAuth2 consumer key/secret (free, but registration is tied to a
person at developers.epo.org). Without credentials the endpoint returns 403 and the
response shape cannot be confirmed against a live call. Every other collector in this
service was written against a captured real response and recorded in
docs/SOURCE_CONTRACTS.md; this one is written against EPO's published REST contract
instead, and it is the only source in the system where that is true.

That distinction is deliberate and visible: `SourceSettings.enabled` defaults to false
for this source, and the contracts document marks it unverified. Set `EPO_CONSUMER_KEY`
and `EPO_CONSUMER_SECRET`, enable it in Settings, and the first run will either confirm
the mapping or degrade this one source with a clear error — the same never-raise
contract every other collector obeys.
"""
from __future__ import annotations

import base64
import datetime as dt
import logging
import os
import threading
import time
from typing import Any

from scout.areas import Area
from scout.collectors.base import BaseCollector, FetchError, http_get_json
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, parse_date
from scout.text import matched_keywords

logger = logging.getLogger(__name__)

_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
_SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"

# OPS tokens are short-lived (20 minutes documented). Cached process-wide with a
# safety margin so a scan across five areas mints one token, not five.
_TOKEN_TTL_MARGIN_S = 120
_token_lock = threading.Lock()
_token: dict[str, Any] = {"value": None, "expires_at": 0.0}


class MissingCredentials(FetchError):
    """No EPO OAuth credentials configured. Reported as a degraded source so a
    deployment without them still serves the other four."""


class EpoCollector(BaseCollector):
    source = SourceId.EPO

    # -- auth --------------------------------------------------------------

    def _credentials(self) -> tuple[str, str]:
        key = os.environ.get("EPO_CONSUMER_KEY", "").strip()
        secret = os.environ.get("EPO_CONSUMER_SECRET", "").strip()
        if not key or not secret:
            raise MissingCredentials(
                "EPO_CONSUMER_KEY / EPO_CONSUMER_SECRET are not set; "
                "register free at developers.epo.org"
            )
        return key, secret

    def _access_token(self) -> str:
        """Client-credentials token, cached until shortly before it expires."""
        with _token_lock:
            if _token["value"] and time.monotonic() < _token["expires_at"]:
                return str(_token["value"])

            key, secret = self._credentials()
            basic = base64.b64encode(f"{key}:{secret}".encode()).decode()
            res = self._session.post(
                _AUTH_URL,
                data={"grant_type": "client_credentials"},
                headers={
                    "Authorization": f"Basic {basic}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15,
            )
            if res.status_code != 200:
                raise FetchError(f"{_AUTH_URL} -> HTTP {res.status_code}")
            payload = res.json()
            value = payload.get("access_token")
            if not value:
                raise FetchError("EPO auth response carried no access_token")

            ttl = int(payload.get("expires_in", 1200))
            _token["value"] = value
            _token["expires_at"] = time.monotonic() + max(60, ttl - _TOKEN_TTL_MARGIN_S)
            return str(value)

    # -- fetch -------------------------------------------------------------

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        token = self._access_token()
        start = today - dt.timedelta(days=settings.window_days)

        # CQL, EPO's query language. `ti,ab=` searches title and abstract; `pd within`
        # bounds the publication date. The keyword group is parenthesised for the same
        # precedence reason as the USPTO collector — an unbracketed OR chain would
        # scope the date filter to the final term only.
        terms = " or ".join(f'"{k}"' for k in area.keywords if len(k) > 3)
        cql = f'(ti,ab=({terms})) and pd within "{start:%Y%m%d} {today:%Y%m%d}"'

        data = http_get_json(
            _SEARCH_URL,
            {"q": cql, "Range": f"1-{min(100, max(settings.limit_per_area * 2, 25))}"},
            session=self._session,
            headers={"Authorization": f"Bearer {token}"},
        )

        # OPS wraps everything in an ops:world-patent-data envelope.
        world = data.get("ops:world-patent-data") or {}
        result = (world.get("ops:biblio-search") or {}).get("ops:search-result") or {}
        documents = result.get("exchange-documents") or result.get("ops:publication-reference") or []
        if isinstance(documents, dict):
            documents = [documents]

        signals = []
        for doc in documents:
            signal = self._to_signal(doc, area)
            if signal is not None:
                signals.append(signal)
        return signals, _SEARCH_URL

    def _to_signal(self, doc: dict[str, Any], area: Area) -> RawSignal | None:
        exchange = doc.get("exchange-document") or doc
        if not isinstance(exchange, dict):
            return None

        country = str(exchange.get("@country") or "")
        number = str(exchange.get("@doc-number") or "")
        kind = str(exchange.get("@kind") or "")
        if not number:
            return None
        publication = f"{country}{number}{kind}"

        biblio = exchange.get("bibliographic-data") or {}
        title = _first_text(biblio.get("invention-title"))
        if not title:
            return None

        applicants = _names(biblio, "applicants", "applicant")
        inventors = _names(biblio, "inventors", "inventor")
        published = _publication_date(biblio)

        company = applicants[0] if applicants else None
        classifications = _classifications(biblio)

        return RawSignal(
            source=self.source,
            external_id=f"EPO:{publication}",
            title=title,
            summary=" · ".join(filter(None, [company or "", f"{country} filing"]))[:600],
            url=f"https://worldwide.espacenet.com/patent/search?q=pn%3D{publication}",
            published=published,
            company_name=company,
            # As with USPTO: a patent has no development phase, so `stage_fit` treats
            # it as not-applicable rather than scoring it on a scale it does not sit on.
            stage=None,
            keywords=matched_keywords(
                area.keywords, title, company or "", " ".join(classifications)
            ),
            payload={
                "publication_number": publication,
                "country": country,
                "kind_code": kind,
                "applicants": applicants,
                "inventors": inventors,
                "classifications": classifications,
                "publication_date": published.isoformat() if published else None,
            },
        )


# ---------------------------------------------------------------------------
# OPS response helpers
#
# OPS collapses single-element arrays into bare objects, so every accessor has to
# tolerate both shapes. Reading a field that happens to be a dict as though it were a
# list is the characteristic way this API breaks a naive parser.
# ---------------------------------------------------------------------------


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _first_text(value: Any) -> str:
    for item in _as_list(value):
        if isinstance(item, dict):
            text = item.get("text") or item.get("$")
            if text:
                return str(text).strip()
        elif isinstance(item, str) and item.strip():
            return item.strip()
    return ""


def _names(biblio: dict[str, Any], group: str, member: str) -> list[str]:
    parties = biblio.get("parties") or {}
    container = parties.get(group) or {}
    out: list[str] = []
    for entry in _as_list(container.get(member)):
        if not isinstance(entry, dict):
            continue
        name = entry.get(f"{member}-name") or {}
        text = name.get("name") if isinstance(name, dict) else None
        value = _first_text(text) or _first_text(name)
        if value and value not in out:
            out.append(value)
    return out


def _classifications(biblio: dict[str, Any]) -> list[str]:
    out: list[str] = []
    cpc = (biblio.get("patent-classifications") or {}).get("patent-classification")
    for entry in _as_list(cpc):
        if not isinstance(entry, dict):
            continue
        section = _first_text(entry.get("section"))
        cls = _first_text(entry.get("class"))
        subclass = _first_text(entry.get("subclass"))
        code = f"{section}{cls}{subclass}".strip()
        if code and code not in out:
            out.append(code)
    return out


def _publication_date(biblio: dict[str, Any]) -> dt.date | None:
    reference = biblio.get("publication-reference") or {}
    for doc_id in _as_list(reference.get("document-id")):
        if not isinstance(doc_id, dict):
            continue
        raw = _first_text(doc_id.get("date"))
        if len(raw) == 8 and raw.isdigit():  # OPS uses YYYYMMDD
            return parse_date(f"{raw[:4]}-{raw[4:6]}-{raw[6:]}")
        parsed = parse_date(raw)
        if parsed:
            return parsed
    return None
