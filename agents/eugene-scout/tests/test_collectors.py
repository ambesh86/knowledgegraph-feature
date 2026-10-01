"""Collector tests against recorded upstream responses.

The fixtures are trimmed copies of real responses captured 2026-08-08 and documented
in docs/SOURCE_CONTRACTS.md. Using real payload shapes rather than invented ones is
the point: a hand-written fixture tests that the parser matches the fixture, which is
a tautology. These test that it matches what the API actually sends.

No network. Every collector is driven through a stubbed session.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.collectors import build
from scout.collectors.base import FetchError, freshest, within_window
from scout.collectors.edgar import EdgarCollector, _document_url, _parse_display_name
from scout.collectors.literature import LiteratureCollector
from scout.collectors.patents import MissingApiKey, PatentsCollector
from scout.collectors.trials import TrialsCollector
from scout.config import SourceSettings
from scout.models import SourceId
from tests.conftest import FROZEN_TODAY, make_signal

TRIALS_RESPONSE = {
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT06003387",
                    "briefTitle": "Efficacy and Safety of CSL222 Gene Therapy in Hemophilia B",
                    "organization": {"fullName": "CSL Behring"},
                },
                "statusModule": {
                    "overallStatus": "RECRUITING",
                    "startDateStruct": {"date": "2024-01-30"},
                    "studyFirstPostDateStruct": {"date": "2023-08-22"},
                    "lastUpdatePostDateStruct": {"date": "2026-08-07"},
                },
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {"name": "CSL Behring", "class": "INDUSTRY"}
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "phases": ["PHASE3"],
                    "enrollmentInfo": {"count": 35},
                },
                "conditionsModule": {"conditions": ["Hemophilia B"]},
                "armsInterventionsModule": {
                    "interventions": [{"type": "GENETIC", "name": "CSL222 (AAV5-hFIXco-Padua)"}]
                },
                "descriptionModule": {"briefSummary": "Assess bleeding risk after CSL222."},
            }
        },
        {
            # Academic sponsor: kept as a signal, but must not be attributed to a company.
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT07000001",
                    "briefTitle": "Factor VIII Prophylaxis in Severe Hemophilia A",
                },
                "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-05"}},
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {"name": "Stanford University", "class": "OTHER"}
                },
                "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
                "conditionsModule": {"conditions": ["Hemophilia A"]},
            }
        },
        {
            # Observational: filtered out entirely.
            "protocolSection": {
                "identificationModule": {"nctId": "NCT07000002", "briefTitle": "A Registry"},
                "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-06"}},
                "designModule": {"studyType": "OBSERVATIONAL"},
            }
        },
    ]
}

EPMC_RESPONSE = {
    "hitCount": 57734,
    "resultList": {
        "result": [
            {
                "id": "42563362",
                "source": "MED",
                "pmid": "42563362",
                "doi": "10.1000/x",
                "title": "Quality of Life in People With Haemophilia: A National Framework",
                "authorString": "Smith J, Jones A.",
                "journalTitle": "Haemophilia",
                "pubYear": "2026",
                "firstPublicationDate": "2026-08-06",
                "abstractText": "Emicizumab prophylaxis in haemophilia A improved outcomes.",
                "isOpenAccess": "Y",
                "citedByCount": 0,
            },
            {
                # No PMID: URL must fall back to the Europe PMC article link.
                "id": "PPR123456",
                "source": "PPR",
                "title": "Factor IX variants in gene therapy",
                "authorString": "Doe J.",
                "pubYear": "2026",
                "firstPublicationDate": "2026-08-01",
            },
        ]
    },
}

USPTO_RESPONSE = {
    "count": 476,
    "patentFileWrapperDataBag": [
        {
            "applicationNumberText": "18123456",
            "applicationMetaData": {
                "inventionTitle": "TREATMENT OF HEMOPHILIA A WITH FITUSIRAN",
                "firstApplicantName": "Genzyme Corporation",
                "applicantBag": [{"applicantNameText": "Genzyme Corporation"}],
                "firstInventorName": "Shauna ANDERSSON",
                "earliestPublicationNumber": "US20260185097A1",
                "earliestPublicationDate": "2026-07-02",
                "filingDate": "2026-03-12",
                "effectiveFilingDate": "2026-03-12",
                "applicationStatusDescriptionText": "Docketed New Case - Ready for Examination",
                "cpcClassificationBag": ["A61K  38/37", "C12N  15/113"],
                "uspcSymbolText": "514/44A",
            },
        }
    ],
}

EDGAR_RESPONSE = {
    "hits": {
        "total": {"value": 1784},
        "hits": [
            {
                "_id": "0001628280-24-032815:exhibit-991072424.htm",
                "_source": {
                    "ciks": ["0001001233"],
                    "display_names": ["SANGAMO THERAPEUTICS, INC  (SGMO)  (CIK 0001001233)"],
                    "file_date": "2026-07-24",
                    "form": "8-K",
                    "root_forms": ["8-K"],
                    "adsh": "0001628280-24-032815",
                    "sics": ["2836"],
                    "biz_states": ["CA"],
                },
            },
            {
                # A bank mentioning the term. Non-biotech SIC: must be filtered out.
                "_id": "0000000000-26-000001:doc.htm",
                "_source": {
                    "ciks": ["0000000009"],
                    "display_names": ["BIG BANK CORP  (BBC)  (CIK 0000000009)"],
                    "file_date": "2026-07-20",
                    "form": "10-K",
                    "adsh": "0000000000-26-000001",
                    "sics": ["6022"],
                },
            },
        ],
    }
}


class StubSession:
    """Returns a canned payload, or raises, without touching the network."""

    def __init__(self, payload=None, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params or {}))
        if self.error:
            raise self.error
        return StubResponse(self.payload)


class StubResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


SETTINGS = SourceSettings(enabled=True, window_days=45, limit_per_area=25)


class TestWindowFiltering:
    def test_item_inside_the_window_is_kept(self):
        assert within_window(FROZEN_TODAY - dt.timedelta(days=10), 45, FROZEN_TODAY) is True

    def test_item_outside_the_window_is_dropped(self):
        assert within_window(FROZEN_TODAY - dt.timedelta(days=100), 45, FROZEN_TODAY) is False

    def test_undated_item_is_dropped(self):
        """REGRESSION: admitting undated records is how 2002 patents appeared under a
        heading that said "overnight"."""
        assert within_window(None, 45, FROZEN_TODAY) is False

    def test_future_publication_date_is_dropped(self):
        assert within_window(FROZEN_TODAY + dt.timedelta(days=30), 45, FROZEN_TODAY) is False

    def test_freshest_filters_then_sorts_then_caps(self):
        signals = [
            make_signal(external_id="a", published=FROZEN_TODAY - dt.timedelta(days=1)),
            make_signal(external_id="b", published=FROZEN_TODAY - dt.timedelta(days=100)),
            make_signal(external_id="c", published=FROZEN_TODAY - dt.timedelta(days=5)),
        ]
        kept = freshest(signals, 45, 10, FROZEN_TODAY)
        assert [s.external_id for s in kept] == ["a", "c"]

    def test_freshest_respects_the_limit(self):
        signals = [
            make_signal(external_id=str(i), published=FROZEN_TODAY - dt.timedelta(days=i))
            for i in range(20)
        ]
        assert len(freshest(signals, 45, 5, FROZEN_TODAY)) == 5


class TestTrialsCollector:
    def _collect(self):
        collector = TrialsCollector()
        collector._session = StubSession(TRIALS_RESPONSE)
        return collector.collect(_area(), SETTINGS, FROZEN_TODAY)

    def test_parses_the_verified_field_paths(self):
        signals, report = self._collect()
        assert report.ok is True
        top = next(s for s in signals if s.external_id == "NCT06003387")
        assert top.company_name == "CSL Behring"
        assert top.stage == "PHASE3"
        assert top.published == dt.date(2026, 8, 7)
        assert top.url == "https://clinicaltrials.gov/study/NCT06003387"
        assert top.payload["enrollment"] == 35

    def test_observational_studies_are_excluded(self):
        signals, _ = self._collect()
        assert all(s.external_id != "NCT07000002" for s in signals)

    def test_academic_sponsor_is_not_attributed_to_a_company(self):
        signals, _ = self._collect()
        academic = next(s for s in signals if s.external_id == "NCT07000001")
        assert academic.company_name is None

    def test_keywords_match_conditions_and_interventions(self):
        signals, _ = self._collect()
        top = next(s for s in signals if s.external_id == "NCT06003387")
        assert "hemophilia" in top.keywords


class TestLiteratureCollector:
    def _collect(self):
        collector = LiteratureCollector()
        collector._session = StubSession(EPMC_RESPONSE)
        return collector.collect(_area(), SETTINGS, FROZEN_TODAY)

    def test_british_spelling_still_matches_keywords(self):
        """REGRESSION: this exact record matched zero keywords on the first live run."""
        signals, _ = self._collect()
        paper = next(s for s in signals if s.external_id == "MED:42563362")
        assert "hemophilia" in paper.keywords

    def test_abstract_becomes_the_summary(self):
        signals, _ = self._collect()
        paper = next(s for s in signals if s.external_id == "MED:42563362")
        assert "Emicizumab prophylaxis" in paper.summary

    def test_pubmed_url_when_pmid_present(self):
        signals, _ = self._collect()
        paper = next(s for s in signals if s.external_id == "MED:42563362")
        assert paper.url == "https://pubmed.ncbi.nlm.nih.gov/42563362/"

    def test_falls_back_to_europepmc_url_without_a_pmid(self):
        signals, _ = self._collect()
        preprint = next(s for s in signals if s.external_id == "PPR:PPR123456")
        assert preprint.url == "https://europepmc.org/article/PPR/PPR123456"

    def test_date_window_is_pushed_upstream(self):
        """Filtering server-side means the fetched page is entirely in-window, so
        over-fetching buys depth instead of being spent discarding stale rows."""
        collector = LiteratureCollector()
        session = StubSession(EPMC_RESPONSE)
        collector._session = session
        collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        query = session.calls[0][1]["query"]
        assert "FIRST_PDATE:[2026-06-24 TO 2026-08-08]" in query

    def test_requests_abstracts(self):
        collector = LiteratureCollector()
        session = StubSession(EPMC_RESPONSE)
        collector._session = session
        collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert session.calls[0][1]["resultType"] == "core"


class TestPatentsCollector:
    def test_parses_uspto_metadata(self, monkeypatch):
        monkeypatch.setenv("USPTO_API_KEY", "test-key")
        collector = PatentsCollector()
        collector._session = StubSession(USPTO_RESPONSE)
        signals, report = collector.collect(
            _area(), SourceSettings(window_days=540, limit_per_area=15), FROZEN_TODAY
        )
        assert report.ok is True
        patent = signals[0]
        assert patent.company_name == "Genzyme Corporation"
        assert patent.published == dt.date(2026, 7, 2)
        assert patent.url == "https://patents.google.com/patent/US20260185097A1/en"
        assert patent.stage is None  # prosecution status is not a development phase

    def test_missing_key_degrades_the_source_not_the_run(self, monkeypatch):
        """A deployment without a USPTO key must still serve the other three sources."""
        monkeypatch.delenv("USPTO_API_KEY", raising=False)
        collector = PatentsCollector()
        collector._session = StubSession(USPTO_RESPONSE)
        signals, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is False
        assert "USPTO_API_KEY" in report.error

    def test_keyword_clause_is_parenthesised(self, monkeypatch):
        """REGRESSION: Lucene binds AND tighter than OR, so `a OR b AND date:[...]`
        applies the date filter to `b` only. Without the parentheses every keyword but
        the last returned unfiltered history."""
        monkeypatch.setenv("USPTO_API_KEY", "test-key")
        collector = PatentsCollector()
        session = StubSession(USPTO_RESPONSE)
        collector._session = session
        collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        query = session.calls[0][1]["q"]
        assert query.startswith("(")
        assert ") AND applicationMetaData.earliestPublicationDate:[" in query

    def test_zero_results_404_is_not_a_failure(self, monkeypatch):
        """REGRESSION: USPTO answers a zero-result query with HTTP 404, not an empty
        200. Treating that as an error marked whole areas degraded on nights when
        there were simply no new filings — a normal outcome for a narrow franchise."""
        monkeypatch.setenv("USPTO_API_KEY", "test-key")
        collector = PatentsCollector()
        collector._session = StubSession(
            error=FetchError("https://api.uspto.gov/... -> HTTP 404")
        )
        signals, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is True

    def test_other_http_errors_still_degrade_the_source(self, monkeypatch):
        """A 500 or a 429 is a real failure and must still be reported as one."""
        monkeypatch.setenv("USPTO_API_KEY", "test-key")
        collector = PatentsCollector()
        collector._session = StubSession(error=FetchError("... -> HTTP 503"))
        signals, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is False

    def test_api_key_is_sent_as_a_header_not_a_query_param(self, monkeypatch):
        """Keeps the key out of request logs and out of the persisted request_url."""
        monkeypatch.setenv("USPTO_API_KEY", "secret-key")
        collector = PatentsCollector()
        session = StubSession(USPTO_RESPONSE)
        collector._session = session
        _, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert "secret-key" not in str(session.calls[0][1])
        assert "secret-key" not in (report.request_url or "")


class TestEdgarCollector:
    def _collect(self):
        collector = EdgarCollector()
        collector._session = StubSession(EDGAR_RESPONSE)
        return collector.collect(
            _area(), SourceSettings(window_days=90, limit_per_area=20), FROZEN_TODAY
        )

    def test_parses_filer_and_form(self):
        signals, report = self._collect()
        assert report.ok is True
        filing = signals[0]
        assert filing.company_name == "SANGAMO THERAPEUTICS, INC"
        assert filing.stage == "8-K"
        assert filing.payload["ticker"] == "SGMO"

    def test_non_biotech_sic_is_filtered_out(self):
        """Without the SIC filter a bank's risk disclosure mentioning "hemophilia"
        ranks alongside a biotech's trial readout."""
        signals, _ = self._collect()
        assert all("BANK" not in (s.company_name or "").upper() for s in signals)

    @pytest.mark.parametrize(
        ("display", "expected"),
        [
            ("SANGAMO THERAPEUTICS, INC  (SGMO)  (CIK 0001001233)",
             ("SANGAMO THERAPEUTICS, INC", "SGMO", "0001001233")),
            ("PRIVATE BIOTECH LLC  (CIK 0000123456)",
             ("PRIVATE BIOTECH LLC", None, "0000123456")),
        ],
    )
    def test_display_name_parsing(self, display, expected):
        assert _parse_display_name(display) == expected

    def test_document_url_construction(self):
        url = _document_url("0001001233", "0001628280-24-032815", "0001628280-24-032815:ex.htm")
        assert url == "https://www.sec.gov/Archives/edgar/data/1001233/000162828024032815/ex.htm"

    def test_document_url_falls_back_when_incomplete(self):
        """A link to the right company's filing list beats a 404 that looks precise."""
        assert "browse-edgar" in _document_url("0001001233", "", "")


class TestNeverRaiseContract:
    def test_upstream_failure_becomes_a_degraded_report(self):
        collector = TrialsCollector()
        collector._session = StubSession(error=FetchError("upstream exploded"))
        signals, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is False
        assert "upstream exploded" in report.error

    def test_malformed_payload_becomes_a_degraded_report(self):
        collector = TrialsCollector()
        collector._session = StubSession({"unexpected": "shape"})
        signals, report = collector.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is True  # a valid response with zero studies is not a failure

    def test_a_failed_report_must_carry_a_reason(self):
        from scout.models import SourceReport

        with pytest.raises(ValueError, match="must carry an error"):
            SourceReport(source=SourceId.TRIALS, area="x", ok=False)

    def test_every_source_has_a_registered_collector(self):
        for source in SourceId:
            assert build(source) is not None


def _area():
    from tests.conftest import Area  # noqa: PLC0415

    return Area(
        {
            "id": "hemophilia",
            "label": "Hemophilia A & B",
            "enabled": True,
            "queries": {
                "literature": "hemophilia",
                "trials_condition": "hemophilia A",
                "trials_intervention": "factor VIII",
            },
            "keywords": ["hemophilia", "factor viii", "factor ix", "emicizumab", "gene therapy"],
        }
    )


EPO_RESPONSE = {
    "ops:world-patent-data": {
        "ops:biblio-search": {
            "ops:search-result": {
                "exchange-documents": [
                    {
                        "exchange-document": {
                            "@country": "EP",
                            "@doc-number": "4123456",
                            "@kind": "A1",
                            "bibliographic-data": {
                                "invention-title": [
                                    {"text": "FACTOR VIII FUSION PROTEIN FORMULATIONS"}
                                ],
                                "publication-reference": {
                                    "document-id": [{"date": {"text": "20260715"}}]
                                },
                                "parties": {
                                    "applicants": {
                                        "applicant": [
                                            {"applicant-name": {"name": {"text": "CSL Behring GmbH"}}}
                                        ]
                                    },
                                    "inventors": {
                                        "inventor": [
                                            {"inventor-name": {"name": {"text": "MUELLER, Anna"}}}
                                        ]
                                    },
                                },
                                "patent-classifications": {
                                    "patent-classification": [
                                        {
                                            "section": {"text": "A"},
                                            "class": {"text": "61"},
                                            "subclass": {"text": "K"},
                                        }
                                    ]
                                },
                            },
                        }
                    }
                ]
            }
        }
    }
}


class TestEpoCollector:
    """EPO OPS is the only source written against a published contract rather than a
    captured live response, because it needs an OAuth key to call at all. It ships
    disabled for that reason; these tests pin the mapping so enabling it later is a
    config change and not a debugging session."""

    def _collector(self, monkeypatch, payload=EPO_RESPONSE):
        from scout.collectors.epo import EpoCollector

        monkeypatch.setenv("EPO_CONSUMER_KEY", "key")
        monkeypatch.setenv("EPO_CONSUMER_SECRET", "secret")
        c = EpoCollector()
        c._session = StubSession(payload)
        # Bypass the OAuth round trip; token acquisition is tested separately.
        c._access_token = lambda: "test-token"  # type: ignore[method-assign]
        return c

    def test_maps_an_ops_document(self, monkeypatch):
        c = self._collector(monkeypatch)
        signals, report = c.collect(
            _area(), SourceSettings(window_days=540, limit_per_area=15), FROZEN_TODAY
        )
        assert report.ok is True
        s = signals[0]
        assert s.external_id == "EPO:EP4123456A1"
        assert s.company_name == "CSL Behring GmbH"
        assert s.published == dt.date(2026, 7, 15)
        assert s.stage is None  # a patent has no development phase
        assert "espacenet.com" in s.url

    def test_ops_collapses_single_element_arrays(self, monkeypatch):
        """OPS returns a bare object where a list is expected when there is one
        element — reading it as a list is the characteristic way this API breaks a
        naive parser."""
        collapsed = {
            "ops:world-patent-data": {
                "ops:biblio-search": {
                    "ops:search-result": {
                        "exchange-documents": {
                            "exchange-document": {
                                "@country": "WO",
                                "@doc-number": "2026123456",
                                "@kind": "A1",
                                "bibliographic-data": {
                                    "invention-title": {"text": "HEMOPHILIA GENE THERAPY"},
                                    "publication-reference": {
                                        "document-id": {"date": {"text": "20260601"}}
                                    },
                                },
                            }
                        }
                    }
                }
            }
        }
        c = self._collector(monkeypatch, collapsed)
        signals, report = c.collect(
            _area(), SourceSettings(window_days=540, limit_per_area=15), FROZEN_TODAY
        )
        assert report.ok is True
        assert signals[0].external_id == "EPO:WO2026123456A1"

    def test_missing_credentials_degrade_the_source_only(self, monkeypatch):
        from scout.collectors.epo import EpoCollector

        monkeypatch.delenv("EPO_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("EPO_CONSUMER_SECRET", raising=False)
        c = EpoCollector()
        c._session = StubSession(EPO_RESPONSE)
        signals, report = c.collect(_area(), SETTINGS, FROZEN_TODAY)
        assert signals == []
        assert report.ok is False
        assert "EPO_CONSUMER_KEY" in report.error

    def test_keyword_group_is_parenthesised_in_the_cql(self, monkeypatch):
        """Same precedence trap as the USPTO collector: an unbracketed OR chain would
        scope the date filter to the final term only."""
        c = self._collector(monkeypatch)
        c.collect(_area(), SourceSettings(window_days=540, limit_per_area=15), FROZEN_TODAY)
        q = c._session.calls[0][1]["q"]
        assert q.startswith("(ti,ab=(")
        assert "pd within" in q

    def test_epo_is_disabled_by_default(self):
        """Unverified against a live response, so it must not be on by default."""
        from scout.config import ScanConfig
        from scout.models import SourceId

        assert ScanConfig().is_enabled(SourceId.EPO) is False

    def test_epo_maps_to_the_patent_signal_type(self):
        from scout.models import SourceId
        from scout.scoring import signal_type_for

        assert signal_type_for(SourceId.EPO).value == "Patent"
