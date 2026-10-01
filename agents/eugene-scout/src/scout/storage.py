"""S3 object storage — the only database this service has.

There is no Postgres here by design. The signal corpus is small (low thousands of
rows), read-mostly, and rebuilt wholesale by each scan, which is precisely the shape
S3 serves well and a relational store buys nothing for. What we would have gained
from Postgres — ad-hoc filtering — is instead provided by an in-memory index
(`index.py`) rehydrated from a single curated object.

Two tiers, and the split is the point:

  * `raw/`     STAGING. Untouched upstream payloads, exactly as fetched, partitioned
               by date/run/source. Write-once. This is what makes a scoring change
               replayable over history instead of requiring a fresh crawl of four
               public APIs — and what lets an analyst answer "what did we actually
               see on the 3rd?" months later.
  * `curated/` FINAL. Scored, deduped signals and company scores, plus a per-area
               index object the API serves from. Rewritten by each scan; versioning
               is enabled on the bucket so the previous generation is recoverable.

The key layout is built here and nowhere else. Scattering f-string keys across modules
is how the writer and the reader drift apart — a lesson already paid for in
agents/eugene-ade/src/ade/storage.py, whose structure this mirrors deliberately so
there is one storage idiom in the codebase rather than two.

Raw botocore exceptions never escape this module; callers get `StorageError`.
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import logging
from typing import Any, Iterable, Iterator

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from scout import config as cfg

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Any failure talking to object storage."""


class NotFound(StorageError):
    """The requested key does not exist. Distinct from a transport failure because
    'no scan has run yet' is a normal cold-start state the API must render as an
    empty Radar, not as an outage."""


# ---------------------------------------------------------------------------
# Key layout — single source of truth
# ---------------------------------------------------------------------------

_CONFIG_KEY = "config/scan_config.json"
_LATEST_RUN_KEY = "runs/latest.json"


def key_raw(run_id: str, area: str, source: str, day: dt.date) -> str:
    """Staging partition. Hive-style `dt=`/`area=`/`source=` so the same layout can
    later be crawled by Glue or queried by Athena without a migration — the lakehouse
    door is left open even though we are not walking through it today."""
    return f"raw/dt={day.isoformat()}/run={run_id}/area={area}/source={source}/records.jsonl.gz"


def key_curated_signals(area: str) -> str:
    return f"curated/signals/area={area}/signals.jsonl.gz"


def key_curated_companies(area: str) -> str:
    return f"curated/companies/area={area}/companies.jsonl.gz"


def key_curated_index(area: str) -> str:
    """The object the serving layer loads into memory. One per area, small enough to
    fetch in a single GET and cheap enough to reload after every scan."""
    return f"curated/index/area={area}/index.json"


def key_area_manifest() -> str:
    """Which areas have curated data. Read at boot so the index knows what to load
    without a LIST call against a versioned bucket (where LIST also returns the
    delete markers and stale versions we do not want)."""
    return "curated/index/_areas.json"


def key_snapshot(area: str, day: dt.date) -> str:
    """Immutable daily copy of the curated tier.

    Curated objects are overwritten by each scan. Bucket versioning technically
    retains the old bytes, but recovering a specific day through version history is
    awkward and the lifecycle rule expires non-current versions at 90 days. An
    explicit dated snapshot is what the 30-day company score delta is computed
    against, so it needs to be addressable by date, not by version id.
    """
    return f"curated/snapshots/area={area}/dt={day.isoformat()}/signals.jsonl.gz"


def key_run(run_id: str) -> str:
    return f"runs/{run_id}/manifest.json"


def key_digest(area: str, day: dt.date) -> str:
    return f"curated/digests/area={area}/dt={day.isoformat()}/digest.json"


def key_dd_brief(target_id: str) -> str:
    """Latest due-diligence brief for a target.

    Overwritten per target rather than accumulating per run: an analyst asks "what do
    we know about this company", not "what did we know on the 14th". The dated copy
    below is what preserves history, so nothing is lost by keeping this address stable
    and therefore linkable.
    """
    return f"curated/duediligence/target={target_id}/brief.json"


def key_dd_brief_dated(target_id: str, day: dt.date) -> str:
    """Immutable dated copy.

    Diligence is a decision record. When someone asks in six months why a partnership
    was progressed, the brief as it read that day is the answer, and an overwritten
    object cannot provide it.
    """
    return f"curated/duediligence/target={target_id}/dt={day.isoformat()}/brief.json"


def key_dd_index() -> str:
    """Which targets have briefs, newest first. Read to list without a LIST call
    against a versioned bucket, matching the reasoning behind key_area_manifest."""
    return "curated/duediligence/_targets.json"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Storage:
    """Typed wrapper over the handful of S3 operations this service performs."""

    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket or cfg.bucket()
        self.region = region or cfg.region()
        if not self.bucket:
            raise StorageError("SCOUT_S3_BUCKET is not set")
        # Adaptive retries rather than the default 'legacy' mode: a nightly scan that
        # writes a few hundred objects will occasionally meet S3 throttling, and the
        # adaptive mode backs off on the client side instead of surfacing a 503.
        self._client = client or boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=cfg.s3_endpoint_url(),
            # Prefers this service's own scoped identity when one is configured;
            # otherwise falls through to boto3's normal chain (shared key locally,
            # instance/task role on AWS). See config.s3_credentials().
            **cfg.s3_credentials(),
            config=BotoConfig(retries={"max_attempts": 5, "mode": "adaptive"}),
        )

    # -- primitives --------------------------------------------------------

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        try:
            self._client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
            )
        except (BotoCoreError, ClientError) as e:
            raise StorageError(f"put {key} failed: {e}") from e
        logger.debug(f"put s3://{self.bucket}/{key} ({len(data)} bytes)")
        return f"s3://{self.bucket}/{key}"

    def get_bytes(self, key: str) -> bytes:
        try:
            res = self._client.get_object(Bucket=self.bucket, Key=key)
            return res["Body"].read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NoSuchBucket"):
                raise NotFound(key) from e
            raise StorageError(f"get {key} failed: {e}") from e
        except BotoCoreError as e:
            raise StorageError(f"get {key} failed: {e}") from e

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
        except BotoCoreError as e:
            raise StorageError(f"head {key} failed: {e}") from e

    def health(self) -> bool:
        """Cheap reachability probe used by /health. HEAD on the bucket, not a LIST:
        a LIST on a bucket with many versions is neither cheap nor constant-time."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"s3 health check failed: {e}")
            return False

    # -- JSON / JSONL ------------------------------------------------------

    def put_json(self, key: str, obj: Any) -> str:
        body = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=_encode).encode()
        return self.put_bytes(key, body, "application/json")

    def get_json(self, key: str) -> Any:
        return json.loads(self.get_bytes(key).decode("utf-8"))

    def get_json_or(self, key: str, default: Any) -> Any:
        """Read-or-default. Cold start is a normal state, not an error: before the
        first scan there is no index, and the API must answer with an empty Radar."""
        try:
            return self.get_json(key)
        except NotFound:
            return default

    def put_jsonl_gz(self, key: str, rows: Iterable[Any]) -> tuple[str, int]:
        """Write newline-delimited JSON, gzipped. Returns (uri, row_count).

        JSONL rather than one big JSON array so the objects stay streamable and
        Athena-readable, and gzip because these are highly repetitive text records —
        measured ~8x on signal payloads, which matters for the raw tier where we keep
        every field the upstream sent.
        """
        buf = io.BytesIO()
        count = 0
        # mtime=0 keeps the output byte-identical for identical input, which is what
        # lets a test assert on content without the timestamp making every run differ.
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
            for row in rows:
                line = json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=_encode)
                gz.write(line.encode("utf-8"))
                gz.write(b"\n")
                count += 1
        return self.put_bytes(key, buf.getvalue(), "application/gzip"), count

    def get_jsonl_gz(self, key: str) -> Iterator[dict[str, Any]]:
        raw = self.get_bytes(key)
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as gz:
            for line in gz:
                line = line.strip()
                if line:
                    yield json.loads(line.decode("utf-8"))

    def get_jsonl_gz_or_empty(self, key: str) -> list[dict[str, Any]]:
        try:
            return list(self.get_jsonl_gz(key))
        except NotFound:
            return []

    # -- domain-level accessors -------------------------------------------

    def load_config_raw(self) -> dict[str, Any] | None:
        try:
            return self.get_json(_CONFIG_KEY)
        except NotFound:
            return None

    def save_config_raw(self, payload: dict[str, Any]) -> str:
        return self.put_json(_CONFIG_KEY, payload)

    def load_area_manifest(self) -> list[str]:
        return self.get_json_or(key_area_manifest(), [])

    def save_area_manifest(self, areas: list[str]) -> str:
        return self.put_json(key_area_manifest(), sorted(set(areas)))

    def save_latest_run(self, summary: dict[str, Any]) -> str:
        return self.put_json(_LATEST_RUN_KEY, summary)

    def load_latest_run(self) -> dict[str, Any] | None:
        return self.get_json_or(_LATEST_RUN_KEY, None)

    def list_run_ids(self, limit: int = 20) -> list[str]:
        """Most recent run ids. Run ids are timestamp-prefixed, so lexical order is
        chronological order and a plain prefix listing suffices."""
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            keys: list[str] = []
            for page in paginator.paginate(
                Bucket=self.bucket, Prefix="runs/", Delimiter="/", PaginationConfig={"MaxItems": 2000}
            ):
                for p in page.get("CommonPrefixes", []) or []:
                    keys.append(p["Prefix"].removeprefix("runs/").rstrip("/"))
            return sorted(keys, reverse=True)[:limit]
        except (BotoCoreError, ClientError) as e:
            raise StorageError(f"listing runs failed: {e}") from e


def _encode(obj: Any) -> Any:
    """JSON fallback for the types our models legitimately hold."""
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"not JSON-serialisable: {type(obj).__name__}")
