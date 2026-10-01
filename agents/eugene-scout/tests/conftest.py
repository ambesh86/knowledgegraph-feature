"""Shared fixtures.

Every test in this suite is hermetic: no network, no real S3, no real clock where a
clock would make an assertion flap. `moto` provides an in-process S3 so the storage
layer is exercised for real — mocking `Storage` itself would leave the key layout, the
gzip round-trip and the JSONL encoding untested, which is precisely the code most
likely to break silently.

`FROZEN_TODAY` is fixed rather than `date.today()`. Recency is a scoring input, so a
suite that used the real date would produce different scores every day and its
assertions would rot.
"""
from __future__ import annotations

import datetime as dt
import os

import pytest

# Must be set before boto3/moto import, otherwise botocore may pick up a real profile
# from the developer's machine and the "hermetic" suite quietly talks to AWS.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("SCOUT_S3_BUCKET", "test-scout-bucket")
os.environ.setdefault("SCOUT_LLM_ENABLED", "false")
os.environ.setdefault("SCOUT_NOTIFY_ENABLED", "false")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from scout.areas import Area  # noqa: E402
from scout.config import ScanConfig  # noqa: E402
from scout.models import RawSignal, SourceId  # noqa: E402
from scout.storage import Storage  # noqa: E402
from scout.store import Store  # noqa: E402

FROZEN_TODAY = dt.date(2026, 8, 8)
FROZEN_NOW = dt.datetime(2026, 8, 8, 12, 0, 0, tzinfo=dt.UTC)
BUCKET = "test-scout-bucket"


@pytest.fixture
def aws():
    """In-process S3 for the duration of one test."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture
def storage(aws) -> Storage:
    return Storage(bucket=BUCKET, region="us-east-1")


@pytest.fixture
def store(storage) -> Store:
    return Store(storage)


@pytest.fixture
def config() -> ScanConfig:
    return ScanConfig()


@pytest.fixture
def area() -> Area:
    """A stand-in for the hemophilia area, defined inline rather than loaded from the
    real YAML so a taxonomy edit cannot silently change what the scoring tests mean."""
    return Area(
        {
            "id": "hemophilia",
            "label": "Hemophilia A & B",
            "enabled": True,
            "queries": {
                "literature": "hemophilia AND (factor VIII OR factor IX)",
                "trials_condition": "hemophilia A OR hemophilia B",
                "trials_intervention": "factor VIII OR emicizumab",
            },
            "keywords": [
                "hemophilia", "factor viii", "factor ix", "emicizumab",
                "gene therapy", "inhibitor", "hemgenix",
            ],
        }
    )


# Distinguishes "caller omitted published" from "caller explicitly said undated".
# Using None for both made it impossible to build an undated signal, which silently
# turned the undated-recency test into a no-op.
_UNSET = object()


def make_signal(
    *,
    source: SourceId = SourceId.TRIALS,
    external_id: str = "NCT00000001",
    title: str = "A Phase 2 Study of Factor VIII in Hemophilia A",
    summary: str = "Recombinant factor VIII prophylaxis in severe hemophilia A.",
    published: dt.date | None | object = _UNSET,
    company_name: str | None = "Acme Biotherapeutics, Inc.",
    stage: str | None = "PHASE2",
    keywords: tuple[str, ...] = ("hemophilia", "factor viii"),
    url: str = "https://clinicaltrials.gov/study/NCT00000001",
    payload: dict | None = None,
) -> RawSignal:
    """Builder for a realistic RawSignal. Defaults describe a strong, relevant signal
    so tests can vary one property at a time and attribute any score change to it."""
    return RawSignal(
        source=source,
        external_id=external_id,
        title=title,
        summary=summary,
        url=url,
        published=(FROZEN_TODAY - dt.timedelta(days=3)) if published is _UNSET else published,  # type: ignore[arg-type]
        company_name=company_name,
        stage=stage,
        keywords=keywords,
        payload=payload or {},
    )
