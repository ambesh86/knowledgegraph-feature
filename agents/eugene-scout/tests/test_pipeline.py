"""Text normalisation, relevance gating, dedup and company aggregation.

Several of these tests exist because the behaviour they assert was measured broken on
a live run first. Those are marked in their docstrings — they are regression tests
with a known incident behind them, not speculative coverage.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.companies import aggregate
from scout.config import ScanConfig
from scout.dedupe import dedupe_identity, group_corroborated, primary_of
from scout.enrich import company_id_for, enrich, is_commercial, is_relevant
from scout.models import (
    Priority,
    Signal,
    SignalSource,
    SignalType,
    SourceId,
    clean_text,
    parse_date,
)
from scout.text import matched_keywords, normalize, normalize_company
from tests.conftest import FROZEN_NOW, FROZEN_TODAY, make_signal


class TestTextNormalisation:
    def test_british_spelling_matches_american_keyword(self):
        """REGRESSION: a live Europe PMC result titled "Quality of Life in People With
        Haemophilia" matched zero keywords, silently sinking every British-spelled
        paper to the bottom of the Radar."""
        assert matched_keywords(("hemophilia",), "Quality of Life in People With Haemophilia") == (
            "hemophilia",
        )

    @pytest.mark.parametrize(
        ("text", "keyword"),
        [
            ("Haemophilia A", "hemophilia"),
            ("severe anaemia reported", "anemia"),
            ("pulmonary oedema", "edema"),
            ("tumour burden", "tumor"),
            ("FACTOR-VIII deficiency", "factor viii"),
            ("factor 8 activity", "factor viii"),
            ("CAR-T cell therapy", "car t"),
        ],
    )
    def test_variants_match(self, text, keyword):
        assert matched_keywords((keyword,), text) == (keyword,)

    def test_matching_is_word_boundary_aware(self):
        """Substring matching made "ig" match inside "light", which produced keyword
        hits an analyst would call nonsense."""
        assert matched_keywords(("ig",), "the light microscope") == ()
        assert matched_keywords(("ig",), "subcutaneous Ig therapy") == ("ig",)

    def test_original_spelling_is_returned_not_the_normalised_form(self):
        """The UI shows these to analysts; returning a different spelling than the one
        declared looks like a bug even when the match is right."""
        assert matched_keywords(("haemophilia",), "Hemophilia A study") == ("haemophilia",)

    def test_stemming_is_not_applied(self):
        """`inhibitor` is a specific clinical complication in hemophilia, not a
        generic mechanism word. Collapsing it with `inhibition` would produce matches
        a haematologist would reject."""
        assert matched_keywords(("inhibitor",), "inhibition of the pathway") == ()

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            ("Sangamo Therapeutics, Inc.", "SANGAMO THERAPEUTICS INC"),
            ("Sangamo Therapeutics", "Sangamo Therapeutics Inc."),
            ("Roche Holding AG", "Roche Holding"),
            ("Acme Bio N.V.", "ACME BIO NV"),
            # REGRESSION: these two appeared as separate watchlist rows on a live run,
            # splitting one company's evidence across both.
            ("BIOVERATIV THERAPEUTICS INC.", "Bioverativ, a Sanofi company"),
            ("Regeneron Pharmaceuticals", "Regeneron"),
            ("Spur Therapeutics", "Spur"),
            ("Acme Biosciences", "Acme"),
            ("Acme Labs (a Zeta subsidiary)", "Acme Laboratories"),
        ],
    )
    def test_company_variants_normalise_together(self, a, b):
        assert normalize_company(a) == normalize_company(b)
        assert company_id_for(a) == company_id_for(b)

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            ("Pfizer Inc.", "Bayer AG"),
            # Sibling entities of one parent are NOT one company — merging them would
            # attribute one's pipeline to the other. `products` is deliberately absent
            # from the descriptor list for exactly this reason.
            ("Roche Holding AG", "Roche Products Ltd"),
            ("Precision BioSciences", "Precision Optics Corporation"),
            ("CSL Behring", "CSL Seqirus"),
        ],
    )
    def test_distinct_companies_do_not_collide(self, a, b):
        assert company_id_for(a) != company_id_for(b)

    def test_stripping_never_empties_an_identity(self):
        """A filer genuinely named "Therapeutics Inc" must keep an identity rather
        than collapsing to "" and colliding with every other fully-stripped name."""
        assert normalize_company("Therapeutics Inc") == "therapeutics"
        assert normalize_company("Pharma Inc") == "pharma"
        assert normalize_company("Therapeutics Inc") != normalize_company("Pharma Inc")

    def test_company_id_is_deterministic_across_processes(self):
        """`company_id_for` hashes the normalised name, so an id must not depend on
        which other names happened to appear in the same scan — otherwise a rebuild
        from staging would orphan every stored reference."""
        assert company_id_for("Regeneron Pharmaceuticals") == company_id_for("Regeneron")
        assert company_id_for("Regeneron") == company_id_for("  regeneron  ")

    def test_clean_text_strips_markup_and_entities(self):
        assert clean_text("Factor <sup>VIII</sup> &amp; IX") == "Factor VIII & IX"


class TestDateParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2026-08-07", dt.date(2026, 8, 7)),
            ("2026", dt.date(2026, 1, 1)),
            ("2026-08", dt.date(2026, 8, 1)),
            ("", None),
            (None, None),
            ("not-a-date", None),
        ],
    )
    def test_upstream_date_shapes(self, raw, expected):
        assert parse_date(raw) == expected


class TestRelevanceGate:
    def test_zero_keyword_match_is_rejected(self, config):
        """REGRESSION: an oncology checkpoint-inhibitor trial entered the hemophilia
        area because the registry's free-text search matched somewhere in its protocol."""
        signal = make_signal(keywords=())
        keep, reason = is_relevant(signal, config)
        assert keep is False
        assert "no area keywords" in reason

    def test_generic_only_match_is_rejected(self, config):
        """REGRESSION: USPTO patents for hearing loss and phenylketonuria entered on
        the strength of "gene therapy" alone."""
        signal = make_signal(keywords=("gene therapy",))
        keep, reason = is_relevant(signal, config)
        assert keep is False
        assert "generic" in reason

    def test_specific_match_is_accepted(self, config):
        keep, _ = is_relevant(make_signal(keywords=("hemophilia",)), config)
        assert keep is True

    def test_gate_can_be_disabled(self):
        config = ScanConfig(min_specific_matches=0)
        assert is_relevant(make_signal(keywords=("gene therapy",)), config)[0] is True

    def test_gate_threshold_is_configurable(self):
        config = ScanConfig(min_specific_matches=2)
        assert is_relevant(make_signal(keywords=("hemophilia",)), config)[0] is False
        assert is_relevant(make_signal(keywords=("hemophilia", "factor viii")), config)[0] is True


class TestCompanyAttribution:
    @pytest.mark.parametrize(
        "name",
        ["Stanford University", "Assistance Publique Hopitaux de Paris", "NHS Trust",
         "National Cancer Institute", "Mayo Clinic"],
    )
    def test_non_commercial_sponsors_are_not_partners(self, name):
        assert is_commercial(name) is False

    @pytest.mark.parametrize(
        "name", ["Pfizer Inc.", "Sangamo Therapeutics", "CSL Behring", "Hoffmann-La Roche"]
    )
    def test_commercial_sponsors_are_partners(self, name):
        assert is_commercial(name) is True

    def test_enrich_drops_academic_attribution_but_keeps_signal(self, area, config):
        signal = make_signal(company_name="Stanford University")
        enriched = enrich(signal, area, config)
        assert enriched.company_name is None
        assert enriched.title == signal.title

    def test_enrich_rematches_keywords_across_payload(self, area, config):
        signal = make_signal(
            title="A Study",
            summary="",
            keywords=(),
            payload={"conditions": ["Hemophilia A"], "interventions": ["emicizumab"]},
        )
        enriched = enrich(signal, area, config)
        assert set(enriched.keywords) >= {"hemophilia", "emicizumab"}


class TestDedupe:
    def test_identity_dedupe_collapses_refetches(self):
        a = make_signal(external_id="NCT1")
        b = make_signal(external_id="NCT1", title="Slightly Edited Title")
        assert len(dedupe_identity([a, b])) == 1

    def test_distinct_records_survive(self):
        a = make_signal(external_id="NCT1")
        b = make_signal(external_id="NCT2")
        assert len(dedupe_identity([a, b])) == 2

    def test_identity_ignores_title_edits(self):
        """A copy-edited registry title must not resurface as a new signal every night."""
        a = make_signal(external_id="NCT1", title="Original")
        b = make_signal(external_id="NCT1", title="Completely Different Wording Here")
        assert a.content_hash == b.content_hash

    def test_cross_source_merge_groups_the_same_event(self):
        title = "Acme Reports Positive Phase 2 Results for Factor VIII Gene Therapy Programme"
        trial = make_signal(source=SourceId.TRIALS, external_id="NCT9", title=title)
        filing = make_signal(source=SourceId.EDGAR, external_id="8K-9", title=title)
        groups = group_corroborated([trial, filing])
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_same_source_records_never_merge(self):
        title = "Acme Reports Positive Phase 2 Results for Factor VIII Gene Therapy Programme"
        a = make_signal(source=SourceId.TRIALS, external_id="NCT1", title=title)
        b = make_signal(source=SourceId.TRIALS, external_id="NCT2", title=title)
        assert len(group_corroborated([a, b])) == 2

    def test_different_companies_never_merge(self):
        title = "Positive Phase 2 Results for Factor VIII Gene Therapy Programme Announced"
        a = make_signal(source=SourceId.TRIALS, external_id="1", title=title, company_name="Acme Inc")
        b = make_signal(source=SourceId.EDGAR, external_id="2", title=title, company_name="Zeta Corp")
        assert len(group_corroborated([a, b])) == 2

    def test_temporally_distant_records_never_merge(self):
        title = "Acme Reports Positive Phase 2 Results for Factor VIII Gene Therapy Programme"
        a = make_signal(source=SourceId.TRIALS, external_id="1", title=title,
                        published=dt.date(2026, 1, 5))
        b = make_signal(source=SourceId.EDGAR, external_id="2", title=title,
                        published=dt.date(2026, 6, 5))
        assert len(group_corroborated([a, b])) == 2

    def test_short_titles_never_merge(self):
        """Titles that are mostly stopwords make similarity meaningless."""
        a = make_signal(source=SourceId.TRIALS, external_id="1", title="A Study of X")
        b = make_signal(source=SourceId.EDGAR, external_id="2", title="A Study of Y")
        assert len(group_corroborated([a, b])) == 2

    def test_primary_prefers_the_richest_source(self):
        title = "Acme Reports Positive Phase 2 Results for Factor VIII Gene Therapy Programme"
        trial = make_signal(source=SourceId.TRIALS, external_id="NCT9", title=title)
        filing = make_signal(source=SourceId.EDGAR, external_id="8K-9", title=title)
        assert primary_of([filing, trial]).source is SourceId.TRIALS


def _signal(score: float, company: str | None = "Acme Inc", priority=Priority.MED,
            signal_id: str = "sig-00000001", published: dt.date | None = None) -> Signal:
    return Signal(
        id=signal_id,
        area="hemophilia",
        type=SignalType.TRIAL,
        title="A trial",
        score=score,
        priority=priority,
        company_name=company,
        company_id=company_id_for(company) if company else None,
        published=published or FROZEN_TODAY,
        detected_at=FROZEN_NOW,
        first_seen_run="r1",
        last_seen_run="r1",
        sources=[SignalSource(source=SourceId.TRIALS, external_id="x",
                              url="https://clinicaltrials.gov/study/NCT1")],
    )


class TestCompanyAggregation:
    def test_score_is_best_signal_plus_support_bonus(self):
        """Base is the strongest signal; two equally strong ones support it."""
        signals = [_signal(90, signal_id=f"sig-{i:08d}") for i in range(3)]
        rows = aggregate(signals, now=FROZEN_NOW)
        assert len(rows) == 1
        assert rows[0].score == pytest.approx(94.0)  # 90 + 2 supporting x 2.0
        assert rows[0].breakdown["base_best_signal_score"] == pytest.approx(90.0)
        assert rows[0].breakdown["supporting_signals"] == 2

    def test_single_signal_scores_exactly_that_signal(self):
        assert aggregate([_signal(90)], now=FROZEN_NOW)[0].score == pytest.approx(90.0)

    def test_weak_extra_signals_do_not_lower_the_score(self):
        """The defect the previous top-k-mean formula had: being found out about more
        made a company look weaker."""
        alone = aggregate([_signal(90, company="Solo Inc")], now=FROZEN_NOW)[0]
        with_noise = aggregate(
            [_signal(90, company="Noisy Inc", signal_id="sig-00000001"),
             _signal(20, company="Noisy Inc", signal_id="sig-00000002"),
             _signal(15, company="Noisy Inc", signal_id="sig-00000003")],
            now=FROZEN_NOW,
        )[0]
        assert with_noise.score >= alone.score

    def test_only_signals_within_the_support_band_count(self):
        row = aggregate(
            [_signal(90, signal_id="sig-00000001"),
             _signal(80, signal_id="sig-00000002"),   # within 15 -> supports
             _signal(40, signal_id="sig-00000003")],  # outside 15 -> does not
            now=FROZEN_NOW,
        )[0]
        assert row.breakdown["supporting_signals"] == 1
        assert row.score == pytest.approx(92.0)

    def test_coverage_is_not_punished(self):
        """Mean-of-all would rank the better-documented company lower, which is
        backwards for a BD watchlist."""
        lean = aggregate([_signal(90, company="Lean Inc")], now=FROZEN_NOW)[0]
        documented = aggregate(
            [_signal(90, company="Doc Inc", signal_id="sig-00000001"),
             _signal(50, company="Doc Inc", signal_id="sig-00000002"),
             _signal(50, company="Doc Inc", signal_id="sig-00000003")],
            now=FROZEN_NOW,
        )[0]
        assert documented.score >= lean.score

    def test_volume_bonus_is_bounded(self):
        """Volume must be a tie-breaker, not a way to out-file your way to the top."""
        many = aggregate(
            [_signal(60, signal_id=f"sig-{i:08d}") for i in range(50)], now=FROZEN_NOW
        )[0]
        assert many.score <= 60.0 + 6.0

    def test_unattributed_signals_produce_no_company_row(self):
        assert aggregate([_signal(90, company=None)], now=FROZEN_NOW) == []

    def test_dismissed_signals_are_excluded(self):
        signal = _signal(90)
        signal.dismissed = True
        assert aggregate([signal], now=FROZEN_NOW) == []

    def test_stale_signals_stop_contributing(self):
        old = _signal(90, published=FROZEN_TODAY - dt.timedelta(days=500))
        assert aggregate([old], now=FROZEN_NOW) == []

    def test_delta_is_zero_without_a_baseline(self):
        """An arrow implying movement when nothing exists to compare against is a lie
        the UI would render confidently."""
        row = aggregate([_signal(80)], now=FROZEN_NOW, previous=None)[0]
        assert row.delta_30d == 0.0
        assert row.breakdown["has_baseline"] is False

    def test_delta_reflects_the_baseline(self):
        cid = company_id_for("Acme Inc")
        row = aggregate([_signal(80)], now=FROZEN_NOW, previous={cid: 70.0})[0]
        assert row.delta_30d == pytest.approx(10.0)

    def test_company_name_variants_produce_one_row(self):
        rows = aggregate(
            [_signal(80, company="Sangamo Therapeutics, Inc.", signal_id="sig-00000001"),
             _signal(70, company="SANGAMO THERAPEUTICS INC", signal_id="sig-00000002")],
            now=FROZEN_NOW,
        )
        assert len(rows) == 1
        assert rows[0].signal_count == 2

    def test_rows_are_ranked_by_score(self):
        rows = aggregate(
            [_signal(60, company="Low Inc", signal_id="sig-00000001"),
             _signal(90, company="High Inc", signal_id="sig-00000002")],
            now=FROZEN_NOW,
        )
        assert [r.name for r in rows] == ["High Inc", "Low Inc"]


class TestGenericKeywordCalibration:
    """Generic terms are added on evidence, not intuition. Each entry here has a
    real false positive behind it."""

    def test_augmentation_alone_does_not_admit_a_signal(self, config):
        """REGRESSION: 'augmentation' is a genuine alpha-1 antitrypsin therapy term,
        and on its own it admitted USPTO patents from Palo Alto Networks ("automated
        prompt augmentation") and OPTUM ("authorization request augmentation")."""
        signal = make_signal(keywords=("augmentation",))
        keep, reason = is_relevant(signal, config)
        assert keep is False
        assert "generic" in reason

    def test_augmentation_with_a_specific_term_still_passes(self):
        """The word is not banned — it just cannot carry a signal by itself."""
        from scout.config import ScanConfig

        config = ScanConfig()
        signal = make_signal(keywords=("augmentation", "alpha-1 antitrypsin"))
        assert is_relevant(signal, config)[0] is True
