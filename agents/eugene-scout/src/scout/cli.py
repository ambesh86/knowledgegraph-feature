"""One-shot entry points, for running the fetching half somewhere that is not a server.

`scout.api` is a resident service with an APScheduler cron, which is the right
shape on a host that stays up. It is the wrong shape on a VDI or a laptop: those
sleep, reboot, and get logged out, so a daily cron inside a container that is not
running is a schedule that silently never fires.

This module gives the same work a beginning and an end. Point Windows Task
Scheduler, launchd, or a CI job at it and the platform's own scheduler decides
when it runs — a scheduler that survives a reboot, which is the one property the
in-container cron cannot offer on a desktop.

    python -m scout.cli scan                    # every enabled area
    python -m scout.cli scan --areas hematology
    python -m scout.cli digest

Exit codes: 0 success, 1 the run failed, 2 bad arguments. Non-zero on failure is
the point — a scheduled task that always exits 0 reports success while writing
nothing, and no one notices until the data is a month old.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from scout import config as cfg
from scout import digest as digest_builder
from scout import logging_setup
from scout.index import SignalIndex
from scout.models import utcnow
from scout.orchestrator import Orchestrator
from scout.store import Store

logging_setup.configure()
logger = logging.getLogger("scout.cli")


def _scan(args: argparse.Namespace) -> int:
    store = Store()
    orchestrator = Orchestrator(store)

    # Refuse rather than mislead: this binary exists to fetch, and an instance
    # configured as serve-only has been told it has no internet. Running anyway
    # would produce a run record full of connection errors that looks like an
    # outage rather than a misconfiguration.
    if not cfg.scan_enabled():
        logger.error(
            "SCOUT_SCAN_ENABLED=false — this configuration is serve-only. "
            "Run this where outbound internet exists, with SCOUT_SCAN_ENABLED=true."
        )
        return 2

    logger.info(f"one-shot scan starting (bucket={store.s3.bucket})")
    run = orchestrator.run(trigger=args.trigger, areas=args.areas)
    summary = run.summary()

    # Refresh the local index so the summary reflects what a reader would now be
    # served, not what was in memory before the run.
    try:
        SignalIndex(store).refresh()
    except Exception as e:  # noqa: BLE001 - the write already succeeded; this is cosmetic
        logger.warning(f"post-scan index refresh failed: {type(e).__name__}: {e}")

    print(json.dumps(summary, indent=2, default=str))

    # A run that reached zero sources produced nothing, whatever its status says.
    if summary.get("status") == "failed":
        logger.error("scan failed")
        return 1
    logger.info(f"scan complete at {utcnow().isoformat()}")
    return 0


def _digest(args: argparse.Namespace) -> int:
    store = Store()
    today = utcnow().date()
    areas = args.areas or store.known_areas()
    out = {}
    for area_id in areas:
        signals = store.load_signals(area_id)
        companies = store.load_companies(area_id)
        payload = digest_builder.build(area_id, signals, companies)
        store.save_digest(area_id, today, payload)
        out[area_id] = payload["company_count"]
    print(json.dumps({"status": "ok", "areas": out, "date": today.isoformat()}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scout.cli",
        description="Run the Scout fetching half once and exit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="scan every enabled area and write results to S3")
    p_scan.add_argument("--areas", nargs="*", default=None, help="limit to these area ids")
    # ScanRun.trigger is a Literal, so an arbitrary label fails validation at the
    # end of a scan that has already done all its work. Constrain it here.
    p_scan.add_argument(
        "--trigger",
        default="manual",
        choices=["cron", "manual", "startup", "test"],
        help="label recorded on the run (must match ScanRun.trigger)",
    )
    p_scan.set_defaults(func=_scan)

    p_digest = sub.add_parser("digest", help="rebuild the weekly ranked briefing")
    p_digest.add_argument("--areas", nargs="*", default=None)
    p_digest.set_defaults(func=_digest)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001 - a scheduled task needs a non-zero exit, not a traceback
        logger.exception(f"{args.command} failed: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
