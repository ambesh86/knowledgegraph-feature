"""S3 storage adapter for ADE artifacts.

Every artifact this service produces is addressed by exactly one key layout, and
that layout is built here and nowhere else. Scattering `f"documents/{id}/..."`
across modules is how storage layouts silently drift between the writer and the
reader — and the reader in this system is an evidence viewer that must be able to
find the exact bytes an answer was derived from, months later.

Raw botocore exceptions never escape this module: callers get `StorageError`.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Any failure talking to object storage."""


# ---------------------------------------------------------------------------
# Key layout — the single source of truth
# ---------------------------------------------------------------------------
def key_pdf(doc_id: str) -> str:
    return f"documents/{doc_id}/source.pdf"


def key_manifest(doc_id: str) -> str:
    return f"documents/{doc_id}/document.json"


def key_markdown(doc_id: str) -> str:
    return f"documents/{doc_id}/parse.md"


def key_chunks(doc_id: str) -> str:
    return f"documents/{doc_id}/chunks.json"


def key_grounding(doc_id: str) -> str:
    return f"documents/{doc_id}/grounding.json"


def key_render(doc_id: str, chunk_id: str, dpi: int) -> str:
    return f"documents/{doc_id}/renders/{chunk_id}@{dpi}.png"


class Storage:
    """Thin, typed wrapper over the S3 operations this service needs."""

    def __init__(self, bucket: str | None = None, region: str | None = None) -> None:
        self.bucket = bucket or os.environ.get("ADE_S3_BUCKET", "")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        if not self.bucket:
            raise StorageError("ADE_S3_BUCKET is not set")
        self._client = boto3.client("s3", region_name=self.region)

    # -- primitives --------------------------------------------------------
    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        try:
            self._client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"put s3://{self.bucket}/{key} failed: {e}") from e
        return f"s3://{self.bucket}/{key}"

    def get_bytes(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"get s3://{self.bucket}/{key} failed: {e}") from e

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            # 404/NoSuchKey is a normal answer, not a failure.
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise StorageError(f"head s3://{self.bucket}/{key} failed: {e}") from e
        except BotoCoreError as e:
            raise StorageError(f"head s3://{self.bucket}/{key} failed: {e}") from e

    # -- json convenience --------------------------------------------------
    def put_json(self, key: str, obj: Any) -> str:
        return self.put_bytes(
            key, json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json",
        )

    def get_json(self, key: str) -> Any:
        return json.loads(self.get_bytes(key).decode("utf-8"))

    def presign(self, key: str, ttl_s: int = 3600) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl_s,
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"presign s3://{self.bucket}/{key} failed: {e}") from e

    def health(self) -> dict[str, Any]:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return {"ok": True, "bucket": self.bucket, "region": self.region}
        except Exception as e:  # surfaced, not raised — health must not 500
            return {"ok": False, "bucket": self.bucket, "error": str(e)[:200]}


_instance: Storage | None = None


def storage() -> Storage:
    global _instance
    if _instance is None:
        _instance = Storage()
    return _instance
