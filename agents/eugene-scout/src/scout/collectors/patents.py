"""USPTO Open Data Portal patent collector.

The use case calls for "patent APIs (USPTO/EPO)". This is the USPTO half, reading the
Patent File Wrapper search endpoint on api.uspto.gov.

**Why not Europe PMC's patent index**, which the rest of this codebase already talks
to: it is abandoned. Measured 2026-08-08 — 139,427 patent records published in
2011-2012, and *exactly zero* from 2013 onward. Every query against it returns
decade-old filings no matter how it is sorted or filtered. That is the true root cause
of the "2002 patents under an overnight heading" defect documented in
`lib/atlas/intel.ts`: the bug was never really the unhonoured sort, it was that the
index stops in 2012. No amount of client-side filtering can make a frozen corpus
fresh, so the source was replaced rather than patched.

USPTO ODP is strictly better on every axis that matters here:

  * Fresh — a `hemophilia` query returns applications published within the last month.
  * `sort` is genuinely honoured (verified, unlike Europe PMC's).
  * Lucene range filters work, so the recency window is pushed upstream instead of
    being enforced only after fetching.
  * Applicants are structured, so patents attribute to a company directly rather than
    depending on a name being inferred from an author string.

Requires an API key (`USPTO_API_KEY`), passed as `X-API-KEY`. Field paths verified live
2026-08-08 — see docs/SOURCE_CONTRACTS.md §3.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any

from scout.areas import Area
from scout.collectors.base import BaseCollector, FetchError, http_get_json
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, parse_date
from scout.text import matched_keywords

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.uspto.gov/api/v1/patent/applications/search"

# Publication is the event with BD meaning: a filing is confidential for 18 months, so
# the publication date is when the competitive information actually becomes knowable.
_DATE_FIELD = "applicationMetaData.earliestPublicationDate"


class MissingApiKey(FetchError):
    """No USPTO_API_KEY configured. Reported as a degraded source rather than a crash,
    so a deployment that has not yet been given a key still serves the other three."""


class PatentsCollector(BaseCollector):
    source = SourceId.PATENTS

    def _api_key(self) -> str:
        key = os.environ.get("USPTO_API_KEY", "").strip()
        if not key:
            raise MissingApiKey(
                "USPTO_API_KEY is not set; obtain one free at developer.uspto.gov/apis"
            )
        return key

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        key = self._api_key()
        start = today - dt.timedelta(days=settings.window_days)

        # The keyword clause MUST be parenthesised. Lucene binds AND tighter than OR,
        # so `a OR b OR c AND date:[...]` parses as `a OR b OR (c AND date:[...])` —
        # the date filter would apply to only the last keyword and every other term
        # would return unfiltered history. Local filtering in base.freshest caught the
        # stale rows, but the query was fetching mostly-useless pages to do it.
        #
        # The window is pushed upstream AND enforced locally. That is not redundant:
        # it keeps this collector correct if USPTO ever changes range semantics, which
        # is exactly the assumption Europe PMC violated.
        params = {
            "q": (
                f"({area.patent_query()}) AND "
                f"{_DATE_FIELD}:[{start.isoformat()} TO {today.isoformat()}]"
            ),
            "sort": f"{_DATE_FIELD} desc",
            "limit": str(min(100, max(settings.limit_per_area * 3, 25))),
        }
        try:
            data = http_get_json(
                _ENDPOINT,
                params,
                session=self._session,
                headers={"X-API-KEY": key},
            )
        except FetchError as e:
            # USPTO answers a zero-result query with HTTP 404 and the body
            # "No matching records found, refine your search criteria" rather than an
            # empty 200. Treating that as a failure marked whole areas degraded on
            # nights when there simply were no new filings — which is a normal,
            # frequent outcome for a narrow franchise, not an outage.
            if _is_empty_result(e):
                logger.info(f"uspto: no matching applications for area={area.id}")
                return [], _ENDPOINT
            raise

        wrappers: list[dict[str, Any]] = data.get("patentFileWrapperDataBag") or []

        signals = []
        for wrapper in wrappers:
            signal = self._to_signal(wrapper, area)
            if signal is not None:
                signals.append(signal)
        return signals, _ENDPOINT

    def _to_signal(self, wrapper: dict[str, Any], area: Area) -> RawSignal | None:
        md = wrapper.get("applicationMetaData") or {}
        app_number = str(wrapper.get("applicationNumberText") or "").strip()
        title = str(md.get("inventionTitle") or "").strip()
        if not app_number or not title:
            return None

        pub_number = str(md.get("earliestPublicationNumber") or "").strip()
        published = parse_date(md.get("earliestPublicationDate"))
        filed = parse_date(md.get("filingDate")) or parse_date(md.get("effectiveFilingDate"))

        applicants = [
            str(a.get("applicantNameText") or "").strip()
            for a in (md.get("applicantBag") or [])
            if a.get("applicantNameText")
        ]
        company = str(md.get("firstApplicantName") or "").strip() or (
            applicants[0] if applicants else None
        )

        # CPC codes are the patent world's therapeutic taxonomy and are far more
        # reliable than title text for classification, so they join the keyword
        # haystack alongside the prose.
        cpc = [str(c).strip() for c in (md.get("cpcClassificationBag") or [])]
        inventor = str(md.get("firstInventorName") or "").strip()
        status = str(md.get("applicationStatusDescriptionText") or "").strip()

        summary_parts = [
            company or "",
            f"filed {filed.isoformat()}" if filed else "",
            status,
        ]
        summary = " · ".join(p for p in summary_parts if p)

        return RawSignal(
            source=self.source,
            external_id=pub_number or app_number,
            title=title,
            summary=summary[:600],
            url=_patent_url(pub_number, app_number),
            published=published,
            company_name=company or None,
            # An application's stage is its prosecution status, which is not a
            # development phase. It is deliberately left None so `stage_fit` treats
            # patents as not-applicable rather than scoring them against a trial
            # phase scale they do not belong on.
            stage=None,
            keywords=matched_keywords(area.keywords, title, company or "", " ".join(cpc), inventor),
            payload={
                "application_number": app_number,
                "publication_number": pub_number,
                "publication_date": md.get("earliestPublicationDate"),
                "filing_date": md.get("filingDate"),
                "effective_filing_date": md.get("effectiveFilingDate"),
                "applicants": applicants,
                "first_applicant": company,
                "first_inventor": inventor,
                "status": status,
                "status_code": md.get("applicationStatusCode"),
                "application_type": md.get("applicationTypeLabelName"),
                "cpc_classifications": cpc,
                "uspc_symbol": md.get("uspcSymbolText"),
                "publication_categories": md.get("publicationCategoryBag"),
                "national_stage": md.get("nationalStageIndicator"),
            },
        )


def _is_empty_result(error: FetchError) -> bool:
    """Whether a FetchError is really USPTO's "nothing matched" 404.

    Matched on the status code alone rather than the message text: the phrasing is
    upstream prose that can change, while a 404 from a search endpoint that we know
    exists and are authenticated against means one thing.
    """
    return "HTTP 404" in str(error)


def _patent_url(pub_number: str, app_number: str) -> str:
    """Link to something an analyst can actually open.

    Google Patents renders a publication number directly and needs no session or key,
    which USPTO's own Patent Public Search does not. When there is no publication
    number yet (application filed but not published), fall back to Patent Center,
    which resolves by application number.
    """
    if pub_number:
        return f"https://patents.google.com/patent/{pub_number}/en"
    if app_number:
        return f"https://patentcenter.uspto.gov/applications/{app_number}"
    return "https://ppubs.uspto.gov/pubwebapp/"
