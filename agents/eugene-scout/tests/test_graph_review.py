"""Knowledge-graph linkage and human-in-the-loop confidence flagging.

Two behaviours here are design decisions rather than mechanics, and both are asserted
explicitly because a future change could silently reverse either:

  * Graph membership must NOT influence the score. The BD team is hunting assets it
    does not already track, so ranking on "we already know this" would put the
    familiar above the novel and defeat the point of the use case.
  * Low-confidence signals must be flagged and still shown. Suppressing them makes a
    cleaner Radar and destroys the analyst's trust in everything that remains.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.config import ScanConfig, Thresholds
from scout.graph import _MAX_CONSECUTIVE_FAILURES as MAX_CONSECUTIVE_FAILURES
from scout.graph import GraphClient, clear_cache
from scout.models import GraphEntity, RationaleKind, ReviewReason
from scout.review import BORDERLINE_MARGIN, assess, summarise
from scout.scoring import score
from tests.conftest import FROZEN_TODAY, make_signal


class StubResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class StubSession:
    """Counts calls so caching can be asserted, and can be told to fail."""

    def __init__(self, payload=None, error: Exception | None = None):
        self.payload = payload if payload is not None else {"results": [], "count": 0}
        self.error = error
        self.calls: list[str] = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if self.error:
            raise self.error
        return StubResponse(self.payload)


class FlakySession(StubSession):
    """A graph that is up but occasionally slow — the real observed failure mode.

    `fail_first` fails the opening N calls; `fail_every` fails every Nth call. Both
    model transient latency rather than an outage, which is the distinction the
    consecutive-failure threshold is there to draw.
    """

    def __init__(self, payload=None, *, fail_first=0, fail_every=0, error=None):
        super().__init__(payload)
        self.fail_first = fail_first
        self.fail_every = fail_every
        self.error = error or TimeoutError("slow")
        self._n = 0

    def get(self, url, headers=None, timeout=None):
        self._n += 1
        self.calls.append(url)
        if self._n <= self.fail_first:
            raise self.error
        if self.fail_every and self._n % self.fail_every == 0:
            raise self.error
        return StubResponse(self.payload)


FOUND = {"results": [{"id": "DB13923", "value": "Emicizumab"}], "count": 1}


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestGraphLinkage:
    def test_resolves_a_term_to_a_node(self):
        client = GraphClient(base_url="http://ws", session=StubSession(FOUND))
        entities = client.lookup("emicizumab")
        assert entities == [
            GraphEntity(id="DB13923", value="Emicizumab", matched_term="emicizumab")
        ]

    def test_unknown_term_yields_nothing(self):
        client = GraphClient(base_url="http://ws", session=StubSession())
        assert client.lookup("a-drug-that-does-not-exist") == []

    def test_results_are_cached_across_signals(self):
        """The same terms recur across hundreds of signals in one scan; without a
        cache that is hundreds of identical round trips."""
        session = StubSession(FOUND)
        client = GraphClient(base_url="http://ws", session=session)
        for _ in range(50):
            client.lookup("emicizumab")
        assert len(session.calls) == 1

    def test_very_short_terms_are_not_looked_up(self):
        session = StubSession(FOUND)
        client = GraphClient(base_url="http://ws", session=session)
        assert client.lookup("ig") == []
        assert session.calls == []

    def test_link_dedupes_across_terms(self):
        client = GraphClient(base_url="http://ws", session=StubSession(FOUND))
        entities = client.link(["emicizumab", "Emicizumab", "emicizumab "])
        assert len(entities) == 1

    def test_link_respects_a_per_signal_budget(self):
        """Entity linkage is an annotation; it must not dominate the scan runtime."""
        session = StubSession(FOUND)
        client = GraphClient(base_url="http://ws", session=session)
        client.link([f"distinct-term-{i}" for i in range(50)])
        assert len(session.calls) <= 6

    def test_graph_outage_costs_a_few_requests_not_hundreds(self):
        """A sustained outage latches linkage off rather than paying the timeout on
        every remaining term."""
        session = StubSession(error=ConnectionError("graph down"))
        client = GraphClient(base_url="http://ws", session=session)
        for i in range(20):
            assert client.lookup(f"term-{i}") == []
        assert len(session.calls) == MAX_CONSECUTIVE_FAILURES
        assert client.available is False

    def test_one_slow_lookup_does_not_cost_the_whole_run(self):
        """THE regression this threshold exists for.

        `/node/find` is heavy-tailed, not binary: a median around 20ms with an
        occasional multi-second outlier. Latching linkage off after a single timeout
        meant one slow term stripped the graph annotations from every signal in the
        run — while the service was up and answering everything else in milliseconds.
        """
        session = FlakySession(FOUND, fail_first=1, error=TimeoutError("slow once"))
        client = GraphClient(base_url="http://ws", session=session)

        assert client.lookup("emicizumab") == []          # the unlucky one
        assert client.available is True                    # ...and we carry on

        assert client.lookup("efanesoctocog") != []
        assert client.lookup("concizumab") != []

    def test_the_failure_counter_is_consecutive_not_cumulative(self):
        """Occasional slowness spread across a long run must never accumulate into a
        shutdown; only an unbroken run of failures means the graph is actually down."""
        session = FlakySession(FOUND, fail_every=2, error=TimeoutError("intermittent"))
        client = GraphClient(base_url="http://ws", session=session)

        for i in range(40):
            client.lookup(f"term-{i}")

        assert client.available is True, (
            "alternating failures are a flaky service, not a dead one"
        )

    def test_a_failed_lookup_is_never_cached(self):
        """A timeout means 'we do not know', which is not what an empty result means.

        The cache is module-level and outlives the run, so caching [] on failure would
        record 'the graph has no such node' and serve that wrong answer to every later
        run in the process — long after the graph recovered.
        """
        session = FlakySession(FOUND, fail_first=1, error=TimeoutError("slow once"))
        client = GraphClient(base_url="http://ws", session=session)

        assert client.lookup("emicizumab") == []
        assert client.lookup("emicizumab") == [
            GraphEntity(id="DB13923", value="Emicizumab", matched_term="emicizumab")
        ], "the retry must reach the graph, not a cached failure"

    def test_terms_seen_during_an_outage_are_not_cached_as_absent(self):
        """Once linkage is off, lookups must return without poisoning the cache — the
        same term has to resolve normally in the next run."""
        session = StubSession(error=ConnectionError("graph down"))
        client = GraphClient(base_url="http://ws", session=session)
        for i in range(10):
            client.lookup(f"term-{i}")
        assert client.available is False

        recovered = GraphClient(base_url="http://ws", session=StubSession(FOUND))
        assert recovered.lookup("term-0") != [], (
            "a term seen while the graph was down must not be remembered as absent"
        )

    def test_malformed_response_degrades_silently(self):
        client = GraphClient(base_url="http://ws", session=StubSession({"unexpected": True}))
        assert client.lookup("emicizumab") == []

    def test_non_200_is_not_an_error(self):
        session = StubSession(FOUND)
        session.get = lambda url, headers=None, timeout=None: StubResponse({}, 404)  # type: ignore[method-assign]
        client = GraphClient(base_url="http://ws", session=session)
        assert client.lookup("emicizumab") == []


class TestGraphDoesNotAffectScore:
    def test_score_is_identical_with_and_without_graph_entities(self, area, config):
        """THE load-bearing assertion of graph.py's design.

        `score()` does not take graph entities as an argument at all, which is the
        structural guarantee. This test pins the intent so that adding such a
        parameter later is a visible, deliberate act rather than a quiet drift.
        """
        signal = make_signal()
        baseline = score(signal, area, config, today=FROZEN_TODAY)

        import inspect

        params = set(inspect.signature(score).parameters)
        assert "graph_entities" not in params, (
            "graph membership must not be a scoring input — a drug absent from the "
            "graph is more likely to be the novel opportunity, not less relevant"
        )
        assert score(signal, area, config, today=FROZEN_TODAY).score == baseline.score


class TestReviewFlagging:
    def _result(self, area, config, **kw):
        return score(make_signal(**kw), area, config, today=FROZEN_TODAY)

    def test_borderline_score_is_flagged(self, area):
        config = ScanConfig()
        signal = make_signal()
        result = self._result(area, config)
        # Move the threshold onto the computed score so the boundary case is exact.
        tuned = ScanConfig(thresholds=Thresholds(high=result.score, med=result.score - 20))
        reasons = assess(
            signal, result, tuned,
            source_count=2, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.BORDERLINE_SCORE in reasons

    def test_comfortably_inside_a_band_is_not_flagged_as_borderline(self, area, config):
        signal = make_signal()
        result = self._result(area, config)
        tuned = ScanConfig(
            thresholds=Thresholds(
                high=result.score - (BORDERLINE_MARGIN + 10),
                med=result.score - (BORDERLINE_MARGIN + 30),
            )
        )
        reasons = assess(
            signal, result, tuned,
            source_count=2, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.BORDERLINE_SCORE not in reasons

    def test_thin_evidence_needs_all_three_conditions(self, area, config):
        """No corroboration AND a minimal topical match AND no attribution."""
        signal = make_signal(keywords=("hemophilia",), company_name=None)
        reasons = assess(
            signal, self._result(area, config, keywords=("hemophilia",)), config,
            source_count=1, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.THIN_EVIDENCE in reasons

    def test_an_attributed_signal_is_not_thin(self, area, config):
        """CALIBRATION: requiring only one-source-and-one-keyword fired on 65% of a
        live corpus, because single-source is the norm. A marker on two rows in three
        is decoration an analyst learns to scroll past."""
        signal = make_signal(keywords=("hemophilia",), company_name="Acme Inc")
        reasons = assess(
            signal, self._result(area, config, keywords=("hemophilia",)), config,
            source_count=1, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.THIN_EVIDENCE not in reasons

    def test_corroborated_signal_is_not_thin(self, area, config):
        signal = make_signal(keywords=("hemophilia", "factor viii"), company_name=None)
        reasons = assess(
            signal, self._result(area, config), config,
            source_count=2, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.THIN_EVIDENCE not in reasons

    def test_rejected_llm_output_is_flagged(self, area, config):
        """The template shown is correct, but the rejection is itself information:
        the model could not describe this signal without inventing something."""
        reasons = assess(
            make_signal(), self._result(area, config), config,
            source_count=2, rationale_kind=RationaleKind.TEMPLATE, llm_was_attempted=True,
        )
        assert ReviewReason.UNVERIFIED_RATIONALE in reasons

    def test_template_without_an_llm_is_not_flagged(self, area, config):
        """No provider configured is not a confidence signal — it is a deployment fact."""
        reasons = assess(
            make_signal(), self._result(area, config), config,
            source_count=2, rationale_kind=RationaleKind.TEMPLATE, llm_was_attempted=False,
        )
        assert ReviewReason.UNVERIFIED_RATIONALE not in reasons

    def test_undated_signal_is_flagged(self, area, config):
        signal = make_signal(published=None)
        reasons = assess(
            signal, self._result(area, config, published=None), config,
            source_count=2, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert ReviewReason.UNDATED in reasons

    def test_a_strong_signal_carries_no_flags(self, area, config):
        signal = make_signal(keywords=("hemophilia", "factor viii", "emicizumab"))
        result = self._result(area, config, keywords=("hemophilia", "factor viii", "emicizumab"))
        tuned = ScanConfig(thresholds=Thresholds(high=result.score - 15, med=result.score - 35))
        reasons = assess(
            signal, result, tuned,
            source_count=3, rationale_kind=RationaleKind.LLM, llm_was_attempted=True,
        )
        assert reasons == []

    def test_assess_is_pure(self, area, config):
        """No clock, no I/O — the same signal must flag identically every time."""
        signal = make_signal(keywords=("hemophilia",))
        result = self._result(area, config, keywords=("hemophilia",))
        runs = [
            assess(signal, result, config, source_count=1,
                   rationale_kind=RationaleKind.LLM, llm_was_attempted=True)
            for _ in range(20)
        ]
        assert all(r == runs[0] for r in runs)

    def test_summarise_counts_by_reason(self):
        counts = summarise([
            ("a", [ReviewReason.THIN_EVIDENCE]),
            ("b", [ReviewReason.THIN_EVIDENCE, ReviewReason.UNDATED]),
        ])
        assert counts == {"thin_evidence": 2, "undated": 1}


class TestNothingIsSuppressed:
    def test_flagged_signals_still_appear_in_query_results(self, store):
        """The use case's actual requirement: flag uncertainty, do not hide it."""
        from scout.index import SignalIndex
        from scout.models import Priority, Signal, SignalSource, SignalType, SourceId
        from tests.conftest import FROZEN_NOW

        flagged = Signal(
            id="sig-flagged-0001",
            area="hemophilia",
            type=SignalType.TRIAL,
            title="A borderline trial",
            score=74.0,
            priority=Priority.MED,
            published=FROZEN_TODAY,
            detected_at=FROZEN_NOW,
            first_seen_run="r1",
            last_seen_run="r1",
            needs_review=True,
            review_reasons=[ReviewReason.THIN_EVIDENCE],
            sources=[SignalSource(source=SourceId.TRIALS, external_id="x",
                                  url="https://clinicaltrials.gov/study/NCT1")],
        )
        store.publish_area("hemophilia", [flagged], [], day=FROZEN_TODAY, run_id="r1")
        index = SignalIndex(store)
        index.refresh(["hemophilia"])
        rows, total, _ = index.query_signals()
        assert total == 1
        assert rows[0]["needs_review"] is True

    def test_confidence_note_is_human_readable(self):
        from scout.models import Priority, Signal, SignalSource, SignalType, SourceId
        from tests.conftest import FROZEN_NOW

        s = Signal(
            id="sig-x-00000001", area="a", type=SignalType.TRIAL, title="t",
            score=50.0, priority=Priority.MED, detected_at=FROZEN_NOW,
            first_seen_run="r", last_seen_run="r",
            review_reasons=[ReviewReason.THIN_EVIDENCE, ReviewReason.BORDERLINE_SCORE],
            sources=[SignalSource(source=SourceId.TRIALS, external_id="x",
                                  url="https://clinicaltrials.gov/study/NCT1")],
        )
        note = s.confidence_note
        assert "single source" in note and "boundary" in note
