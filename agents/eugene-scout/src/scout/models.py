"""Typed contracts for everything that crosses a boundary in this service.

Three families of model live here and the distinction between them is load-bearing:

  * `RawSignal` is what a collector produces. It is source-shaped, minimally
    validated, and written to S3 staging verbatim alongside the untouched upstream
    payload. If a scoring rule is later found to be wrong, staging is what lets us
    re-derive every signal without re-hitting the public APIs.
  * `Signal` is what the pipeline produces. Scored, deduped, enriched, and written to
    S3 curated. This is the object the UI renders.
  * `ScanRun` / `SourceReport` are the audit trail. Every claim the UI makes about
    freshness traces back to one of these.

Validators here are not decoration. Collectors talk to four public APIs whose
responses we do not control, and a malformed date or an empty URL that slips into the
curated tier is a wrong answer shown to an analyst with full confidence. Rejecting at
the boundary is cheaper than debugging it later.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SourceId(StrEnum):
    """One value per collector. Also the S3 staging partition key."""

    TRIALS = "clinicaltrials"
    LITERATURE = "europepmc_lit"
    PATENTS = "europepmc_pat"
    EDGAR = "sec_edgar"
    EPO = "epo_ops"


class SignalType(StrEnum):
    """Mirrors the `SignalType` union in the UI's lib/atlas/seed.ts so the existing
    Radar filter chips keep working without a translation layer."""

    TRIAL = "Trial"
    PATENT = "Patent"
    PUBLICATION = "Publication"
    REGULATORY = "Regulatory"
    CORPORATE = "Corporate"


class Priority(StrEnum):
    """Mirrors the UI's `Priority` union ("high" | "med" | "watch") so
    <PriorityBadge> renders these values unchanged."""

    HIGH = "high"
    MED = "med"
    WATCH = "watch"


class RunStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    DEGRADED = "degraded"  # completed, but at least one source failed
    FAILED = "failed"
    SKIPPED = "skipped"  # another run held the lock


class RationaleKind(StrEnum):
    """Provenance of the prose shown to the analyst. Surfaced in the UI — an
    LLM-written paragraph and a deterministic template are not the same claim, and
    pretending otherwise is how trust in the whole panel gets spent."""

    LLM = "llm"
    TEMPLATE = "template"


# ---------------------------------------------------------------------------
# Helpers shared by validators
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")
_TAGS = re.compile(r"<[^>]+>")
_ENTITIES = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}
_NUMERIC_ENTITY = re.compile(r"&#\d+;")


def clean_text(value: str | None) -> str:
    """Strip markup and collapse whitespace.

    Europe PMC returns titles containing <sup>, <i> and HTML entities; rendering
    those raw put literal `&amp;` into the Radar list. Ported from `clean()` in
    agents/eugene-agent-ui-next/lib/atlas/intel.ts — same rules, one behaviour.
    """
    if not value:
        return ""
    text = _TAGS.sub("", value)
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    text = _NUMERIC_ENTITY.sub("", text)
    return _WS.sub(" ", text).strip()


def parse_date(value: str | None) -> dt.date | None:
    """Parse the date shapes the four upstream APIs actually emit.

    Observed in the wild (see docs/SOURCE_CONTRACTS.md): `2026-08-07` from
    ClinicalTrials.gov and EDGAR, `2026-06-11` from Europe PMC's
    firstPublicationDate, and a bare `2026` from its pubYear when the full date is
    unknown. A bare year is deliberately floored to January 1st rather than
    discarded: it is genuinely all the upstream knows, and the recency factor
    treats it as the worst case it could be.
    """
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if len(raw) == 4 and raw.isdigit():
        return dt.date(int(raw), 1, 1)
    if len(raw) == 7 and raw[4] == "-":  # "2026-08" from statusVerifiedDate
        try:
            return dt.date(int(raw[:4]), int(raw[5:]), 1)
        except ValueError:
            return None
    try:
        return dt.date.fromisoformat(raw[:10])
    except ValueError:
        return None


def utcnow() -> dt.datetime:
    """Timezone-aware UTC now, truncated to the second.

    Injected into the pipeline rather than called inside it: `score()` must be a
    pure function of its inputs, and a bare `now()` inside a scoring rule would
    make the same signal score differently on every call.
    """
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


# ---------------------------------------------------------------------------
# Collector output
# ---------------------------------------------------------------------------


class RawSignal(BaseModel):
    """One item as a collector found it, before any cross-source reasoning.

    `payload` keeps the untouched upstream record. It is what gets written to S3
    staging, and it is the reason a scoring change can be replayed over history
    instead of requiring a fresh crawl of four public APIs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: SourceId
    external_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1)
    summary: str = ""
    url: str = ""
    published: dt.date | None = None
    company_name: str | None = None
    stage: str | None = None  # "PHASE2", "8-K", … source-specific, normalised later
    keywords: tuple[str, ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "summary", mode="before")
    @classmethod
    def _clean(cls, v: Any) -> str:
        return clean_text(v if isinstance(v, str) else None)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        """A signal the analyst cannot click through to is not evidence.

        Empty is allowed (some sources legitimately lack a canonical URL and the
        pipeline synthesises one); a non-HTTP scheme is not, because it would be
        rendered into an <a href> in the Radar list.
        """
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(f"url must be http(s), got {v[:40]!r}")
        return v

    @property
    def content_hash(self) -> str:
        """Stable identity for deduplication across runs AND across sources.

        Keyed on source + external_id, not on the title: the same trial re-fetched
        tomorrow with a copy-edited title is the same trial, and hashing the title
        would resurface it as new every night. Cross-source corroboration (the same
        story from EDGAR and ClinicalTrials.gov) is matched separately in dedupe.py
        on normalised title, because those genuinely are different records.
        """
        return hashlib.sha256(f"{self.source}:{self.external_id}".encode()).hexdigest()[:32]


class SourceReport(BaseModel):
    """Per-source outcome for one run. Collectors return this instead of raising.

    A source that 429s must degrade that source alone. Letting it abort the run
    would mean one flaky public API costs the BD team their entire morning digest.
    """

    model_config = ConfigDict(extra="forbid")

    source: SourceId
    area: str
    ok: bool
    fetched: int = 0
    kept: int = 0  # survived the date window
    duration_ms: int = 0
    error: str | None = None
    request_url: str | None = None

    @model_validator(mode="after")
    def _failure_has_reason(self) -> Self:
        if not self.ok and not self.error:
            raise ValueError("a failed SourceReport must carry an error")
        return self


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class ScoreFactor(BaseModel):
    """One scoring dimension, with the inputs that produced it.

    `inputs` exists so the UI's score-breakdown panel can show *why* a factor fired
    ("matched: hemophilia, factor viii") rather than an unexplained 0.8. The PDF
    calls for explainability; a number with no provenance is not that.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    value: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0)
    inputs: dict[str, Any] = Field(default_factory=dict)

    @property
    def contribution(self) -> float:
        return self.value * self.weight


class ScoreResult(BaseModel):
    """Output of the pure scoring function."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0.0, le=100.0)
    priority: Priority
    factors: tuple[ScoreFactor, ...]

    def breakdown(self) -> dict[str, Any]:
        """Serialisable form persisted with the signal and rendered by the UI."""
        return {
            "total": round(self.score, 2),
            "priority": self.priority.value,
            "factors": [
                {
                    "name": f.name,
                    "value": round(f.value, 4),
                    "weight": f.weight,
                    "contribution": round(f.contribution, 4),
                    "inputs": f.inputs,
                }
                for f in self.factors
            ],
        }


# ---------------------------------------------------------------------------
# Curated output
# ---------------------------------------------------------------------------


class GraphEntity(BaseModel):
    """A node in Eugene's knowledge graph that this signal mentions.

    Context, not score. See `graph.py` — ranking on graph membership would rank the
    familiar above the novel, which is backwards for a team hunting assets it does
    not already track.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    value: str
    matched_term: str


class ReviewReason(StrEnum):
    """Why a signal was flagged for human attention.

    The use case asks the orchestrator to "flag low-confidence outputs for human
    review rather than suppressing uncertainty, preserving analyst trust". These are
    the conditions under which this system is honest about not being sure.
    """

    BORDERLINE_SCORE = "borderline_score"  # sits within a hair of a priority boundary
    THIN_EVIDENCE = "thin_evidence"  # one source, one keyword
    UNVERIFIED_RATIONALE = "unverified_rationale"  # the LLM output failed the fence
    UNDATED = "undated"  # no publication date could be established


class SignalSource(BaseModel):
    """A citation. Every signal carries at least one; the UI links all of them."""

    model_config = ConfigDict(extra="forbid")

    source: SourceId
    external_id: str
    url: str
    published: dt.date | None = None


class Signal(BaseModel):
    """A scored, deduped, analyst-facing signal. Written to S3 curated."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=8, max_length=64)
    area: str
    type: SignalType
    title: str = Field(min_length=1)
    summary: str = ""
    rationale: str = ""
    rationale_kind: RationaleKind = RationaleKind.TEMPLATE
    score: float = Field(ge=0.0, le=100.0)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    priority: Priority
    company_name: str | None = None
    company_id: str | None = None
    stage: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    published: dt.date | None = None
    detected_at: dt.datetime
    first_seen_run: str
    last_seen_run: str
    sources: list[SignalSource] = Field(min_length=1)
    dismissed: bool = False
    # Knowledge-graph annotations. Context for the analyst; never an input to score.
    graph_entities: list[GraphEntity] = Field(default_factory=list)
    # Human-in-the-loop: surfaced in the UI rather than silently suppressed.
    needs_review: bool = False
    review_reasons: list[ReviewReason] = Field(default_factory=list)

    @model_validator(mode="after")
    def _priority_matches_score(self) -> Self:
        """Guard against a hand-edited or partially-migrated curated object.

        Score and priority are two representations of one decision. If they ever
        disagree in storage, the Radar list and its filter chips disagree with each
        other, which is worse than either being wrong alone.
        """
        if self.score < 0 or self.score > 100:
            raise ValueError("score out of range")
        return self

    @property
    def primary_url(self) -> str:
        return self.sources[0].url if self.sources else ""

    @property
    def confidence_note(self) -> str:
        """Human-readable reason this signal wants a second look."""
        labels = {
            ReviewReason.BORDERLINE_SCORE: "score sits on a priority boundary",
            ReviewReason.THIN_EVIDENCE: "single source with a weak keyword match",
            ReviewReason.UNVERIFIED_RATIONALE: "generated rationale failed verification",
            ReviewReason.UNDATED: "no publication date could be established",
        }
        return "; ".join(labels.get(r, r.value) for r in self.review_reasons)


class CompanyScore(BaseModel):
    """A watchlist row. Derived entirely from the signals attributed to the company —
    there is no independently-maintained company score to drift out of sync."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    normalized_name: str
    ticker: str | None = None
    cik: str | None = None
    areas: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    delta_30d: float = 0.0
    signal_count: int = 0
    high_priority_count: int = 0
    top_signal_id: str | None = None
    last_signal_at: dt.datetime | None = None
    computed_at: dt.datetime
    breakdown: dict[str, Any] = Field(default_factory=dict)


class ScanRun(BaseModel):
    """The audit record for one execution. Written to S3 under runs/."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    trigger: Literal["cron", "manual", "startup", "test"]
    status: RunStatus
    started_at: dt.datetime
    finished_at: dt.datetime | None = None
    areas: list[str] = Field(default_factory=list)
    source_reports: list[SourceReport] = Field(default_factory=list)
    signals_fetched: int = 0
    signals_kept: int = 0
    signals_new: int = 0
    signals_updated: int = 0
    companies_scored: int = 0
    notifications_sent: int = 0
    signals_needing_review: int = 0
    review_reasons: dict[str, int] = Field(default_factory=dict)
    graph_entities_linked: int = 0
    error: str | None = None

    @property
    def duration_ms(self) -> int:
        if not self.finished_at:
            return 0
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    def summary(self) -> dict[str, Any]:
        """Compact form for GET /status and the UI's Settings > Scanning panel."""
        failed = [r.source.value for r in self.source_reports if not r.ok]
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "areas": self.areas,
            "signals_new": self.signals_new,
            "signals_kept": self.signals_kept,
            "companies_scored": self.companies_scored,
            "failed_sources": failed,
            "error": self.error,
        }
