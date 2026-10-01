"""Europe PMC literature collector (SRC:MED).

Europe PMC rather than PubMed directly, for the same reason the ingestion pipeline
chose it (`ingestion/src/pipeline/orchestrator.py`): it indexes PubMed and more, and
exposes per-record identifiers we can turn into a working link for every hit.

Field paths verified live 2026-08-08 — docs/SOURCE_CONTRACTS.md §2.

⚠️ The `sort=P_PDATE_D desc` parameter is accepted and ignored. Measured that day: a
57,734-hit query returned `2026-06-11` as its first result, two months stale. The sort
is still sent (it costs nothing and helps when honoured) but correctness rests
entirely on the local date filter in `base.freshest`.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from scout.areas import Area
from scout.collectors.base import BaseCollector, http_get_json
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, clean_text, parse_date
from scout.text import matched_keywords

_ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class LiteratureCollector(BaseCollector):
    source = SourceId.LITERATURE
    _src_filter = "SRC:MED"
    _record_kind = "paper"

    def _query(self, area: Area) -> str:
        return area.literature_query or " OR ".join(area.keywords)

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        # The window is pushed upstream as a FIRST_PDATE range. Verified 2026-08-08:
        # this filter IS honoured (a July-August 2026 range returned 127 hits, all in
        # range) even though `sort` is not. Filtering server-side also means the page
        # we fetch is entirely in-window, so over-fetching actually buys depth rather
        # than being consumed by stale records we then discard.
        start = today - dt.timedelta(days=settings.window_days)
        date_clause = f"(FIRST_PDATE:[{start.isoformat()} TO {today.isoformat()}])"
        params = {
            "query": f"({self._query(area)}) AND {self._src_filter} AND {date_clause}",
            "format": "json",
            "pageSize": str(min(200, max(settings.limit_per_area * 5, 25))),
            "sort": "P_PDATE_D desc",
            # `core` rather than `lite` to get abstractText. Without the abstract the
            # only text available for keyword matching is the title, author list and
            # journal name — measured on a live run, that matched zero area keywords
            # on most papers and pushed the entire literature source to the bottom of
            # the ranking regardless of relevance.
            "resultType": "core",
        }
        data = http_get_json(_ENDPOINT, params, session=self._session)
        hits: list[dict[str, Any]] = ((data.get("resultList") or {}).get("result")) or []

        signals = []
        for hit in hits:
            signal = self._to_signal(hit, area)
            if signal is not None:
                signals.append(signal)
        return signals, _ENDPOINT

    def _to_signal(self, hit: dict[str, Any], area: Area) -> RawSignal | None:
        record_id = str(hit.get("id") or "").strip()
        title = str(hit.get("title") or "").strip()
        if not record_id or not title:
            return None

        src = str(hit.get("source") or "MED")
        pmid = str(hit.get("pmid") or "").strip()
        # Prefer the PubMed link an analyst will recognise; fall back to Europe PMC's
        # canonical article URL, which exists for every record including those with
        # no PMID at all.
        url = (
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if pmid
            else f"https://europepmc.org/article/{src}/{record_id}"
        )

        # firstPublicationDate is the real publication date; pubYear is a bare year and
        # only used when the full date is absent (parse_date floors it to Jan 1, which
        # makes the recency factor treat it as the oldest it could be).
        published = parse_date(hit.get("firstPublicationDate")) or parse_date(hit.get("pubYear"))

        authors = str(hit.get("authorString") or "")
        journal = str(hit.get("journalTitle") or src)
        abstract = clean_text(hit.get("abstractText"))

        # The abstract is by far the richest matching surface — it is where the
        # indication, the mechanism and the modality are all actually named. Matching
        # is spelling-normalised (text.matched_keywords) because a live run showed
        # British-spelled titles like "Quality of Life in People With Haemophilia"
        # matching none of the hemophilia keywords at all.
        keywords = matched_keywords(area.keywords, title, abstract, journal, authors)

        # Prefer the abstract for the analyst-facing summary; fall back to the
        # bibliographic line when a record has none (common for editorials).
        summary = abstract or " · ".join(filter(None, [authors[:200], journal]))

        return RawSignal(
            source=self.source,
            external_id=f"{src}:{record_id}",
            title=title,
            summary=summary[:600],
            url=url,
            published=published,
            company_name=None,  # attribution comes from enrich.py, not the author list
            stage=None,
            keywords=keywords,
            payload={
                "record_id": record_id,
                "source_db": src,
                "pmid": pmid or None,
                "pmcid": hit.get("pmcid"),
                "doi": hit.get("doi"),
                "journal": journal,
                "authors": authors,
                "pub_year": hit.get("pubYear"),
                "first_publication_date": hit.get("firstPublicationDate"),
                "is_open_access": hit.get("isOpenAccess"),
                "cited_by_count": hit.get("citedByCount"),
                "has_abstract": bool(abstract),
                "kind": self._record_kind,
            },
        )
