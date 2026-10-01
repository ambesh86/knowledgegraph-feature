"""Notification dispatch — webhook and SMTP.

The use case calls for high-scoring signals to be "pushed to the BD team via email or
Slack with a one-paragraph rationale". Two properties govern this module, and both
exist to protect the recipients rather than the code:

  * **Off by default.** `SCOUT_NOTIFY_ENABLED` defaults to false. A developer running
    `docker compose up` must not be able to message the BD team by accident. That is a
    mistake you make once and are reminded of for a year.

  * **Idempotent.** Dispatch is keyed on (run_id, signal_id) and the sent keys are
    persisted to S3. A retried or re-run scan re-notifies nobody. Without this, one
    operator re-running a failed job at 09:00 sends the morning's alerts twice, and the
    team learns to ignore them.

Failure to notify never fails a scan. The signals are already durably in S3 and
visible in the UI; a Slack outage is not a reason to mark the night's intelligence as
failed.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Any

from scout import config as cfg
from scout.models import Signal
from scout.storage import Storage

logger = logging.getLogger(__name__)

_SENT_KEY = "runs/_notified.json"
# Bounded so the dedup ledger cannot grow without limit. Well above one run's worth of
# notifications, so nothing is forgotten before it stops being relevant.
_MAX_LEDGER = 5000

_TIMEOUT_S = 10.0


class Notifier:
    def __init__(self, storage: Storage | None = None) -> None:
        self.s3 = storage or Storage()

    # -- ledger ------------------------------------------------------------

    def _load_ledger(self) -> list[str]:
        value = self.s3.get_json_or(_SENT_KEY, [])
        return value if isinstance(value, list) else []

    def _save_ledger(self, keys: list[str]) -> None:
        self.s3.put_json(_SENT_KEY, keys[-_MAX_LEDGER:])

    # -- dispatch ----------------------------------------------------------

    def dispatch(
        self,
        signals: list[Signal],
        *,
        run_id: str,
        min_score: float,
        area_label: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Send alerts for signals at or above `min_score`.

        Returns a report rather than raising, so the caller can record what happened
        in the run manifest either way.
        """
        if not cfg.notify_enabled() and not force:
            return {"sent": 0, "skipped": len(signals), "reason": "notifications disabled"}

        candidates = [
            s for s in signals
            if s.score >= min_score and not s.dismissed and s.priority.value == "high"
        ]
        if not candidates:
            return {"sent": 0, "skipped": 0, "reason": "no signals above threshold"}

        ledger = self._load_ledger()
        seen = set(ledger)
        fresh = [s for s in candidates if f"{run_id}:{s.id}" not in seen]
        # Keyed on signal id alone as well as run id: a signal already announced by an
        # earlier run should not be announced again just because a later run re-saw it.
        already = {k.split(":", 1)[1] for k in ledger if ":" in k}
        fresh = [s for s in fresh if s.id not in already]

        if not fresh:
            return {"sent": 0, "skipped": len(candidates), "reason": "all already notified"}

        body = _render(fresh, area_label=area_label)
        results: dict[str, Any] = {"webhook": None, "email": None}

        webhook = cfg.notify_webhook_url()
        if webhook:
            results["webhook"] = _post_webhook(webhook, body, fresh, area_label)

        if _smtp_configured():
            results["email"] = _send_email(body, area_label, len(fresh))

        if not webhook and not _smtp_configured():
            return {"sent": 0, "skipped": len(fresh), "reason": "no notification target configured"}

        delivered = any(v is True for v in results.values())
        if delivered:
            self._save_ledger(ledger + [f"{run_id}:{s.id}" for s in fresh])

        return {
            "sent": len(fresh) if delivered else 0,
            "skipped": len(candidates) - len(fresh),
            "channels": results,
            "reason": None if delivered else "all channels failed",
        }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render(signals: list[Signal], *, area_label: str) -> str:
    """One paragraph per signal, as the use case specifies."""
    lines = [f"*{len(signals)} high-priority signal(s) — {area_label}*", ""]
    for s in signals:
        company = f"{s.company_name} · " if s.company_name else ""
        published = s.published.isoformat() if s.published else "date unknown"
        lines += [
            f"• *{s.title}*",
            f"  {company}{s.type.value} · score {s.score:.0f}/100 · {published}",
            f"  {s.rationale or s.summary[:200]}",
            f"  {s.primary_url}",
            "",
        ]
    return "\n".join(lines)


def _post_webhook(url: str, body: str, signals: list[Signal], area_label: str) -> bool:
    """POST a Slack-compatible payload.

    `text` is what Slack renders; the structured fields alongside it let any other
    consumer (Teams, a Lambda, a log sink) act on the data without parsing prose.
    """
    payload = {
        "text": body,
        "area": area_label,
        "signal_count": len(signals),
        "signals": [
            {
                "id": s.id,
                "title": s.title,
                "company": s.company_name,
                "score": s.score,
                "priority": s.priority.value,
                "type": s.type.value,
                "url": s.primary_url,
                "rationale": s.rationale,
            }
            for s in signals
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": cfg.user_agent()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            ok = 200 <= response.status < 300
            if not ok:
                logger.warning(f"webhook returned HTTP {response.status}")
            return ok
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        logger.warning(f"webhook delivery failed: {type(e).__name__}: {e}")
        return False


def _smtp_configured() -> bool:
    return bool(os.environ.get("SCOUT_SMTP_HOST") and os.environ.get("SCOUT_NOTIFY_EMAIL_TO"))


def _send_email(body: str, area_label: str, count: int) -> bool:
    host = os.environ.get("SCOUT_SMTP_HOST", "")
    port = int(os.environ.get("SCOUT_SMTP_PORT", "587"))
    user = os.environ.get("SCOUT_SMTP_USER") or None
    password = os.environ.get("SCOUT_SMTP_PASSWORD") or None
    sender = os.environ.get("SCOUT_NOTIFY_EMAIL_FROM", "eugene-scout@csl.local")
    recipients = [
        r.strip() for r in os.environ.get("SCOUT_NOTIFY_EMAIL_TO", "").split(",") if r.strip()
    ]
    if not host or not recipients:
        return False

    message = EmailMessage()
    message["Subject"] = f"[CSL Atlas] {count} high-priority signal(s) — {area_label}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=_TIMEOUT_S) as smtp:
            # STARTTLS where offered. Not mandatory because a compose-internal relay
            # on a private network legitimately has no certificate.
            if smtp.has_extn("starttls"):
                smtp.starttls()
                smtp.ehlo()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        logger.warning(f"email delivery failed: {type(e).__name__}: {e}")
        return False


def send_test(area_label: str = "test") -> dict[str, Any]:
    """Verify a notification target without waiting for a scan.

    Bypasses the enabled flag and the ledger on purpose: this is an explicit,
    interactive action from the Settings page, and its whole value is telling the
    operator whether delivery works right now.
    """
    body = (
        "*CSL Atlas — Eugene Scout test notification*\n\n"
        "If you are reading this, the configured notification channel is working.\n"
        "No signals are included; this message was triggered manually from Settings."
    )
    results: dict[str, Any] = {"webhook": None, "email": None}
    webhook = cfg.notify_webhook_url()
    if webhook:
        results["webhook"] = _post_webhook(webhook, body, [], area_label)
    if _smtp_configured():
        results["email"] = _send_email(body, area_label, 0)
    configured = webhook is not None or _smtp_configured()
    return {
        "configured": configured,
        "delivered": any(v is True for v in results.values()),
        "channels": results,
    }
