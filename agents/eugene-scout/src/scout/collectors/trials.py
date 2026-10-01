"""ClinicalTrials.gov API v2 collector.

Trials are the highest-value source for this use case: a Phase I/II study registered
by a company we do not already track is exactly the "before it becomes widely known"
signal the BD team is asking for, and the registry carries the sponsor, the phase and
the intervention in structured form rather than prose.

Every field path below appears verbatim in docs/SOURCE_CONTRACTS.md §1 against a live
response captured 2026-08-08.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from scout.areas import Area
from scout.collectors.base import BaseCollector, http_get_json
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, parse_date
from scout.text import matched_keywords

_ENDPOINT = "https://clinicaltrials.gov/api/v2/studies"

# Registry-only records that are not investigational activity. An observational
# registry opening is not a partnership signal, and including them buried the
# interventional trials that are.
_WANTED_STUDY_TYPES = frozenset({"INTERVENTIONAL", "EXPANDED_ACCESS"})


class TrialsCollector(BaseCollector):
    source = SourceId.TRIALS

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        params = {
            "query.term": area.trials_query(),
            # Over-fetch. The window filter runs after this call, so requesting
            # exactly `limit` would leave us short whenever recent records are
            # interleaved with older ones — which they are, sort or no sort.
            "pageSize": str(min(200, max(settings.limit_per_area * 5, 25))),
            "sort": "LastUpdatePostDate:desc",
        }
        data = http_get_json(_ENDPOINT, params, session=self._session)
        studies: list[dict[str, Any]] = data.get("studies") or []

        signals: list[RawSignal] = []
        for study in studies:
            signal = self._to_signal(study, area)
            if signal is not None:
                signals.append(signal)
        return signals, _ENDPOINT

    def _to_signal(self, study: dict[str, Any], area: Area) -> RawSignal | None:
        ps = study.get("protocolSection") or {}
        ident = ps.get("identificationModule") or {}
        status = ps.get("statusModule") or {}
        design = ps.get("designModule") or {}
        sponsors = ps.get("sponsorCollaboratorsModule") or {}
        conditions = ps.get("conditionsModule") or {}
        arms = ps.get("armsInterventionsModule") or {}
        desc = ps.get("descriptionModule") or {}

        nct = str(ident.get("nctId") or "").strip()
        title = str(ident.get("briefTitle") or "").strip()
        if not nct or not title:
            # Both are mandatory in the registry; a record missing either is
            # malformed and there is nothing useful to show an analyst.
            return None

        if (design.get("studyType") or "INTERVENTIONAL") not in _WANTED_STUDY_TYPES:
            return None

        phases = [str(p) for p in (design.get("phases") or [])]
        # "PHASE1, PHASE2" is a real registry value for seamless designs. The earlier
        # phase is the one that carries the partnership signal, so it wins.
        stage = phases[0] if phases else "NA"

        lead = (sponsors.get("leadSponsor") or {}).get("name")
        sponsor_class = (sponsors.get("leadSponsor") or {}).get("class")
        # Academic and government sponsors are kept as signals but carry no company
        # attribution — attributing a university trial to a "partner company" would
        # populate the watchlist with institutions nobody can do a deal with.
        company = str(lead).strip() if lead and sponsor_class == "INDUSTRY" else None

        interventions = [
            str(i.get("name") or "").strip()
            for i in (arms.get("interventions") or [])
            if i.get("name")
        ]
        condition_list = [str(c) for c in (conditions.get("conditions") or [])]

        summary = str(desc.get("briefSummary") or "")
        if not summary:
            summary = " · ".join(filter(None, [", ".join(condition_list), ", ".join(interventions)]))

        published = parse_date((status.get("lastUpdatePostDateStruct") or {}).get("date"))

        return RawSignal(
            source=self.source,
            external_id=nct,
            title=title,
            summary=summary[:600],
            url=f"https://clinicaltrials.gov/study/{nct}",
            published=published,
            company_name=company,
            stage=stage,
            keywords=matched_keywords(
                area.keywords, title, summary, *condition_list, *interventions
            ),
            payload={
                "nct_id": nct,
                "overall_status": status.get("overallStatus"),
                "phases": phases,
                "study_type": design.get("studyType"),
                "lead_sponsor": lead,
                "lead_sponsor_class": sponsor_class,
                "conditions": condition_list,
                "interventions": interventions,
                "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
                "start_date": (status.get("startDateStruct") or {}).get("date"),
                "first_posted": (status.get("studyFirstPostDateStruct") or {}).get("date"),
                "last_update_posted": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
            },
        )
