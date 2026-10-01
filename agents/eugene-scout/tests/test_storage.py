"""S3 storage and repository tests, against an in-process S3 (moto).

Deliberately not mocked at the `Storage` boundary. The key layout, the gzip round
trip, the JSONL encoding and the cold-start behaviour are exactly the parts most
likely to break silently, and a mock of `Storage` would test none of them.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.config import ScanConfig, ScoringWeights
from scout.models import (
    CompanyScore,
    Priority,
    RunStatus,
    ScanRun,
    Signal,
    SignalSource,
    SignalType,
    SourceId,
)
from scout.storage import NotFound, Storage, key_curated_signals, key_raw, key_snapshot
from tests.conftest import BUCKET, FROZEN_NOW, FROZEN_TODAY, make_signal


def _curated(signal_id: str = "sig-00000001", score: float = 80.0, area: str = "hemophilia") -> Signal:
    return Signal(
        id=signal_id,
        area=area,
        type=SignalType.TRIAL,
        title="A Phase 2 Study of Factor VIII",
        summary="Summary",
        score=score,
        priority=Priority.HIGH if score >= 75 else Priority.MED,
        published=FROZEN_TODAY,
        detected_at=FROZEN_NOW,
        first_seen_run="run-1",
        last_seen_run="run-1",
        sources=[
            SignalSource(
                source=SourceId.TRIALS,
                external_id="NCT1",
                url="https://clinicaltrials.gov/study/NCT1",
            )
        ],
    )


class TestPrimitives:
    def test_json_round_trip(self, storage: Storage):
        storage.put_json("test/a.json", {"x": 1, "when": FROZEN_TODAY})
        assert storage.get_json("test/a.json") == {"x": 1, "when": "2026-08-08"}

    def test_jsonl_gz_round_trip(self, storage: Storage):
        rows = [{"i": i, "name": f"row-{i}"} for i in range(500)]
        _, count = storage.put_jsonl_gz("test/rows.jsonl.gz", rows)
        assert count == 500
        assert list(storage.get_jsonl_gz("test/rows.jsonl.gz")) == rows

    def test_gzip_output_is_byte_stable(self, storage: Storage):
        """mtime=0 in the gzip header — without it identical input produces different
        bytes each run and no test could assert on stored content."""
        rows = [{"a": 1}]
        storage.put_jsonl_gz("test/x1.jsonl.gz", rows)
        first = storage.get_bytes("test/x1.jsonl.gz")
        storage.put_jsonl_gz("test/x2.jsonl.gz", rows)
        assert storage.get_bytes("test/x2.jsonl.gz") == first

    def test_missing_key_raises_notfound_not_a_generic_error(self, storage: Storage):
        """Cold start must be distinguishable from an outage: one renders an empty
        Radar, the other an error banner."""
        with pytest.raises(NotFound):
            storage.get_json("nope/missing.json")

    def test_get_json_or_returns_default_on_cold_start(self, storage: Storage):
        assert storage.get_json_or("nope/missing.json", {"empty": True}) == {"empty": True}

    def test_jsonl_or_empty_on_cold_start(self, storage: Storage):
        assert storage.get_jsonl_gz_or_empty("nope/missing.jsonl.gz") == []

    def test_health_reports_reachability(self, storage: Storage):
        assert storage.health() is True

    def test_unserialisable_type_is_rejected_loudly(self, storage: Storage):
        with pytest.raises(TypeError):
            storage.put_json("test/bad.json", {"fn": object()})


class TestKeyLayout:
    def test_raw_key_is_hive_partitioned(self):
        key = key_raw("run-1", "hemophilia", "clinicaltrials", dt.date(2026, 8, 8))
        assert key == (
            "raw/dt=2026-08-08/run=run-1/area=hemophilia/"
            "source=clinicaltrials/records.jsonl.gz"
        )

    def test_curated_and_snapshot_keys_are_distinct(self):
        """Overwriting the snapshot with the live object would destroy the only
        baseline the 30-day delta has."""
        assert key_curated_signals("hemophilia") != key_snapshot("hemophilia", FROZEN_TODAY)


class TestConfigPersistence:
    def test_cold_start_returns_defaults(self, store):
        assert store.load_config().version == 1

    def test_round_trip(self, store):
        config = ScanConfig(weights=ScoringWeights(area_fit=0.9))
        store.save_config(config)
        assert store.load_config().weights.area_fit == pytest.approx(0.9)

    def test_corrupt_config_falls_back_rather_than_breaking_the_scanner(self, store):
        """A bad Settings save must not take the whole scanner offline until someone
        hand-edits an S3 object."""
        store.s3.save_config_raw({"weights": {"area_fit": "not-a-number"}})
        assert store.load_config().version == 1

    def test_bumped_increments_version(self, store):
        first = store.save_config(ScanConfig())
        second = store.save_config(first.bumped("tester"))
        assert second.version == first.version + 1
        assert second.updated_by == "tester"


class TestStagingTier:
    def test_raw_is_written_verbatim(self, store):
        signals = [make_signal(external_id=f"NCT{i}") for i in range(3)]
        store.stage_raw("run-1", "hemophilia", "clinicaltrials", FROZEN_TODAY, signals)
        rows = store.load_raw("run-1", "hemophilia", "clinicaltrials", FROZEN_TODAY)
        assert len(rows) == 3
        assert {r["external_id"] for r in rows} == {"NCT0", "NCT1", "NCT2"}

    def test_empty_batch_writes_nothing(self, store):
        """An object with zero rows is pure cost; its absence says the same thing."""
        assert store.stage_raw("run-1", "hemophilia", "clinicaltrials", FROZEN_TODAY, []) is None

    def test_payload_survives_the_round_trip(self, store):
        """The raw tier exists so a scoring change can be replayed. That only works
        if the upstream payload is preserved exactly."""
        signal = make_signal(payload={"phases": ["PHASE2"], "enrollment": 35, "nested": {"a": [1, 2]}})
        store.stage_raw("run-1", "hemophilia", "clinicaltrials", FROZEN_TODAY, [signal])
        rows = store.load_raw("run-1", "hemophilia", "clinicaltrials", FROZEN_TODAY)
        assert rows[0]["payload"] == {"phases": ["PHASE2"], "enrollment": 35, "nested": {"a": [1, 2]}}


class TestCuratedTier:
    def test_publish_then_load(self, store):
        signals = [_curated(f"sig-{i:08d}", score=60 + i) for i in range(5)]
        store.publish_area("hemophilia", signals, [], day=FROZEN_TODAY, run_id="run-1")
        assert len(store.load_signals("hemophilia")) == 5

    def test_publish_writes_the_snapshot_too(self, store):
        store.publish_area("hemophilia", [_curated()], [], day=FROZEN_TODAY, run_id="run-1")
        assert store.s3.exists(key_snapshot("hemophilia", FROZEN_TODAY))

    def test_index_carries_counts_and_rows(self, store):
        signals = [_curated("sig-00000001", 90.0), _curated("sig-00000002", 60.0)]
        index = store.publish_area("hemophilia", signals, [], day=FROZEN_TODAY, run_id="run-1")
        assert index["signal_count"] == 2
        assert index["priority_counts"]["high"] == 1
        assert index["priority_counts"]["med"] == 1
        assert len(index["signals"]) == 2

    def test_area_manifest_is_maintained(self, store):
        store.publish_area("hemophilia", [_curated()], [], day=FROZEN_TODAY, run_id="run-1")
        store.publish_area(
            "immunoglobulin",
            [_curated(area="immunoglobulin")],
            [],
            day=FROZEN_TODAY,
            run_id="run-1",
        )
        assert set(store.known_areas()) == {"hemophilia", "immunoglobulin"}

    def test_malformed_row_costs_one_signal_not_the_panel(self, store):
        store.publish_area("hemophilia", [_curated()], [], day=FROZEN_TODAY, run_id="run-1")
        good = store.s3.get_jsonl_gz_or_empty(key_curated_signals("hemophilia"))
        store.s3.put_jsonl_gz(
            key_curated_signals("hemophilia"),
            good + [{"id": "broken", "not": "a valid signal"}],
        )
        assert len(store.load_signals("hemophilia")) == 1

    def test_cold_start_area_is_empty_not_an_error(self, store):
        assert store.load_signals("never-scanned") == []
        assert store.load_index("never-scanned") is None


class TestDeltaBaseline:
    def test_no_baseline_returns_empty(self, store):
        assert store.baseline_company_scores("hemophilia", FROZEN_TODAY) == {}

    def test_baseline_found_from_a_dated_snapshot(self, store):
        thirty_days_ago = FROZEN_TODAY - dt.timedelta(days=30)
        signal = _curated(score=70.0)
        signal.company_name = "Acme Inc"
        signal.company_id = "co-acme"
        store.s3.put_jsonl_gz(
            key_snapshot("hemophilia", thirty_days_ago), [signal.model_dump(mode="json")]
        )
        baseline = store.baseline_company_scores("hemophilia", FROZEN_TODAY)
        assert baseline.get("co-acme") == pytest.approx(70.0)

    def test_baseline_search_tolerates_a_missing_day(self, store):
        """Daily snapshots are best-effort — a redeploy or outage skips one, and the
        delta must not silently vanish because of it."""
        near = FROZEN_TODAY - dt.timedelta(days=33)
        signal = _curated(score=65.0)
        signal.company_name = "Acme Inc"
        signal.company_id = "co-acme"
        store.s3.put_jsonl_gz(key_snapshot("hemophilia", near), [signal.model_dump(mode="json")])
        assert store.baseline_company_scores("hemophilia", FROZEN_TODAY).get("co-acme") == 65.0


class TestRunManifests:
    def _run(self, run_id: str, status: RunStatus = RunStatus.OK) -> ScanRun:
        return ScanRun(
            run_id=run_id,
            trigger="manual",
            status=status,
            started_at=FROZEN_NOW,
            finished_at=FROZEN_NOW + dt.timedelta(seconds=5),
            areas=["hemophilia"],
            signals_kept=10,
        )

    def test_run_round_trip(self, store):
        store.save_run(self._run("20260808T120000Z"))
        assert store.load_run("20260808T120000Z")["status"] == "ok"

    def test_latest_run_is_tracked(self, store):
        store.save_run(self._run("20260808T120000Z"))
        assert store.latest_run()["run_id"] == "20260808T120000Z"

    def test_recent_runs_are_newest_first(self, store):
        for run_id in ("20260806T120000Z", "20260808T120000Z", "20260807T120000Z"):
            store.save_run(self._run(run_id))
        ids = [r["run_id"] for r in store.recent_runs(10)]
        assert ids == sorted(ids, reverse=True)

    def test_duration_is_computed(self):
        assert self._run("x").duration_ms == 5000

    def test_unfinished_run_has_zero_duration(self):
        run = ScanRun(
            run_id="x", trigger="cron", status=RunStatus.RUNNING, started_at=FROZEN_NOW
        )
        assert run.duration_ms == 0
