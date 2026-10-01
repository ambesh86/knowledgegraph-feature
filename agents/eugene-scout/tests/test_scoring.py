"""Scoring tests.

The contract this file defends is that `score()` is a pure, reproducible function
whose output is fully explained by its recorded breakdown. Everything downstream — the
watchlist ranking, the notification threshold, the briefing order — inherits its
trustworthiness from here, so these tests are the load-bearing ones in the suite.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.config import ScanConfig, ScoringWeights, Thresholds
from scout.models import Priority, SourceId
from scout.scoring import score, signal_type_for
from tests.conftest import FROZEN_TODAY, make_signal


class TestDeterminism:
    def test_identical_inputs_produce_identical_output(self, area, config):
        signal = make_signal()
        results = [score(signal, area, config, today=FROZEN_TODAY) for _ in range(100)]
        assert len({r.score for r in results}) == 1
        assert len({r.priority for r in results}) == 1

    def test_breakdown_is_stable_across_calls(self, area, config):
        signal = make_signal()
        first = score(signal, area, config, today=FROZEN_TODAY).breakdown()
        second = score(signal, area, config, today=FROZEN_TODAY).breakdown()
        assert first == second

    def test_score_does_not_depend_on_wall_clock(self, area, config):
        """`today` is an argument, so a different 'now' must change nothing unless it
        is passed in. This is what makes historical replay meaningful."""
        signal = make_signal(published=dt.date(2026, 8, 1))
        a = score(signal, area, config, today=dt.date(2026, 8, 8))
        b = score(signal, area, config, today=dt.date(2026, 8, 8))
        assert a.score == b.score


class TestBounds:
    def test_score_within_range(self, area, config):
        for days in (0, 1, 10, 44, 400):
            signal = make_signal(published=FROZEN_TODAY - dt.timedelta(days=days))
            result = score(signal, area, config, today=FROZEN_TODAY)
            assert 0.0 <= result.score <= 100.0

    def test_no_applicable_factors_scores_zero_not_crash(self, area):
        """All weights zeroed would divide by zero if normalisation were naive."""
        config = ScanConfig(
            weights=ScoringWeights(
                area_fit=0, stage_fit=0, recency=0, modality_fit=0,
                corroboration=0, company_context=1,
            )
        )
        signal = make_signal(company_name=None, keywords=())
        result = score(signal, area, config, today=FROZEN_TODAY)
        assert result.score == 0.0
        assert result.priority is Priority.WATCH

    def test_all_weights_zero_is_rejected_at_config_boundary(self):
        with pytest.raises(ValueError, match="greater than zero"):
            ScoringWeights(
                area_fit=0, stage_fit=0, recency=0,
                modality_fit=0, corroboration=0, company_context=0,
            )


class TestFactorBehaviour:
    def test_more_keyword_matches_scores_higher(self, area, config):
        few = make_signal(keywords=("hemophilia",))
        many = make_signal(keywords=("hemophilia", "factor viii", "emicizumab"))
        assert score(many, area, config, today=FROZEN_TODAY).score > score(
            few, area, config, today=FROZEN_TODAY
        ).score

    def test_recent_beats_stale(self, area, config):
        fresh = make_signal(published=FROZEN_TODAY - dt.timedelta(days=1))
        stale = make_signal(published=FROZEN_TODAY - dt.timedelta(days=40))
        assert score(fresh, area, config, today=FROZEN_TODAY).score > score(
            stale, area, config, today=FROZEN_TODAY
        ).score

    def test_phase2_outranks_phase4(self, area, config):
        """The use case targets Phase I/II, where a partnership is still available.
        By Phase IV the asset is marketed and the deal window has closed."""
        early = make_signal(stage="PHASE2")
        late = make_signal(stage="PHASE4")
        assert score(early, area, config, today=FROZEN_TODAY).score > score(
            late, area, config, today=FROZEN_TODAY
        ).score

    def test_corroboration_raises_score(self, area, config):
        signal = make_signal()
        one = score(signal, area, config, today=FROZEN_TODAY, corroboration_count=1)
        two = score(signal, area, config, today=FROZEN_TODAY, corroboration_count=2)
        assert two.score > one.score

    def test_unknown_stage_scores_neutral_not_zero(self, area, config):
        """A registry adding a new phase enum must not be punished as irrelevant."""
        unknown = score(make_signal(stage="PHASE_NEW"), area, config, today=FROZEN_TODAY)
        factor = next(f for f in unknown.factors if f.name == "stage_fit")
        assert factor.value == pytest.approx(0.5)
        assert factor.inputs["known"] is False

    def test_missing_stage_is_excluded_not_zeroed(self, area, config):
        """A paper has no development stage. Scoring it zero would make literature
        permanently uncompetitive with trials regardless of relevance."""
        paper = make_signal(source=SourceId.LITERATURE, stage=None)
        result = score(paper, area, config, today=FROZEN_TODAY)
        assert not any(f.name == "stage_fit" for f in result.factors)

    def test_undated_signal_excludes_recency(self, area, config):
        result = score(make_signal(published=None), area, config, today=FROZEN_TODAY)
        assert not any(f.name == "recency" for f in result.factors)

    def test_unattributed_signal_excludes_company_context(self, area, config):
        result = score(make_signal(company_name=None), area, config, today=FROZEN_TODAY)
        assert not any(f.name == "company_context" for f in result.factors)


class TestExplainability:
    def test_every_factor_records_its_inputs(self, area, config):
        result = score(make_signal(), area, config, today=FROZEN_TODAY)
        assert result.factors
        for factor in result.factors:
            assert factor.inputs, f"{factor.name} recorded no inputs"

    def test_breakdown_contributions_reconstruct_the_score(self, area, config):
        """An analyst adding up the factor panel must get the number on the badge."""
        result = score(make_signal(), area, config, today=FROZEN_TODAY)
        total_weight = sum(f.weight for f in result.factors)
        recomputed = 100.0 * sum(f.contribution for f in result.factors) / total_weight
        assert recomputed == pytest.approx(result.score, abs=0.01)

    def test_matched_keywords_are_named_in_the_breakdown(self, area, config):
        result = score(make_signal(keywords=("hemophilia", "factor viii")), area, config,
                       today=FROZEN_TODAY)
        area_fit = next(f for f in result.factors if f.name == "area_fit")
        assert set(area_fit.inputs["matched"]) == {"hemophilia", "factor viii"}


class TestConfigurability:
    def test_weight_change_moves_score_in_expected_direction(self, area):
        """Weights are configuration; changing them must actually change ranking."""
        signal = make_signal(published=FROZEN_TODAY - dt.timedelta(days=40), stage="PHASE2")
        recency_heavy = ScanConfig(
            weights=ScoringWeights(area_fit=0.1, stage_fit=0.1, recency=1.0,
                                   modality_fit=0.1, corroboration=0.1, company_context=0.1)
        )
        stage_heavy = ScanConfig(
            weights=ScoringWeights(area_fit=0.1, stage_fit=1.0, recency=0.1,
                                   modality_fit=0.1, corroboration=0.1, company_context=0.1)
        )
        assert score(signal, area, stage_heavy, today=FROZEN_TODAY).score > score(
            signal, area, recency_heavy, today=FROZEN_TODAY
        ).score

    def test_thresholds_determine_priority(self, area):
        signal = make_signal()
        permissive = ScanConfig(thresholds=Thresholds(high=1.0, med=0.5))
        strict = ScanConfig(thresholds=Thresholds(high=99.9, med=99.0))
        assert score(signal, area, permissive, today=FROZEN_TODAY).priority is Priority.HIGH
        assert score(signal, area, strict, today=FROZEN_TODAY).priority is Priority.WATCH

    def test_thresholds_must_be_ordered(self):
        with pytest.raises(ValueError, match="must exceed"):
            Thresholds(high=50.0, med=75.0)

    def test_per_source_window_normalises_recency(self, area, config):
        """A 300-day-old patent is fresh for its corpus; a 300-day-old paper is not.
        Both must score their recency against their own window."""
        old = FROZEN_TODAY - dt.timedelta(days=300)
        patent = make_signal(source=SourceId.PATENTS, published=old, stage=None)
        paper = make_signal(source=SourceId.LITERATURE, published=old, stage=None)
        p_recency = next(
            f for f in score(patent, area, config, today=FROZEN_TODAY).factors if f.name == "recency"
        )
        # The paper is outside its own 45-day window, so recency floors at zero.
        l_recency = next(
            f for f in score(paper, area, config, today=FROZEN_TODAY).factors if f.name == "recency"
        )
        assert p_recency.value > l_recency.value
        assert l_recency.value == 0.0


class TestSignalTypeMapping:
    def test_each_source_maps_to_a_ui_signal_type(self):
        """The UI's filter chips are built from these values; a str here instead of
        the enum crashed the first live run."""
        for source in SourceId:
            mapped = signal_type_for(source)
            assert mapped.value in {"Trial", "Patent", "Publication", "Regulatory", "Corporate"}
