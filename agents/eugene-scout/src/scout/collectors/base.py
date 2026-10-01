"""Collector protocol and the shared HTTP client.

Every collector obeys one rule: **it returns a report, it does not raise.** A public
API that 429s, changes shape, or simply goes down must degrade its own column of the
Radar and nothing else. The alternative — one flaky source aborting the run — means a
single upstream outage costs the BD team their entire morning briefing, which is the
opposite of the availability the use case is asking for.

The second rule is that ordering from upstream is never trusted. Europe PMC accepts
`sort=P_PDATE_D desc` and ignores it (verified 2026-08-08: the first result was two
months stale against a corpus of 57k hits — see docs/SOURCE_CONTRACTS.md). So every
collector over-fetches, filters by an absolute date window, and sorts locally. This
is the same conclusion `lib/atlas/intel.ts` and `digest_router.py` already reached;
it is restated here because it is the single easiest thing to get wrong.
"""
from __future__ import annotations

import datetime as dt
import logging
import random
import threading
import time
from typing import Any, Protocol

import requests

from scout import config as cfg
from scout.areas import Area
from scout.config import SourceSettings
from scout.models import RawSignal, SourceId, SourceReport, utcnow

logger = logging.getLogger(__name__)

# Retrying a 4xx other than 429 just burns someone else's rate limit for a request
# that will never succeed. Only these are worth a second attempt.
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class RateLimiter:
    """Process-wide minimum interval between calls to one host.

    SEC asks for <=10 req/s and will block a client that ignores it; NCBI/EBI ask
    for restraint without publishing a hard number. A thread-safe monotonic gate is
    the smallest thing that reliably honours both — and it must be shared across
    collector threads, since the fan-out runs them concurrently.
    """

    def __init__(self, min_interval_s: float) -> None:
        self._min = min_interval_s
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last
            sleep_for = self._min - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last = time.monotonic()


# One limiter per upstream host, shared by every collector that talks to it.
LIMITERS: dict[str, RateLimiter] = {
    "clinicaltrials.gov": RateLimiter(0.20),
    "www.ebi.ac.uk": RateLimiter(0.20),
    "efts.sec.gov": RateLimiter(0.15),  # SEC guidance is <=10 req/s
    "api.uspto.gov": RateLimiter(0.30),  # keyed and quota'd; the most conservative
}


class FetchError(RuntimeError):
    """Upstream could not be read after retries. Caught by the collector, which
    converts it into a failed SourceReport."""


def http_get_json(
    url: str,
    params: dict[str, Any],
    *,
    session: requests.Session | None = None,
    timeout: float | None = None,
    retries: int | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """GET returning parsed JSON, with bounded retry and host rate limiting.

    `headers` adds to (and may override) the defaults — USPTO authenticates with an
    `X-API-KEY` header rather than a query parameter, which keeps the key out of
    request logs and out of the `request_url` we persist in the run manifest.
    """
    timeout = timeout if timeout is not None else cfg.http_timeout_s()
    attempts = retries if retries is not None else cfg.http_retries()
    sess = session or requests
    headers = {"User-Agent": cfg.user_agent(), "Accept": "application/json", **(headers or {})}

    host = url.split("/")[2] if "//" in url else ""
    limiter = LIMITERS.get(host)

    last_error: str = "no attempt made"
    for attempt in range(1, max(1, attempts) + 1):
        if limiter:
            limiter.wait()
        try:
            res = sess.get(url, params=params, headers=headers, timeout=timeout)
            if res.status_code in _RETRY_STATUS:
                last_error = f"HTTP {res.status_code}"
                if attempt < attempts:
                    _backoff(attempt)
                    continue
                raise FetchError(f"{url} -> {last_error} after {attempt} attempts")
            if res.status_code >= 400:
                # Non-retryable. Fail immediately rather than spending the budget.
                raise FetchError(f"{url} -> HTTP {res.status_code}")
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            # A 200 carrying HTML means an upstream error page or a captive portal.
            raise FetchError(f"{url} -> non-JSON response: {e}") from e
        except requests.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < attempts:
                _backoff(attempt)
                continue
            raise FetchError(f"{url} -> {last_error}") from e
    raise FetchError(f"{url} -> {last_error}")


def _backoff(attempt: int) -> None:
    """Exponential backoff with jitter.

    Jitter is not decoration: the four collectors start simultaneously, and without
    it a shared upstream hiccup would resynchronise every retry into the same
    instant and re-trigger the throttle we are backing off from.
    """
    delay = min(8.0, 0.5 * (2 ** (attempt - 1)))
    time.sleep(delay + random.uniform(0, 0.25))


def within_window(published: dt.date | None, window_days: int, today: dt.date) -> bool:
    """Absolute date filter. An item with no parseable date is dropped.

    Dropping undated records is deliberate. The failure this whole module is built
    around was a panel headed "overnight" showing patents granted in 2002; admitting
    an item whose date we cannot establish reopens exactly that hole.
    """
    if published is None:
        return False
    if published > today + dt.timedelta(days=1):
        # Trials legitimately carry future dates (estimated completion). A future
        # *publication* date is upstream data corruption, not news.
        return False
    return (today - published).days <= window_days


def freshest(signals: list[RawSignal], window_days: int, limit: int, today: dt.date) -> list[RawSignal]:
    """Filter to the window, sort locally by date, cap. The order this happens in
    matters: sorting before filtering would still let a stale item through if the
    window is wider than the page we fetched."""
    kept = [s for s in signals if within_window(s.published, window_days, today)]
    kept.sort(key=lambda s: (s.published or dt.date.min), reverse=True)
    return kept[:limit]


class Collector(Protocol):
    """The interface the orchestrator depends on. Four implementations, one shape."""

    source: SourceId

    def collect(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], SourceReport]:
        ...


class BaseCollector:
    """Shared plumbing: timing, error capture, and the never-raise contract.

    Subclasses implement `_fetch`, which may raise freely. This wrapper is what turns
    an exception into a degraded SourceReport, so the guarantee is enforced in one
    place rather than depending on four collectors each remembering to try/except.
    """

    source: SourceId = SourceId.TRIALS  # overridden

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def _fetch(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], str]:
        """Return (signals, request_url). May raise; the caller converts."""
        raise NotImplementedError

    def collect(
        self, area: Area, settings: SourceSettings, today: dt.date
    ) -> tuple[list[RawSignal], SourceReport]:
        started = time.monotonic()
        request_url: str | None = None
        try:
            fetched, request_url = self._fetch(area, settings, today)
            kept = freshest(fetched, settings.window_days, settings.limit_per_area, today)
            report = SourceReport(
                source=self.source,
                area=area.id,
                ok=True,
                fetched=len(fetched),
                kept=len(kept),
                duration_ms=int((time.monotonic() - started) * 1000),
                request_url=request_url,
            )
            logger.info(
                f"{self.source.value}/{area.id}: fetched={len(fetched)} kept={len(kept)} "
                f"window={settings.window_days}d in {report.duration_ms}ms"
            )
            return kept, report
        except Exception as e:  # noqa: BLE001 - the never-raise contract lives here
            logger.warning(f"{self.source.value}/{area.id} failed: {type(e).__name__}: {e}")
            return [], SourceReport(
                source=self.source,
                area=area.id,
                ok=False,
                duration_ms=int((time.monotonic() - started) * 1000),
                error=f"{type(e).__name__}: {e}"[:500],
                request_url=request_url,
            )


__all__ = [
    "BaseCollector",
    "Collector",
    "FetchError",
    "RateLimiter",
    "freshest",
    "http_get_json",
    "utcnow",
    "within_window",
]
