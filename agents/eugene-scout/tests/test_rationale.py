"""Rationale generation and — more importantly — the fence around it.

`verify` is the control that stops a fabricated statistic reaching a BD briefing.
These tests are the specification of that control. If they are ever weakened, the
weakening should be a deliberate, argued decision, because the failure mode they
prevent ("a 12-month readout showed 78% efficacy" about a trial that reported neither)
is the most expensive output this system could produce.
"""
from __future__ import annotations

import pytest

from scout.models import RationaleKind, SignalType
from scout.rationale import build, verify
from scout.scoring import score
from tests.conftest import FROZEN_TODAY, make_signal


@pytest.fixture
def result(area, config):
    return score(make_signal(), area, config, today=FROZEN_TODAY)


def _facts_for(result):
    return {
        "score": f"{result.score:.0f}",
        "factors": [
            {"name": f.name, "value": f"{f.value:.2f}", "weight": f"{f.weight:.2f}",
             "inputs": f.inputs}
            for f in result.factors
        ],
        "published": "2026-08-05",
        "stage": "PHASE2",
    }


class TestTemplatePath:
    def test_template_is_used_when_no_provider_is_configured(self, monkeypatch, result):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("SCOUT_LLM_ENABLED", "false")
        text, kind = build(
            title="A trial", summary="Summary", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company="Acme Inc", stage="PHASE2",
            published="2026-08-05", result=result, source_names=["clinicaltrials"],
        )
        assert kind is RationaleKind.TEMPLATE
        assert text

    def test_template_names_the_company_and_score(self, result):
        text, _ = build(
            title="A trial", summary="Summary", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company="Acme Inc", stage="PHASE2",
            published="2026-08-05", result=result, source_names=["clinicaltrials"],
        )
        assert "Acme Inc" in text
        assert f"{result.score:.0f}" in text

    def test_template_reports_corroboration(self, result):
        text, _ = build(
            title="A trial", summary="S", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company=None, stage=None, published=None,
            result=result, source_names=["clinicaltrials", "sec_edgar"],
        )
        assert "2 sources" in text

    def test_template_never_raises_on_sparse_input(self, area, config):
        """A rationale is a nice-to-have; it must never be able to fail a scan."""
        sparse = score(
            make_signal(company_name=None, stage=None, published=None, keywords=("hemophilia",)),
            area, config, today=FROZEN_TODAY,
        )
        text, kind = build(
            title="x", summary="", signal_type=SignalType.PUBLICATION,
            area_label="Hemophilia", company=None, stage=None, published=None,
            result=sparse, source_names=[],
        )
        assert kind is RationaleKind.TEMPLATE
        assert text


class TestNumericFence:
    def test_permits_numbers_that_were_supplied(self, result):
        facts = _facts_for(result)
        ok, _ = verify(f"The signal scored {result.score:.0f} and was published 2026-08-05.", facts)
        assert ok is True

    def test_rejects_a_fabricated_statistic(self, result):
        """The characteristic failure: a confident, specific, invented number."""
        ok, reason = verify(
            "A 12-month readout showed 78.4% efficacy in the treatment arm.", _facts_for(result)
        )
        assert ok is False
        assert "fabricated number" in reason

    @pytest.mark.parametrize(
        "text",
        [
            "Enrolment of 240 patients was reported.",
            "The programme raised $85 million in Series B funding.",
            "Results were presented at the 2019 congress.",
            "A 3.5-fold increase was observed.",
        ],
    )
    def test_rejects_various_invented_figures(self, text, result):
        assert verify(text, _facts_for(result))[0] is False

    def test_rejects_a_refusal(self, result):
        ok, reason = verify(
            "I cannot provide an assessment without more information.", _facts_for(result)
        )
        assert ok is False
        assert reason == "model refused"

    def test_rejects_empty_output(self, result):
        assert verify("   ", _facts_for(result))[0] is False

    def test_rejects_runaway_length(self, result):
        assert verify("word " * 200, _facts_for(result))[0] is False

    def test_accepts_prose_with_no_numbers_at_all(self, result):
        ok, _ = verify(
            "The programme aligns closely with the therapeutic area and CSL's existing "
            "capability, making it a credible partnership candidate.",
            _facts_for(result),
        )
        assert ok is True

    def test_decimal_form_of_a_supplied_integer_passes(self, result):
        """A score supplied as "78" licenses writing "78.0" — otherwise the fence
        rejects prose that is entirely faithful to its input."""
        facts = _facts_for(result)
        supplied = f"{result.score:.0f}"
        assert verify(f"Scored {supplied}.0 overall.", facts)[0] is True

    def test_extra_precision_beyond_what_was_supplied_is_rejected(self, result):
        """Deliberate strictness. The facts round the score to a whole number, so a
        model writing 77.8 has invented a decimal place it was never shown. The cost
        of this rule is occasional over-rejection into a correct template; the cost of
        relaxing it is a fabricated figure nobody catches."""
        facts = _facts_for(result)
        assert verify(f"Scored {result.score:.1f} overall.", facts)[0] is False


class TestLlmPathDegradation:
    def test_provider_failure_falls_back_to_template(self, monkeypatch, result):
        """A Bedrock outage must produce a briefing, not an exception."""
        monkeypatch.setenv("SCOUT_LLM_ENABLED", "true")
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")

        def explode(_prompt):
            raise RuntimeError("bedrock unavailable")

        monkeypatch.setattr("scout.rationale._bedrock", explode)
        text, kind = build(
            title="A trial", summary="S", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company="Acme Inc", stage="PHASE2",
            published="2026-08-05", result=result, source_names=["clinicaltrials"],
        )
        assert kind is RationaleKind.TEMPLATE
        assert text

    def test_fabricating_model_output_is_discarded(self, monkeypatch, result):
        monkeypatch.setenv("SCOUT_LLM_ENABLED", "true")
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        monkeypatch.setattr(
            "scout.rationale._bedrock",
            lambda _p: "The trial enrolled 512 patients and hit a 91% response rate.",
        )
        text, kind = build(
            title="A trial", summary="S", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company="Acme Inc", stage="PHASE2",
            published="2026-08-05", result=result, source_names=["clinicaltrials"],
        )
        assert kind is RationaleKind.TEMPLATE
        assert "512" not in text

    def test_clean_model_output_is_kept_and_labelled(self, monkeypatch, result):
        monkeypatch.setenv("SCOUT_LLM_ENABLED", "true")
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        clean = (
            "This programme sits squarely in the target therapeutic area and overlaps "
            "CSL's existing capability, which is what lifted its ranking."
        )
        monkeypatch.setattr("scout.rationale._bedrock", lambda _p: clean)
        text, kind = build(
            title="A trial", summary="S", signal_type=SignalType.TRIAL,
            area_label="Hemophilia", company="Acme Inc", stage="PHASE2",
            published="2026-08-05", result=result, source_names=["clinicaltrials"],
        )
        assert kind is RationaleKind.LLM
        assert text == clean

    def test_disabled_flag_skips_the_provider_entirely(self, monkeypatch, result):
        monkeypatch.setenv("SCOUT_LLM_ENABLED", "false")

        def fail(_p):
            raise AssertionError("provider must not be called when disabled")

        monkeypatch.setattr("scout.rationale._bedrock", fail)
        _, kind = build(
            title="t", summary="s", signal_type=SignalType.TRIAL, area_label="H",
            company=None, stage=None, published=None, result=result, source_names=[],
        )
        assert kind is RationaleKind.TEMPLATE
