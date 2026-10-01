"""HTTP surface tests.

The UI is the only consumer of this API, so these tests are really a contract between
this service and `agents/eugene-agent-ui-next`. Anything asserted here — field names,
status codes, the shape of an empty result — is something a Radar page load depends on.

The app is exercised through `TestClient`, which runs the real lifespan, so the
scheduler wiring and the startup index load are covered rather than stubbed.
"""
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from scout.models import Priority, Signal, SignalSource, SignalType, SourceId
from tests.conftest import FROZEN_NOW, FROZEN_TODAY


def _signal(
    signal_id: str,
    *,
    score: float = 80.0,
    priority: Priority = Priority.HIGH,
    signal_type: SignalType = SignalType.TRIAL,
    company: str | None = "Acme Inc",
    area: str = "hemophilia",
    published: dt.date | None = None,
    dismissed: bool = False,
) -> Signal:
    return Signal(
        id=signal_id,
        area=area,
        type=signal_type,
        title=f"Signal {signal_id} about factor VIII",
        summary="A summary mentioning emicizumab.",
        rationale="Because it matched.",
        score=score,
        priority=priority,
        company_name=company,
        company_id=f"co-{company.lower().replace(' ', '')}" if company else None,
        published=published or FROZEN_TODAY,
        detected_at=FROZEN_NOW,
        first_seen_run="run-1",
        last_seen_run="run-1",
        dismissed=dismissed,
        sources=[
            SignalSource(
                source=SourceId.TRIALS,
                external_id=signal_id,
                url=f"https://clinicaltrials.gov/study/{signal_id}",
            )
        ],
    )


@pytest.fixture
def client(store, monkeypatch):
    """A TestClient wired to the moto-backed store rather than real S3."""
    from scout import api

    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(api.index, "_store", store)
    monkeypatch.setattr(api.orchestrator, "store", store)
    # `api.index` is a module-level singleton, so areas loaded by an earlier test
    # would otherwise leak into one that is meant to start cold. Reset it both before
    # and after: a "cold start" test is worthless if the index is warm.
    monkeypatch.setattr(api.index, "_areas", {})
    with TestClient(api.app) as c:
        yield c
    api.index._areas = {}


@pytest.fixture
def seeded(store, client):
    signals = [
        _signal("sig-00000001", score=90, priority=Priority.HIGH),
        _signal("sig-00000002", score=60, priority=Priority.MED, signal_type=SignalType.PATENT),
        _signal("sig-00000003", score=30, priority=Priority.WATCH,
                signal_type=SignalType.PUBLICATION, company=None),
        _signal("sig-00000004", score=70, priority=Priority.MED, dismissed=True),
    ]
    from scout.companies import aggregate

    companies = aggregate(signals, now=FROZEN_NOW)
    store.publish_area("hemophilia", signals, companies, day=FROZEN_TODAY, run_id="run-1")
    client.post("/index/refresh")
    return client


class TestHealth:
    def test_health_is_ok_when_s3_is_reachable(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["s3"]["reachable"] is True

    def test_status_reports_the_schedule(self, client):
        body = client.get("/status").json()
        assert body["schedule"]["timezone"] == "UTC"
        assert "daily_hour" in body["schedule"]


class TestColdStart:
    def test_signals_is_an_empty_list_not_an_error(self, client):
        """Before the first scan the Radar must render an empty state, not a 500."""
        body = client.get("/signals").json()
        assert body["signals"] == []
        assert body["total"] == 0

    def test_companies_is_empty_not_an_error(self, client):
        assert client.get("/companies").json()["companies"] == []

    def test_digest_for_an_unknown_area_is_404(self, client):
        assert client.get("/digest?area=nope").status_code == 404


class TestSignalQueries:
    def test_returns_signals_ranked_by_score(self, seeded):
        body = seeded.get("/signals").json()
        scores = [s["score"] for s in body["signals"]]
        assert scores == sorted(scores, reverse=True)

    def test_dismissed_are_hidden_by_default(self, seeded):
        ids = {s["id"] for s in seeded.get("/signals").json()["signals"]}
        assert "sig-00000004" not in ids

    def test_dismissed_can_be_included(self, seeded):
        ids = {s["id"] for s in seeded.get("/signals?include_dismissed=true").json()["signals"]}
        assert "sig-00000004" in ids

    def test_priority_filter(self, seeded):
        body = seeded.get("/signals?priority=high").json()
        assert all(s["priority"] == "high" for s in body["signals"])

    def test_type_filter(self, seeded):
        body = seeded.get("/signals?type=Patent").json()
        assert all(s["type"] == "Patent" for s in body["signals"])

    def test_counts_survive_the_priority_filter(self, seeded):
        """Otherwise the filter chips read "0 medium" the moment you select high,
        which is both useless and confusing."""
        body = seeded.get("/signals?priority=high").json()
        assert body["counts"]["med"] > 0

    def test_unknown_filter_value_is_ignored_not_rejected(self, seeded):
        """A stale bookmark should show the unfiltered Radar, not a 400."""
        assert seeded.get("/signals?type=Nonsense").status_code == 200

    def test_free_text_search(self, seeded):
        assert seeded.get("/signals?q=emicizumab").json()["total"] > 0
        assert seeded.get("/signals?q=zzzznotpresent").json()["total"] == 0

    def test_company_filter(self, seeded):
        body = seeded.get("/signals?company_id=co-acmeinc").json()
        assert all(s["company_id"] == "co-acmeinc" for s in body["signals"])

    def test_pagination(self, seeded):
        first = seeded.get("/signals?limit=1&offset=0").json()
        second = seeded.get("/signals?limit=1&offset=1").json()
        assert len(first["signals"]) == 1
        assert first["signals"][0]["id"] != second["signals"][0]["id"]
        assert first["total"] == second["total"]

    def test_invalid_since_is_a_400(self, seeded):
        assert seeded.get("/signals?since=not-a-date").status_code == 400

    def test_every_signal_carries_at_least_one_clickable_source(self, seeded):
        """The Radar renders these as links; a signal with no URL is not evidence."""
        for s in seeded.get("/signals").json()["signals"]:
            assert s["sources"]
            assert s["sources"][0]["url"].startswith("https://")

    def test_single_signal_lookup(self, seeded):
        assert seeded.get("/signals/sig-00000001").json()["id"] == "sig-00000001"

    def test_missing_signal_is_404(self, seeded):
        assert seeded.get("/signals/nope").status_code == 404


class TestDismissal:
    def test_dismissal_persists_to_the_curated_store(self, seeded, store):
        """An in-memory-only dismissal would silently reappear at the 02:00 scan."""
        assert seeded.patch("/signals/sig-00000001", json={"dismissed": True}).status_code == 200
        stored = {s.id: s for s in store.load_signals("hemophilia")}
        assert stored["sig-00000001"].dismissed is True

    def test_dismissal_removes_it_from_the_default_query(self, seeded):
        seeded.patch("/signals/sig-00000001", json={"dismissed": True})
        ids = {s["id"] for s in seeded.get("/signals").json()["signals"]}
        assert "sig-00000001" not in ids

    def test_dismissal_can_be_undone(self, seeded):
        seeded.patch("/signals/sig-00000001", json={"dismissed": True})
        seeded.patch("/signals/sig-00000001", json={"dismissed": False})
        ids = {s["id"] for s in seeded.get("/signals").json()["signals"]}
        assert "sig-00000001" in ids

    def test_dismissing_an_unknown_signal_is_404(self, seeded):
        assert seeded.patch("/signals/nope", json={"dismissed": True}).status_code == 404


class TestCompaniesAndStats:
    def test_companies_are_ranked(self, seeded):
        body = seeded.get("/companies").json()
        scores = [c["score"] for c in body["companies"]]
        assert scores == sorted(scores, reverse=True)

    def test_stats_report_priority_counts(self, seeded):
        body = seeded.get("/stats").json()
        assert body["priority_counts"]["high"] >= 1

    def test_new_since_counts_recent_detections(self, seeded):
        past = (FROZEN_NOW - dt.timedelta(days=1)).isoformat()
        assert seeded.get(f"/stats?since={past}").json()["new_signals"] >= 1

    def test_new_since_is_zero_for_a_future_timestamp(self, seeded):
        future = (FROZEN_NOW + dt.timedelta(days=365)).isoformat()
        assert seeded.get(f"/stats?since={future}").json()["new_signals"] == 0

    def test_ui_area_maps_onto_scan_areas(self, seeded):
        """A user whose profile says "hematology" must see the hemophilia area."""
        assert seeded.get("/signals?ui_area=hematology").json()["total"] > 0


class TestConfigEndpoint:
    def test_get_returns_defaults(self, client):
        body = client.get("/config").json()
        assert body["version"] == 1
        assert "weights" in body

    def test_put_persists_and_bumps_the_version(self, client):
        response = client.put("/config", json={"notify_min_score": 90.0, "updated_by": "tester"})
        assert response.status_code == 200
        assert response.json()["notify_min_score"] == 90.0
        assert response.json()["version"] == 2

    def test_invalid_config_is_rejected_at_the_boundary(self, client):
        """A bad Settings save must 400, not be written and then silently ignored."""
        response = client.put("/config", json={"thresholds": {"high": 10.0, "med": 50.0}})
        assert response.status_code == 400

    def test_unknown_source_is_rejected(self, client):
        """A typo would otherwise silently disable a source with no error anywhere."""
        response = client.put("/config", json={"sources": {"not_a_source": {"enabled": True}}})
        assert response.status_code == 400

    def test_client_cannot_rewind_the_version(self, client):
        client.put("/config", json={"notify_min_score": 80.0})
        body = client.put("/config", json={"version": 1, "notify_min_score": 81.0}).json()
        assert body["version"] == 3


class TestDigestEndpoint:
    def test_json_digest_is_built_on_demand(self, seeded):
        body = seeded.get("/digest?area=hemophilia").json()
        assert body["area"] == "hemophilia"
        assert "companies" in body

    def test_markdown_rendering(self, seeded):
        response = seeded.get("/digest?area=hemophilia&format=markdown")
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert response.text.startswith("# Partnership Briefing")

    def test_short_briefing_says_so_rather_than_padding(self, seeded):
        """Padding to eight with companies the system does not rate teaches readers to
        distrust the ranking."""
        body = seeded.get("/digest?area=hemophilia").json()
        assert body["below_target"] is True

    def test_every_entry_carries_a_next_action(self, seeded):
        body = seeded.get("/digest?area=hemophilia").json()
        for entry in body["companies"]:
            assert entry["next_action"]
            assert entry["sources_consulted"]

    def test_invalid_date_is_a_400(self, seeded):
        assert seeded.get("/digest?area=hemophilia&date=nope").status_code == 400


class TestRunsAndAreas:
    def test_runs_listing(self, seeded):
        assert "runs" in seeded.get("/runs").json()

    def test_areas_listing_includes_the_taxonomy(self, client):
        body = client.get("/areas").json()
        assert any(a["id"] == "hemophilia" for a in body["areas"])


class TestFreshness:
    """The "as of" indicator's data.

    Three clocks are reported separately on purpose: the platform's date, when the
    scanner last looked, and how recent the newest record each source returned is.
    The third is extracted from the data and is the only one that actually indicates
    staleness — a panel can truthfully say "scanned 20 minutes ago" while its newest
    paper is three weeks old.
    """

    def test_reports_todays_date(self, seeded):
        body = seeded.get("/freshness").json()
        assert body["today"] == dt.datetime.now(dt.UTC).date().isoformat()

    def test_per_source_dates_come_from_the_records(self, seeded):
        body = seeded.get("/freshness").json()
        assert body["sources"]
        for s in body["sources"]:
            assert s["latest_published"] == FROZEN_TODAY.isoformat()
            assert s["signal_count"] >= 1

    def test_reports_the_newest_record_across_sources(self, seeded):
        body = seeded.get("/freshness").json()
        assert body["newest_signal_date"] == FROZEN_TODAY.isoformat()

    def test_reports_the_last_scan_separately_from_record_dates(self, seeded):
        """Conflating "when we looked" with "how recent the data is" is the specific
        confusion this endpoint exists to prevent."""
        body = seeded.get("/freshness").json()
        assert "last_scan" in body
        assert "newest_signal_date" in body

    def test_next_scan_is_in_the_future(self, seeded):
        body = seeded.get("/freshness").json()
        nxt = dt.datetime.fromisoformat(body["next_scan_at"])
        assert nxt > dt.datetime.now(dt.UTC)

    def test_dismissed_signals_do_not_affect_currency(self, seeded):
        """A dismissed signal is hidden from the Radar, so counting it as the newest
        record would claim currency the visible corpus does not have."""
        before = seeded.get("/freshness").json()["signal_count"]
        rows = seeded.get("/signals?limit=1").json()["signals"]
        seeded.patch(f"/signals/{rows[0]['id']}", json={"dismissed": True})
        assert seeded.get("/freshness").json()["signal_count"] == before - 1

    def test_cold_start_still_reports_a_date(self, client):
        """Today's date never depends on a scan having happened."""
        body = client.get("/freshness").json()
        assert body["today"]
        assert body["sources"] == []
