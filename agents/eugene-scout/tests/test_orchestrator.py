"""End-to-end pipeline tests with stubbed collectors and an in-process S3.

The orchestrator is where every other module's guarantees have to actually hold
together, and it was the least covered file in the service. Unit tests proved the
parts; nothing proved the assembly — that staging happens before scoring, that a dead
source degrades one column rather than the run, that a dismissal survives the next
scan, that identity is stable across runs.

Collectors are replaced with deterministic stubs so the whole pipeline runs in
milliseconds with no network. S3 is real (moto), so the key layout, the gzip round
trip and the publish ordering are exercised rather than mocked away.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.collectors.base import BaseCollector
from scout.models import RawSignal, RunStatus, SourceId, SourceReport
from scout.orchestrator import Orchestrator, new_run_id
from scout.storage import key_raw, key_snapshot
from tests.conftest import FROZEN_TODAY


class NoGraph:
    """Entity linkage is optional; these tests are about the pipeline, not the graph."""

    def link(self, terms):  # noqa: D102, ANN001
        return []

    @property
    def available(self) -> bool:
        return False


def _raw(source: SourceId, ext: str, title: str, **kw) -> RawSignal:
    return RawSignal(
        source=source,
        external_id=ext,
        title=title,
        summary=kw.get("summary", "Recombinant factor VIII prophylaxis in hemophilia A."),
        url=kw.get("url", f"https://example.org/{ext}"),
        published=kw.get("published", FROZEN_TODAY - dt.timedelta(days=2)),
        company_name=kw.get("company_name", "Acme Biotherapeutics, Inc."),
        stage=kw.get("stage", "PHASE2"),
        keywords=kw.get("keywords", ("hemophilia", "factor viii")),
        payload=kw.get("payload", {}),
    )


class StubCollector(BaseCollector):
    """Returns a fixed batch, or reports a failure, without any I/O."""

    source = SourceId.TRIALS
    batch: list[RawSignal] = []
    fail: str | None = None

    def __init__(self) -> None:  # noqa: D107 - deliberately skips BaseCollector's session
        pass

    def collect(self, area, settings, today):  # noqa: ANN001
        if self.fail:
            return [], SourceReport(
                source=self.source, area=area.id, ok=False, error=self.fail
            )
        return list(self.batch), SourceReport(
            source=self.source, area=area.id, ok=True,
            fetched=len(self.batch), kept=len(self.batch),
        )


def make_registry(monkeypatch, batches: dict[SourceId, list[RawSignal]],
                  failures: dict[SourceId, str] | None = None):
    """Point the orchestrator's collector factory at stubs."""
    failures = failures or {}

    def build(source: SourceId):
        stub = StubCollector()
        stub.source = source
        stub.batch = batches.get(source, [])
        stub.fail = failures.get(source)
        return stub

    monkeypatch.setattr("scout.orchestrator.build_collector", build)


@pytest.fixture
def orch(store, monkeypatch):
    monkeypatch.setenv("SCOUT_LLM_ENABLED", "false")
    return Orchestrator(store, graph=NoGraph())  # type: ignore[arg-type]


class TestHappyPath:
    def test_a_full_scan_publishes_scored_signals(self, orch, store, monkeypatch):
        make_registry(monkeypatch, {
            SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "Factor VIII trial in hemophilia A")],
            SourceId.LITERATURE: [_raw(SourceId.LITERATURE, "MED:1", "Hemophilia A factor VIII review",
                                       stage=None, company_name=None)],
        })
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        assert run.status is RunStatus.OK
        signals = store.load_signals("hemophilia")
        assert len(signals) == 2
        assert all(0 <= s.score <= 100 for s in signals)
        assert all(s.sources for s in signals)

    def test_companies_are_aggregated_from_signals(self, orch, store, monkeypatch):
        make_registry(monkeypatch, {
            SourceId.TRIALS: [
                _raw(SourceId.TRIALS, "NCT1", "Factor VIII trial one in hemophilia"),
                _raw(SourceId.TRIALS, "NCT2", "Factor VIII trial two in hemophilia"),
            ],
        })
        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        companies = store.load_companies("hemophilia")
        assert len(companies) == 1
        assert companies[0].signal_count == 2

    def test_run_manifest_records_the_audit_trail(self, orch, store, monkeypatch):
        make_registry(monkeypatch, {SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "A hemophilia trial")]})
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        stored = store.load_run(run.run_id)
        assert stored is not None
        assert stored["status"] == "ok"
        assert stored["source_reports"]


class TestStagingBeforeJudgement:
    def test_raw_is_written_for_each_source(self, orch, store, monkeypatch):
        """Staging must capture what upstream said, not what the pipeline concluded."""
        make_registry(monkeypatch, {
            SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "A hemophilia trial")],
            SourceId.EDGAR: [_raw(SourceId.EDGAR, "8K-1", "Acme filed 8-K", stage="8-K")],
        })
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        for source in (SourceId.TRIALS, SourceId.EDGAR):
            assert store.s3.exists(key_raw(run.run_id, "hemophilia", source.value, FROZEN_TODAY))

    def test_records_rejected_by_the_gate_are_still_staged(self, orch, store, monkeypatch):
        """The archive exists to recover from pipeline bugs, so it must hold what was
        fetched — including what the relevance gate later threw away."""
        irrelevant = _raw(SourceId.TRIALS, "NCT9", "An unrelated oncology study",
                          summary="Checkpoint inhibition in solid tumours.", keywords=())
        make_registry(monkeypatch, {SourceId.TRIALS: [irrelevant]})
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        staged = store.load_raw(run.run_id, "hemophilia", SourceId.TRIALS.value, FROZEN_TODAY)
        assert len(staged) == 1
        assert store.load_signals("hemophilia") == []


class TestFailureIsolation:
    def test_a_dead_source_degrades_only_itself(self, orch, store, monkeypatch):
        make_registry(
            monkeypatch,
            {SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "A hemophilia factor VIII trial")]},
            failures={SourceId.LITERATURE: "HTTP 503"},
        )
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        assert run.status is RunStatus.DEGRADED
        assert len(store.load_signals("hemophilia")) == 1  # the healthy source still published
        assert any(not r.ok for r in run.source_reports)

    def test_every_source_failing_still_completes_the_run(self, orch, monkeypatch):
        make_registry(monkeypatch, {}, failures={s: "HTTP 500" for s in SourceId})
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        # Published an empty area rather than crashing: "nothing found" is an answer.
        assert run.status is RunStatus.DEGRADED
        assert run.signals_kept == 0

    def test_no_enabled_areas_fails_loudly(self, orch, monkeypatch):
        make_registry(monkeypatch, {})
        run = orch.run(trigger="test", areas=["not-a-real-area"], today=FROZEN_TODAY)
        assert run.status is RunStatus.FAILED
        assert run.error


class TestIdentityAcrossRuns:
    def _run_twice(self, orch, monkeypatch, second_batch=None):
        batch = [_raw(SourceId.TRIALS, "NCT1", "A hemophilia factor VIII trial")]
        make_registry(monkeypatch, {SourceId.TRIALS: batch})
        first = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        make_registry(monkeypatch, {SourceId.TRIALS: second_batch if second_batch is not None else batch})
        second = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        return first, second

    def test_a_re_seen_signal_is_not_counted_as_new(self, orch, monkeypatch):
        """Otherwise "since you last looked" reports the whole corpus every night."""
        first, second = self._run_twice(orch, monkeypatch)
        assert first.signals_new == 1
        assert second.signals_new == 0
        assert second.signals_updated == 1

    def test_detected_at_and_first_seen_run_are_preserved(self, orch, store, monkeypatch):
        first, second = self._run_twice(orch, monkeypatch)
        signal = store.load_signals("hemophilia")[0]
        assert signal.first_seen_run == first.run_id
        assert signal.last_seen_run == second.run_id

    def test_a_title_edit_does_not_resurface_the_signal(self, orch, monkeypatch):
        edited = [_raw(SourceId.TRIALS, "NCT1", "A hemophilia factor VIII trial (amended)")]
        _, second = self._run_twice(orch, monkeypatch, second_batch=edited)
        assert second.signals_new == 0

    def test_a_dismissal_survives_the_next_scan(self, orch, store, monkeypatch):
        """An analyst's decision must not be silently undone at 02:00."""
        batch = [_raw(SourceId.TRIALS, "NCT1", "A hemophilia factor VIII trial")]
        make_registry(monkeypatch, {SourceId.TRIALS: batch})
        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        signals = store.load_signals("hemophilia")
        signals[0].dismissed = True
        store.publish_area("hemophilia", signals, [], day=FROZEN_TODAY, run_id="manual-patch")

        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        assert store.load_signals("hemophilia")[0].dismissed is True


class TestPipelineSemantics:
    def test_cross_source_corroboration_merges_into_one_signal(self, orch, store, monkeypatch):
        title = "Acme Reports Positive Phase 2 Factor VIII Gene Therapy Results Today"
        make_registry(monkeypatch, {
            SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", title)],
            SourceId.EDGAR: [_raw(SourceId.EDGAR, "8K-1", title, stage="8-K")],
        })
        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        signals = store.load_signals("hemophilia")
        assert len(signals) == 1
        assert len(signals[0].sources) == 2

    def test_academic_sponsors_produce_no_company_row(self, orch, store, monkeypatch):
        make_registry(monkeypatch, {
            SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "A hemophilia trial",
                                   company_name="Stanford University")],
        })
        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        assert store.load_signals("hemophilia")[0].company_name is None
        assert store.load_companies("hemophilia") == []

    def test_snapshot_is_written_alongside_the_live_objects(self, orch, store, monkeypatch):
        """The dated snapshot is the only baseline the 30-day delta has."""
        make_registry(monkeypatch, {SourceId.TRIALS: [_raw(SourceId.TRIALS, "NCT1", "A hemophilia trial")]})
        orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)
        assert store.s3.exists(key_snapshot("hemophilia", FROZEN_TODAY))

    def test_low_confidence_signals_are_flagged_not_dropped(self, orch, store, monkeypatch):
        thin = _raw(SourceId.TRIALS, "NCT1", "A hemophilia study", summary="",
                    company_name=None, keywords=("hemophilia",))
        make_registry(monkeypatch, {SourceId.TRIALS: [thin]})
        run = orch.run(trigger="test", areas=["hemophilia"], today=FROZEN_TODAY)

        signals = store.load_signals("hemophilia")
        assert len(signals) == 1  # present, not suppressed
        assert signals[0].needs_review is True
        assert run.signals_needing_review == 1


class TestRunIds:
    def test_ids_sort_chronologically(self):
        """Lexical order must equal chronological order — `list_run_ids` depends on it."""
        early = new_run_id(dt.datetime(2026, 8, 8, 2, 0, tzinfo=dt.UTC))
        late = new_run_id(dt.datetime(2026, 8, 9, 2, 0, tzinfo=dt.UTC))
        assert early < late
        assert sorted([late, early]) == [early, late]

    def test_ids_are_unique_within_the_same_second(self):
        """REGRESSION: ids were second-precision only, so a cron firing while an
        operator clicked Rescan produced two runs sharing an id — the second silently
        overwrote the first's manifest."""
        same_moment = dt.datetime(2026, 8, 9, 2, 0, tzinfo=dt.UTC)
        ids = {new_run_id(same_moment) for _ in range(200)}
        assert len(ids) == 200
