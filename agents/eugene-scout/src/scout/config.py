"""Runtime configuration.

Two tiers, split by who is allowed to change them:

  * **Deployment settings** (bucket, cron time, timeouts) come from the environment.
    Changing them is a deploy.
  * **Scan settings** (scoring weights, thresholds, enabled sources and areas) live in
    a single JSON object in S3. Changing them is a Settings-page edit by the BD team.

That split is the PDF's "configurable thresholds — managed as configuration, not code,
enabling the BD team to tune the system without developer involvement". It is also what
makes the scoring function testable: weights are an argument, not a global.

`ScanConfig` is versioned. Every scored signal records the config version that produced
it, so a score that looks wrong six weeks later can be explained by the weights that
were actually in force at the time rather than the ones in force now.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scout.models import Priority, SourceId, utcnow

# ---------------------------------------------------------------------------
# Deployment settings — environment only
# ---------------------------------------------------------------------------


def bucket() -> str:
    return os.environ.get("SCOUT_S3_BUCKET", "eugene-scout-087084717211")


def region() -> str:
    return os.environ.get("AWS_REGION", "us-east-1")


def s3_endpoint_url() -> str | None:
    """Set to a MinIO/localstack URL to run without touching real S3. Unset in AWS."""
    return os.environ.get("SCOUT_S3_ENDPOINT_URL") or None


def s3_credentials() -> dict[str, str]:
    """Explicit S3 credentials for this service, if it has its own.

    The scanner should authenticate as a least-privilege identity scoped to its own
    bucket, not as the shared `difflabs-website-deployment` user the rest of the stack
    uses — that identity can also read the CSL lakehouse and the neo4j bucket, which a
    service whose whole job is reading four public APIs has no business touching.

    Resolution happens here rather than in docker-compose because compose gets it
    subtly wrong: an `environment:` entry overrides `env_file:`, and `${SCOUT_AWS_*}`
    substitutes from the shell, which never sees docker.env. Mapping it there rendered
    empty strings and blanked the credentials outright. In code the precedence is one
    obvious expression and a unit test can pin it.

    Returns kwargs for `boto3.client`. Empty when SCOUT_AWS_* is unset, which leaves
    boto3 to its normal chain — the shared key from docker.env today, and an instance
    or task role once this runs on AWS, with no code change.
    """
    key_id = os.environ.get("SCOUT_AWS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("SCOUT_AWS_SECRET_ACCESS_KEY", "").strip()
    if key_id and secret:
        return {"aws_access_key_id": key_id, "aws_secret_access_key": secret}
    return {}


def s3_identity_source() -> str:
    """Which identity the service is using, for /health. An operator should be able
    to see whether the scoped credential actually took effect without exec'ing in."""
    return "scoped" if s3_credentials() else "default-chain"


def cron_hour() -> int:
    """Default 02:00 UTC — deliberately AFTER the 01:00 ingestion sweep
    (`INGESTION_HOUR` in docker-compose.yml) so a scan sees the papers that run
    just indexed rather than racing it."""
    return int(os.environ.get("SCOUT_CRON_HOUR", "2"))


def cron_minute() -> int:
    return int(os.environ.get("SCOUT_CRON_MINUTE", "0"))


def timezone() -> str:
    """UTC by default so the schedule does not shift under DST, matching the
    reasoning already applied to `INGESTION_TZ`."""
    return os.environ.get("SCOUT_TZ", "UTC")


def weekly_digest_dow() -> int:
    """Day of week for the ranked partnership briefing. 0 = Monday."""
    return int(os.environ.get("SCOUT_WEEKLY_DIGEST_DOW", "0"))


def http_timeout_s() -> float:
    return float(os.environ.get("SCOUT_HTTP_TIMEOUT_S", "20"))


def http_retries() -> int:
    return int(os.environ.get("SCOUT_HTTP_RETRIES", "3"))


def user_agent() -> str:
    """A descriptive, contact-bearing UA is a hard requirement at SEC and a stated
    courtesy at NCBI/EBI. `agents/eugene-agent-ws/src/query/tools/external_tools.py`
    learned this the hard way — anonymous clients get throttled or blocked."""
    return os.environ.get(
        "SCOUT_USER_AGENT",
        "CSL-Atlas-Scout/1.0 (biomedical BD intelligence; contact: semanticraj@gmail.com)",
    )


def core_api_url() -> str:
    return os.environ.get("EUGENE_CORE_API_URL", "http://eugene_ws:8000")


def notify_enabled() -> bool:
    """Off unless explicitly switched on. A dev box that emails the BD team because
    someone ran `docker compose up` is a one-time mistake with a long memory."""
    return os.environ.get("SCOUT_NOTIFY_ENABLED", "false").lower() == "true"


def notify_webhook_url() -> str | None:
    return os.environ.get("SCOUT_NOTIFY_WEBHOOK_URL") or None


def llm_enabled() -> bool:
    return os.environ.get("SCOUT_LLM_ENABLED", "true").lower() == "true"


def max_workers() -> int:
    """Collector fan-out width. Bounded because four sources × N areas would
    otherwise open dozens of concurrent sockets against public APIs that have
    explicitly asked us not to."""
    return int(os.environ.get("SCOUT_MAX_WORKERS", "4"))


# ---------------------------------------------------------------------------
# Scan settings — S3-backed, BD-team editable
# ---------------------------------------------------------------------------


class ScoringWeights(BaseModel):
    """Relative weight of each scoring factor.

    Weights need not sum to anything in particular; the score is normalised by the
    total weight of the factors that actually applied. That matters because a factor
    can legitimately be unavailable (a literature hit has no development stage), and
    the alternative — scoring it zero — would systematically punish entire sources
    for a property they cannot have.
    """

    model_config = ConfigDict(extra="forbid")

    area_fit: float = Field(default=0.30, ge=0.0, le=1.0)
    stage_fit: float = Field(default=0.20, ge=0.0, le=1.0)
    recency: float = Field(default=0.15, ge=0.0, le=1.0)
    modality_fit: float = Field(default=0.15, ge=0.0, le=1.0)
    corroboration: float = Field(default=0.10, ge=0.0, le=1.0)
    company_context: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _not_all_zero(self) -> Self:
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("at least one scoring weight must be greater than zero")
        return self

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class Thresholds(BaseModel):
    """Score bands. `high` also gates notifications and LLM rationale generation."""

    model_config = ConfigDict(extra="forbid")

    high: float = Field(default=75.0, ge=0.0, le=100.0)
    med: float = Field(default=55.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.high <= self.med:
            raise ValueError(f"high ({self.high}) must exceed med ({self.med})")
        return self

    def priority_for(self, score: float) -> Priority:
        if score >= self.high:
            return Priority.HIGH
        if score >= self.med:
            return Priority.MED
        return Priority.WATCH


class SourceSettings(BaseModel):
    """Per-source enablement and recency window.

    Windows differ by orders of magnitude on purpose. Literature is indexed within
    weeks; patents publish on a grant lag measured in years, so a 45-day patent
    window returns an empty column and a 540-day one returns the actual competitive
    picture. These numbers are ported from `WINDOW_DAYS` in
    agents/eugene-agent-ui-next/lib/atlas/intel.ts.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    window_days: int = Field(default=45, ge=1, le=3650)
    limit_per_area: int = Field(default=25, ge=1, le=200)


DEFAULT_SOURCES: dict[str, SourceSettings] = {
    SourceId.TRIALS.value: SourceSettings(enabled=True, window_days=45, limit_per_area=25),
    SourceId.LITERATURE.value: SourceSettings(enabled=True, window_days=45, limit_per_area=25),
    SourceId.PATENTS.value: SourceSettings(enabled=True, window_days=540, limit_per_area=15),
    SourceId.EDGAR.value: SourceSettings(enabled=True, window_days=90, limit_per_area=20),
    # Ships DISABLED: implemented against EPO's published contract but never
    # confirmed against a live response, because OPS needs an OAuth key. Every
    # other source here was verified first. Enable once credentials are set.
    SourceId.EPO.value: SourceSettings(enabled=False, window_days=540, limit_per_area=15),
}

# CSL's capability set, used by the modality_fit factor. Sourced from the franchises
# named in ingestion/src/pipeline/config/research_areas.yaml (which is itself derived
# from bin/seed/csl_behring_assets.cypher) rather than from generic pharma categories.
DEFAULT_MODALITIES: list[str] = [
    "plasma-derived",
    "plasma derived",
    "recombinant",
    "monoclonal antibody",
    "bispecific",
    "gene therapy",
    "aav",
    "vaccine",
    "immunoglobulin",
    "fusion protein",
    "albumin",
    "c1 esterase inhibitor",
    "factor viii",
    "factor ix",
]

# Development stages ranked by partnership relevance. The PDF's thesis is explicit:
# the opportunity is in companies "raising Series A/B funding or advancing into Phase
# I/II trials" — by Phase III the deal is usually already done, and preclinical is too
# early to act on. So the curve peaks in the middle rather than at the top.
DEFAULT_STAGE_SCORES: dict[str, float] = {
    "EARLY_PHASE1": 0.70,
    "PHASE1": 0.95,
    "PHASE2": 1.00,
    "PHASE3": 0.65,
    "PHASE4": 0.30,
    "NA": 0.40,
    "PRECLINICAL": 0.50,
    # SEC form types: an 8-K is a material event (the interesting case); a registration
    # statement signals a financing round, which is exactly the Series A/B moment.
    "8-K": 0.85,
    "S-1": 0.90,
    "424B4": 0.75,
    "10-K": 0.35,
    "10-Q": 0.30,
}


# Keywords that are real terms in the taxonomy but carry almost no discriminating
# power on their own. Every one of these is here because it was measured letting
# irrelevant records through on a live run:
#
#   * "gene therapy" alone admitted USPTO patents for hearing loss and phenylketonuria
#     into the hemophilia area.
#   * "inhibitor" alone admitted an oncology checkpoint-inhibitor trial.
#   * "augmentation" — a real AATD therapy term — alone admitted USPTO patents from
#     Palo Alto Networks ("automated PROMPT AUGMENTATION") and OPTUM ("authorization
#     request AUGMENTATION") into the alpha-1 antitrypsin area. Found while pulling
#     real data for the stakeholder document, which is exactly the kind of thing a
#     synthetic demo never surfaces.
#
# A record matching ONLY generic terms is topically adjacent, not relevant, and the
# relevance gate drops it. Editable by the BD team, because where that line sits is a
# judgement about their portfolio and not a fact about the code.
DEFAULT_GENERIC_KEYWORDS: list[str] = [
    "gene therapy",
    "inhibitor",
    "prophylaxis",
    "bleeding",
    "anticoagulation",
    "reversal",
    "cholesterol efflux",
    "augmentation",
    "ig",
    "pcc",
]


class ScanConfig(BaseModel):
    """The complete BD-editable configuration. Persisted as one S3 object."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())
    updated_by: str | None = None
    enabled_areas: list[str] = Field(default_factory=list)  # empty = every enabled area
    sources: dict[str, SourceSettings] = Field(default_factory=lambda: dict(DEFAULT_SOURCES))
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    modalities: list[str] = Field(default_factory=lambda: list(DEFAULT_MODALITIES))
    stage_scores: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_STAGE_SCORES))
    notify_min_score: float = Field(default=75.0, ge=0.0, le=100.0)
    generic_keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_GENERIC_KEYWORDS))
    # How many *specific* (non-generic) keywords a record must match to enter the
    # curated tier at all. Zero disables the gate entirely, which is supported but
    # measurably noisy — it is what let a hearing-loss patent into a hemophilia Radar.
    min_specific_matches: int = Field(default=1, ge=0, le=5)

    def specific_keywords(self, keywords: Iterable[str]) -> list[str]:
        """The subset of `keywords` that actually discriminates."""
        generic = {g.lower().strip() for g in self.generic_keywords}
        return [k for k in keywords if k.lower().strip() not in generic]

    def is_relevant(self, matched: Iterable[str]) -> bool:
        """Whether a record clears the relevance gate."""
        if self.min_specific_matches <= 0:
            return True
        return len(self.specific_keywords(matched)) >= self.min_specific_matches

    @model_validator(mode="after")
    def _every_source_known(self) -> Self:
        """Reject a config naming a source no collector implements.

        Without this, a typo in the Settings page silently disables a source: the key
        is written, no collector matches it, and the BD team sees a quieter Radar with
        no error anywhere to explain why.
        """
        known = {s.value for s in SourceId}
        unknown = set(self.sources) - known
        if unknown:
            raise ValueError(f"unknown source(s) in config: {sorted(unknown)}")
        return self

    def source_for(self, source: SourceId) -> SourceSettings:
        return self.sources.get(source.value, DEFAULT_SOURCES[source.value])

    def is_enabled(self, source: SourceId) -> bool:
        return self.source_for(source).enabled

    def bumped(self, updated_by: str | None = None) -> ScanConfig:
        """Return a copy with the version incremented and the timestamp refreshed."""
        return self.model_copy(
            update={
                "version": self.version + 1,
                "updated_at": utcnow().isoformat(),
                "updated_by": updated_by,
            }
        )

    def public(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Split deployment: scanning and serving are separate jobs
# ---------------------------------------------------------------------------
# The scan needs the public internet (ClinicalTrials.gov, Europe PMC, NCBI,
# USPTO, SEC). Serving does not — it reads a curated index from S3. In the CSL
# AWS account an SCP forbids internet gateways, so nothing deployed there can
# scan; but S3 is reachable over a gateway endpoint, so anything there can serve.
#
# That splits one service across two homes: scan where there is internet (a VDI,
# a CI runner, a laptop), serve where there is uptime and shared access (AWS).
# Both point at the same bucket.


def scan_enabled() -> bool:
    """False turns this instance into a read-only server.

    It stops registering the scan and digest crons and refuses /scan, rather than
    letting them fail against an unreachable internet every night and fill the
    logs with errors that look like defects.
    """
    return os.environ.get("SCOUT_SCAN_ENABLED", "true").lower() == "true"


def index_refresh_minutes() -> int:
    """How often a serve-only instance re-reads the curated index from S3.

    Only meaningful when scan_enabled() is false. A scanning instance refreshes
    its own index after each scan, so it has no use for a timer; a serving one
    would otherwise hold whatever it loaded at boot for as long as it stays up,
    quietly serving a snapshot that gets older every hour.

    Ten minutes is well under the daily cadence of the data itself, and the read
    is one small S3 object per area.
    """
    return int(os.environ.get("SCOUT_INDEX_REFRESH_MINUTES", "10"))
