"""Notification dispatch.

This module messages real people, so its failure modes are social rather than
technical: alerting a BD team twice for one event, or alerting them at all from a
developer's laptop. Both are the kind of mistake that gets a feature switched off
permanently, so both are pinned here.

Delivery itself was verified end-to-end against a live webhook sink during
deployment; these tests cover the decision logic around it — who gets sent, when, and
exactly once — without touching a socket.
"""
from __future__ import annotations

import datetime as dt

import pytest

from scout.models import Priority, Signal, SignalSource, SignalType, SourceId
from scout.notify import Notifier, send_test
from tests.conftest import FROZEN_NOW, FROZEN_TODAY


def _signal(signal_id: str, score: float, priority: Priority = Priority.HIGH,
            dismissed: bool = False) -> Signal:
    # Signal.id enforces a minimum length (real ids are 32-char hashes), so short
    # test names are padded rather than the validator being loosened for tests.
    return Signal(
        id=f"sig-{signal_id}".ljust(12, "0"),
        area="hemophilia",
        type=SignalType.TRIAL,
        title=f"Trial {signal_id}",
        summary="A hemophilia trial.",
        rationale="Scored well on area fit.",
        score=score,
        priority=priority,
        company_name="Acme Inc",
        company_id="co-acme",
        published=FROZEN_TODAY,
        detected_at=FROZEN_NOW,
        first_seen_run="r1",
        last_seen_run="r1",
        dismissed=dismissed,
        sources=[SignalSource(source=SourceId.TRIALS, external_id=signal_id,
                              url=f"https://clinicaltrials.gov/study/{signal_id}")],  # noqa: E501
    )


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture webhook payloads instead of posting them."""
    captured: list[dict] = []

    def fake_post(url, body, signals, area_label):  # noqa: ANN001
        captured.append({"url": url, "body": body, "signals": list(signals)})
        return True

    monkeypatch.setattr("scout.notify._post_webhook", fake_post)
    monkeypatch.setenv("SCOUT_NOTIFY_WEBHOOK_URL", "https://hooks.example/test")
    return captured


class TestDisabledByDefault:
    def test_nothing_is_sent_unless_explicitly_enabled(self, storage, sent, monkeypatch):
        """A developer running `docker compose up` must not be able to message the
        BD team. This is a mistake you make once and hear about for a year."""
        monkeypatch.delenv("SCOUT_NOTIFY_ENABLED", raising=False)
        report = Notifier(storage).dispatch(
            [_signal("s1", 90)], run_id="r1", min_score=75, area_label="Hemophilia"
        )
        assert report["sent"] == 0
        assert "disabled" in report["reason"]
        assert sent == []

    def test_force_bypasses_the_flag_for_an_explicit_action(self, storage, sent, monkeypatch):
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "false")
        report = Notifier(storage).dispatch(
            [_signal("s1", 90)], run_id="r1", min_score=75, area_label="Hemophilia", force=True
        )
        assert report["sent"] == 1


class TestSelection:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch):
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")

    def test_only_signals_at_or_above_the_threshold(self, storage, sent):
        report = Notifier(storage).dispatch(
            [_signal("high", 90), _signal("low", 60, Priority.MED)],
            run_id="r1", min_score=75, area_label="Hemophilia",
        )
        assert report["sent"] == 1
        assert [s.id for s in sent[0]["signals"]] == ["sig-high0000"]

    def test_only_high_priority(self, storage, sent):
        """A high score in a med band is still not an alert-worthy event."""
        report = Notifier(storage).dispatch(
            [_signal("med", 90, Priority.MED)], run_id="r1", min_score=75, area_label="H"
        )
        assert report["sent"] == 0

    def test_dismissed_signals_are_never_notified(self, storage, sent):
        report = Notifier(storage).dispatch(
            [_signal("s1", 90, dismissed=True)], run_id="r1", min_score=75, area_label="H"
        )
        assert report["sent"] == 0

    def test_nothing_above_threshold_is_a_clean_no_op(self, storage, sent):
        report = Notifier(storage).dispatch(
            [_signal("s1", 10, Priority.WATCH)], run_id="r1", min_score=75, area_label="H"
        )
        assert report["sent"] == 0
        assert "threshold" in report["reason"]


class TestIdempotency:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch):
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")

    def test_a_repeat_run_notifies_nobody(self, storage, sent):
        """One operator re-running a failed job at 09:00 must not send the morning's
        alerts twice — that is how a team learns to ignore them."""
        notifier = Notifier(storage)
        signals = [_signal("s1", 90)]
        first = notifier.dispatch(signals, run_id="r1", min_score=75, area_label="H")
        second = notifier.dispatch(signals, run_id="r1", min_score=75, area_label="H")
        assert first["sent"] == 1
        assert second["sent"] == 0
        assert "already notified" in second["reason"]

    def test_a_signal_seen_by_a_later_run_is_not_re_announced(self, storage, sent):
        """Keyed on signal id as well as run id: the nightly scan re-sees yesterday's
        signals, and they are not news twice."""
        notifier = Notifier(storage)
        signals = [_signal("s1", 90)]
        notifier.dispatch(signals, run_id="run-monday", min_score=75, area_label="H")
        second = notifier.dispatch(signals, run_id="run-tuesday", min_score=75, area_label="H")
        assert second["sent"] == 0

    def test_a_genuinely_new_signal_is_announced(self, storage, sent):
        notifier = Notifier(storage)
        notifier.dispatch([_signal("s1", 90)], run_id="r1", min_score=75, area_label="H")
        second = notifier.dispatch(
            [_signal("s1", 90), _signal("s2", 92)], run_id="r2", min_score=75, area_label="H"
        )
        assert second["sent"] == 1
        assert [s.id for s in sent[-1]["signals"]] == ["sig-s2000000"]

    def test_the_ledger_survives_a_new_notifier(self, storage, sent):
        """State lives in S3, not in the process — a container restart must not
        re-announce everything."""
        Notifier(storage).dispatch([_signal("s1", 90)], run_id="r1", min_score=75, area_label="H")
        second = Notifier(storage).dispatch(
            [_signal("s1", 90)], run_id="r2", min_score=75, area_label="H"
        )
        assert second["sent"] == 0

    def test_the_ledger_is_bounded(self, storage, monkeypatch):
        """It must not grow without limit across a long-lived deployment."""
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")
        monkeypatch.setattr("scout.notify._post_webhook", lambda *a, **k: True)
        monkeypatch.setenv("SCOUT_NOTIFY_WEBHOOK_URL", "https://hooks.example/test")
        notifier = Notifier(storage)
        notifier._save_ledger([f"run:{i}" for i in range(20_000)])
        assert len(notifier._load_ledger()) <= 5000


class TestDeliveryFailure:
    def test_a_failed_channel_does_not_mark_signals_as_sent(self, storage, monkeypatch):
        """Otherwise a webhook outage silently swallows the alert forever — the
        ledger would say delivered and no retry would ever happen."""
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")
        monkeypatch.setenv("SCOUT_NOTIFY_WEBHOOK_URL", "https://hooks.example/test")
        monkeypatch.setattr("scout.notify._post_webhook", lambda *a, **k: False)

        notifier = Notifier(storage)
        report = notifier.dispatch([_signal("s1", 90)], run_id="r1", min_score=75, area_label="H")
        assert report["sent"] == 0
        assert notifier._load_ledger() == []

        # And a later attempt can still deliver it.
        monkeypatch.setattr("scout.notify._post_webhook", lambda *a, **k: True)
        retry = notifier.dispatch([_signal("s1", 90)], run_id="r2", min_score=75, area_label="H")
        assert retry["sent"] == 1

    def test_no_configured_channel_is_reported_not_crashed(self, storage, monkeypatch):
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")
        monkeypatch.delenv("SCOUT_NOTIFY_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("SCOUT_SMTP_HOST", raising=False)
        report = Notifier(storage).dispatch(
            [_signal("s1", 90)], run_id="r1", min_score=75, area_label="H"
        )
        assert report["sent"] == 0
        assert "no notification target" in report["reason"]


class TestPayload:
    def test_the_message_carries_a_rationale_and_a_link(self, storage, sent, monkeypatch):
        """The use case asks for "a one-paragraph rationale" with each pushed signal."""
        monkeypatch.setenv("SCOUT_NOTIFY_ENABLED", "true")
        Notifier(storage).dispatch(
            [_signal("s1", 90)], run_id="r1", min_score=75, area_label="Hemophilia"
        )
        body = sent[0]["body"]
        assert "Scored well on area fit." in body
        assert "https://clinicaltrials.gov/study/s1" in body
        assert "Hemophilia" in body


class TestSendTest:
    def test_reports_when_nothing_is_configured(self, monkeypatch):
        monkeypatch.delenv("SCOUT_NOTIFY_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("SCOUT_SMTP_HOST", raising=False)
        result = send_test("hemophilia")
        assert result["configured"] is False
        assert result["delivered"] is False

    def test_reports_delivery(self, monkeypatch):
        """Bypasses the enabled flag and the ledger on purpose — its whole value is
        telling an operator whether delivery works right now."""
        monkeypatch.setenv("SCOUT_NOTIFY_WEBHOOK_URL", "https://hooks.example/test")
        monkeypatch.setattr("scout.notify._post_webhook", lambda *a, **k: True)
        result = send_test("hemophilia")
        assert result["configured"] is True
        assert result["delivered"] is True
