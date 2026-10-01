"""Enrichment — company attribution and entity linking.

The PDF assigns this job to Amazon Comprehend Medical, linking extracted entities to
an internal ontology in HealthLake. Neither is provisioned in this stack, so the same
job is done with the two things that are: the declared keyword taxonomy, and the
Neo4j knowledge graph already sitting behind `eugene_ws`.

That substitution is an improvement for this particular use case, not a compromise.
Comprehend Medical extracts clinical entities from prose; what a BD Radar needs is
attribution to a *company* and a link to CSL's own portfolio. Structured applicant
names from USPTO, lead sponsors from ClinicalTrials.gov and filer names from EDGAR
give that directly and exactly, with no model confidence to second-guess.

Company identity is the delicate part. `Sangamo Therapeutics, Inc.`, `SANGAMO
THERAPEUTICS INC` and `Sangamo Therapeutics` must resolve to one watchlist row —
otherwise the evidence for a single company fragments across three near-duplicate
entries, each looking a third as important as the company actually is.
"""
from __future__ import annotations

import hashlib
import logging
import re

from scout.areas import Area
from scout.config import ScanConfig
from scout.models import RawSignal, SourceId
from scout.text import matched_keywords, normalize_company

logger = logging.getLogger(__name__)

# Sponsors that are not partnership candidates. A university or a government body can
# sponsor an excellent trial, but it is not a company CSL can do a deal with, and
# letting these into the watchlist fills the BD team's ranked list with institutions
# they cannot act on.
_NON_COMMERCIAL = re.compile(
    r"\b(university|universit[eä]|college|school|hospital|clinic|institute|institut|"
    r"foundation|trust|council|ministry|department|national|federal|centre national|"
    r"academy|academic|nhs|inserm|cnrs|nih|nci|fda|assistance publique)\b",
    re.IGNORECASE,
)


def is_commercial(name: str | None) -> bool:
    """Whether a sponsor/applicant name looks like a company.

    Substring matching on a curated word list rather than a classifier: it is
    inspectable, it is deterministic, and when it is wrong an analyst can see exactly
    which word caused it. `_NON_COMMERCIAL` deliberately errs toward excluding — a
    missing company can be added to the watchlist by hand, whereas a watchlist full
    of universities is a report nobody reads twice.
    """
    if not name or not name.strip():
        return False
    return not _NON_COMMERCIAL.search(name)


def company_id_for(name: str) -> str:
    """Stable synthetic id for a company, derived from its normalised name.

    Deterministic rather than random so the id survives a full rebuild of the curated
    tier from staging — which is the whole point of keeping raw data. A UUID minted
    per run would break every stored reference on the first replay.
    """
    normalized = normalize_company(name)
    return "co-" + hashlib.sha256(normalized.encode()).hexdigest()[:16]


def enrich(
    signal: RawSignal,
    area: Area,
    config: ScanConfig,
) -> RawSignal:
    """Fill in what the collector could not determine on its own.

    Returns a new RawSignal — the model is frozen, and enrichment being non-mutating
    means the staged raw record and the enriched one are separately inspectable.
    """
    company = signal.company_name
    if company and not is_commercial(company):
        # Keep the signal, drop the attribution. The trial is still real news; it
        # simply has no partnership counterparty.
        logger.debug(f"dropping non-commercial attribution: {company!r}")
        company = None

    # Re-match keywords across every text field now available, including any the
    # collector did not consider. Matching is spelling-normalised, so British-spelled
    # records match American-spelled taxonomy terms and vice versa.
    keywords = matched_keywords(
        area.keywords,
        signal.title,
        signal.summary,
        company or "",
        *_payload_text(signal),
    )

    return signal.model_copy(
        update={
            "company_name": company.strip() if company else None,
            "keywords": keywords,
        }
    )


def _payload_text(signal: RawSignal) -> list[str]:
    """Source-specific extra text worth matching against.

    Kept per-source rather than flattening the whole payload: dumping every value
    would match on field names, status codes and identifiers, producing keyword hits
    that are technically present and analytically meaningless.
    """
    p = signal.payload
    if signal.source == SourceId.TRIALS:
        return [
            " ".join(str(c) for c in (p.get("conditions") or [])),
            " ".join(str(i) for i in (p.get("interventions") or [])),
        ]
    if signal.source == SourceId.PATENTS:
        return [
            " ".join(str(c) for c in (p.get("cpc_classifications") or [])),
            str(p.get("first_inventor") or ""),
        ]
    if signal.source == SourceId.LITERATURE:
        return [str(p.get("journal") or "")]
    if signal.source == SourceId.EDGAR:
        return [str(p.get("form") or "")]
    return []


def is_relevant(signal: RawSignal, config: ScanConfig) -> tuple[bool, str]:
    """Relevance gate. Returns (keep, reason) so rejections are explainable.

    Both rejection reasons here were observed on live runs, not imagined:
      * zero matched keywords — an oncology checkpoint-inhibitor trial entered the
        hemophilia area because the registry's free-text search matched "inhibitor"
        somewhere in its protocol.
      * generic-only matches — USPTO patents for hearing loss and phenylketonuria
        entered on the strength of "gene therapy" alone.
    """
    if not signal.keywords:
        return False, "no area keywords matched"
    if not config.is_relevant(signal.keywords):
        generic = sorted(set(signal.keywords))
        return False, f"only generic keywords matched: {generic}"
    return True, ""


def resolve_companies(signals: list[RawSignal]) -> dict[str, str]:
    """Map each distinct company name to its stable id.

    Built once per run and shared, so two spellings of one company converge on a
    single id and therefore a single watchlist row.
    """
    out: dict[str, str] = {}
    for s in signals:
        if s.company_name:
            out.setdefault(s.company_name, company_id_for(s.company_name))
    return out
