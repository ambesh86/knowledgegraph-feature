"""Load, volume and adversarial-input tests.

Two questions are being answered here, and neither is "is it fast":

  1. **Does the design hold at scale?** The whole architecture rests on the claim that
     the corpus is small enough to filter in memory. That claim deserves a test, not
     an assumption — and if it ever stops holding, this is where it will fail first.

  2. **Does it survive hostile input?** Public APIs return unicode, enormous strings,
     null bytes and duplicate ids. None of that should be able to crash a scan or
     poison a ranking.

Marked `stress` so the fast suite can skip them: `pytest -m "not stress"`.
Still hermetic — no network, no real S3.
"""
from __future__ import annotations

import datetime as dt
import time

import pytest

from scout.companies import aggregate
from scout.dedupe import dedupe_identity, group_corroborated
from scout.index import SignalIndex
from scout.models import (
    Priority,
    RawSignal,
    Signal,
    SignalSource,
    SignalType,
    SourceId,
    clean_text,
)
from scout.scoring import score
from scout.text import matched_keywords, normalize_company
from tests.conftest import FROZEN_NOW, FROZEN_TODAY, make_signal

pytestmark = pytest.mark.stress


def _bulk_signals(count: int, area: str = "hemophilia") -> list[Signal]:
    return [
        Signal(
            id=f"sig-{i:012d}",
            area=area,
            type=[SignalType.TRIAL, SignalType.PATENT, SignalType.PUBLICATION][i % 3],
            title=f"Signal {i} concerning factor VIII and hemophilia therapy",
            summary="A summary mentioning emicizumab and gene therapy approaches.",
            score=float(i % 101),
            priority=[Priority.HIGH, Priority.MED, Priority.WATCH][i % 3],
            company_name=f"Company {i % 200} Inc",
            company_id=f"co-{i % 200:04d}",
            published=FROZEN_TODAY - dt.timedelta(days=i % 40),
            detected_at=FROZEN_NOW,
            first_seen_run="run-1",
            last_seen_run="run-1",
            sources=[
                SignalSource(
                    source=SourceId.TRIALS,
                    external_id=f"NCT{i:08d}",
                    url=f"https://clinicaltrials.gov/study/NCT{i:08d}",
                )
            ],
        )
        for i in range(count)
    ]


class TestQueryScale:
    """The in-memory index is the deliberate alternative to a database. These tests
    define the scale at which that trade is still sound."""

    @pytest.mark.parametrize("count", [1_000, 10_000, 50_000])
    def test_query_latency_stays_sub_second(self, store, count):
        store.publish_area(
            "hemophilia", _bulk_signals(count), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])

        started = time.perf_counter()
        rows, total, counts = index.query_signals(priority="high", limit=100)
        elapsed = time.perf_counter() - started

        assert total > 0
        assert len(rows) <= 100
        assert sum(counts.values()) == count
        # Generous by design: this is a regression guard against an accidental O(n²),
        # not a benchmark. At 50k the real measurement is tens of milliseconds.
        assert elapsed < 1.0, f"query over {count} signals took {elapsed:.3f}s"

    def test_filter_combination_narrows_correctly_at_scale(self, store):
        store.publish_area(
            "hemophilia", _bulk_signals(10_000), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])
        _, total, _ = index.query_signals(
            priority="high", signal_type="Trial", since=FROZEN_TODAY - dt.timedelta(days=5)
        )
        _, unfiltered, _ = index.query_signals()
        assert 0 < total < unfiltered

    def test_ranking_is_correct_at_scale(self, store):
        store.publish_area(
            "hemophilia", _bulk_signals(10_000), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])
        rows, _, _ = index.query_signals(limit=500)
        scores = [r["score"] for r in rows]
        assert scores == sorted(scores, reverse=True)

    def test_pagination_never_repeats_or_skips(self, store):
        store.publish_area(
            "hemophilia", _bulk_signals(1_000), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])
        seen: list[str] = []
        for offset in range(0, 500, 100):
            rows, _, _ = index.query_signals(limit=100, offset=offset)
            seen.extend(r["id"] for r in rows)
        assert len(seen) == len(set(seen)) == 500


class TestPipelineScale:
    def test_dedupe_is_not_quadratic(self):
        """Identity dedup runs over every fetched record on every scan."""
        signals = [make_signal(external_id=f"NCT{i}") for i in range(20_000)]
        started = time.perf_counter()
        result = dedupe_identity(signals + signals)
        elapsed = time.perf_counter() - started
        assert len(result) == 20_000
        assert elapsed < 2.0, f"dedupe of 40k records took {elapsed:.3f}s"

    def test_cross_source_grouping_stays_tractable(self):
        """Grouping is O(n²) within a month bucket. The bucketing is what keeps a
        realistic run affordable, and this is the test that proves it."""
        signals = [
            make_signal(
                external_id=f"NCT{i}",
                title=f"Distinct study number {i} of factor VIII therapy in patients",
                published=FROZEN_TODAY - dt.timedelta(days=i % 60),
            )
            for i in range(3_000)
        ]
        started = time.perf_counter()
        groups = group_corroborated(signals)
        elapsed = time.perf_counter() - started
        assert len(groups) == 3_000  # all distinct
        assert elapsed < 10.0, f"grouping 3k records took {elapsed:.3f}s"

    def test_scoring_throughput(self, area, config):
        signals = [make_signal(external_id=f"NCT{i}") for i in range(10_000)]
        started = time.perf_counter()
        for signal in signals:
            score(signal, area, config, today=FROZEN_TODAY)
        elapsed = time.perf_counter() - started
        assert elapsed < 10.0, f"scoring 10k signals took {elapsed:.3f}s"

    def test_company_aggregation_at_scale(self):
        rows = aggregate(_bulk_signals(20_000), now=FROZEN_NOW)
        assert len(rows) == 200
        assert all(0 <= r.score <= 100 for r in rows)
        assert [r.score for r in rows] == sorted((r.score for r in rows), reverse=True)


class TestStorageVolume:
    def test_large_curated_object_round_trips(self, store):
        signals = _bulk_signals(20_000)
        store.publish_area("hemophilia", signals, [], day=FROZEN_TODAY, run_id="run-1")
        assert len(store.load_signals("hemophilia")) == 20_000

    def test_compression_is_worth_having(self, storage):
        """Signals are highly repetitive text; if gzip ever stopped helping, the raw
        tier's storage cost assumptions would need revisiting."""
        rows = [s.model_dump(mode="json") for s in _bulk_signals(5_000)]
        storage.put_jsonl_gz("test/bulk.jsonl.gz", rows)
        import json

        raw_size = len(json.dumps(rows, default=str).encode())
        stored_size = len(storage.get_bytes("test/bulk.jsonl.gz"))
        assert stored_size < raw_size / 4


class TestAdversarialInput:
    @pytest.mark.parametrize(
        "title",
        [
            "A" * 50_000,
            "Ünïcödé — hémophilie · 血友病 · гемофилия",
            "Title with <script>alert('xss')</script> markup",
            "Tabs\tand\nnewlines\r\neverywhere",
            "Emoji 🧬🩸 in a trial title",
            "Nulls \x00 and controls \x01\x02",
        ],
    )
    def test_hostile_titles_do_not_crash_the_pipeline(self, title, area, config):
        signal = make_signal(title=title)
        result = score(signal, area, config, today=FROZEN_TODAY)
        assert 0 <= result.score <= 100

    def test_markup_is_stripped_from_titles(self):
        assert "<script>" not in clean_text("Title <script>alert(1)</script> here")

    @pytest.mark.parametrize(
        "name",
        ["", "   ", "\x00", "A" * 5_000, "Ünïcödé Pharma GmbH", "!!!", "Inc.", "The The"],
    )
    def test_company_normalisation_never_raises(self, name):
        assert isinstance(normalize_company(name), str)

    def test_keyword_matching_handles_enormous_haystacks(self):
        haystack = ("filler text " * 100_000) + "hemophilia"
        assert matched_keywords(("hemophilia",), haystack) == ("hemophilia",)

    def test_duplicate_external_ids_collapse_rather_than_duplicating(self):
        signals = [make_signal(external_id="SAME") for _ in range(1_000)]
        assert len(dedupe_identity(signals)) == 1

    def test_extreme_dates_are_handled(self, area, config):
        for published in (dt.date(1900, 1, 1), dt.date(2099, 12, 31), None):
            signal = make_signal(published=published)
            result = score(signal, area, config, today=FROZEN_TODAY)
            assert 0 <= result.score <= 100

    def test_url_scheme_is_validated_at_the_boundary(self):
        """A signal is rendered into an <a href>; a javascript: URL must never get
        that far."""
        with pytest.raises(ValueError, match="must be http"):
            RawSignal(
                source=SourceId.TRIALS,
                external_id="x",
                title="t",
                url="javascript:alert(1)",
            )

    def test_empty_title_is_rejected(self):
        with pytest.raises(ValueError):
            RawSignal(source=SourceId.TRIALS, external_id="x", title="")


class TestIndexConcurrencySafety:
    def test_readers_never_see_a_partial_refresh(self, store):
        """The index is swapped in atomically, so a refresh that fails partway must
        leave the previous generation serving rather than an empty one."""
        store.publish_area(
            "hemophilia", _bulk_signals(500), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])
        before, _, _ = index.query_signals(limit=10)

        index.refresh(["never-scanned-area"])  # yields nothing
        after, total, _ = index.query_signals(limit=10)

        assert total == 500
        assert [r["id"] for r in before] == [r["id"] for r in after]

    def test_concurrent_reads_during_refresh_are_consistent(self, store):
        import threading

        store.publish_area(
            "hemophilia", _bulk_signals(2_000), [], day=FROZEN_TODAY, run_id="run-1"
        )
        index = SignalIndex(store)
        index.refresh(["hemophilia"])

        errors: list[Exception] = []
        totals: list[int] = []

        def reader():
            try:
                for _ in range(50):
                    _, total, _ = index.query_signals(limit=10)
                    totals.append(total)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        def refresher():
            try:
                for _ in range(5):
                    index.refresh(["hemophilia"])
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads.append(threading.Thread(target=refresher))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert set(totals) == {2_000}
