"""Turning a due-diligence target into something the existing collectors can sweep.

Use Case 2 asks for four specialist sub-agents — Literature, Clinical Data, IP, and
Competitive Positioning — fanned out against one company or asset. Use Case 1 already
built and hardened exactly those fetchers: rate limiting that respects SEC's 10 req/s
and NCBI's stated restraint, the never-raise contract so one dead source degrades one
column instead of the run, local date filtering because Europe PMC ignores its own
sort parameter.

Rebuilding them target-scoped would mean re-learning all of that, and the second
implementation would drift from the first the day someone fixed a bug in only one. So
this module does the cheaper thing: it expresses a due-diligence target as an `Area`.

An Area is "a label plus the queries that sweep it". A target is a label plus the
queries that sweep it. The collectors never learn the difference, and every property
they already guarantee holds unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from scout.areas import Area


def slug(text: str) -> str:
    """Stable id for a target, so re-running due diligence on the same company
    overwrites its brief rather than accumulating near-duplicates in S3."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "unknown"


# Corporate suffixes carry no search signal and actively hurt recall: ClinicalTrials.gov
# lists "Hoffmann-La Roche" as the sponsor of trials that Europe PMC attributes to
# "Roche". Searching the full legal name finds the intersection rather than the union.
_LEGAL_SUFFIX = re.compile(
    r"\b(inc|inc\.|llc|ltd|limited|corp|corporation|co|company|plc|gmbh|ag|sa|s\.a|"
    r"nv|n\.v|ab|as|a/s|oy|pty|holdings?|group|therapeutics|pharmaceuticals?|pharma|"
    r"biosciences?|bio|labs?|laboratories)\b\.?",
    re.IGNORECASE,
)


def core_name(company: str) -> str:
    """The searchable stem of a company name.

    "Alnylam Pharmaceuticals, Inc." -> "Alnylam". Kept as a separate function because
    the brief shows the full legal name to the reader while searching on the stem;
    conflating the two produces either an unrecognisable heading or an empty result set.
    """
    stripped = _LEGAL_SUFFIX.sub(" ", company or "")
    stripped = re.sub(r"[,\.]+", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    # A name that was ENTIRELY suffixes ("Bio Labs Ltd") keeps its original form —
    # returning an empty query would silently sweep the whole corpus.
    return stripped or (company or "").strip()


@dataclass
class Target:
    """What due diligence is being run on."""

    company: str
    asset: str | None = None
    aliases: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return slug(f"{self.company}-{self.asset}" if self.asset else self.company)

    @property
    def label(self) -> str:
        return f"{self.company} — {self.asset}" if self.asset else self.company

    def search_terms(self) -> list[str]:
        """Every string worth searching for, most specific first."""
        terms = []
        if self.asset:
            terms.append(self.asset)
        stem = core_name(self.company)
        terms.append(stem)
        if stem.lower() != (self.company or "").strip().lower():
            terms.append(self.company.strip())
        terms.extend(a for a in self.aliases if a)
        # Order-preserving dedupe, case-insensitive.
        seen, out = set(), []
        for t in terms:
            k = t.lower().strip()
            if k and k not in seen:
                seen.add(k)
                out.append(t.strip())
        return out

    def as_area(self) -> Area:
        """Express the target as an Area the collectors already understand.

        The asset, when given, is AND-ed with the company for literature rather than
        OR-ed: a due-diligence brief on one molecule should not fill up with the
        company's unrelated programmes. For trials the sponsor field does that job
        better, so the terms stay OR-ed and the sponsor filter is applied downstream.
        """
        terms = self.search_terms()
        quoted = [f'"{t}"' for t in terms]

        if self.asset:
            literature = f'"{self.asset}" AND ("{core_name(self.company)}")'
        else:
            literature = " OR ".join(quoted)

        return Area({
            "id": f"dd-{self.id}",
            "label": self.label,
            "enabled": True,
            "queries": {
                "literature": literature,
                "trials_condition": " OR ".join(quoted),
                "trials_intervention": self.asset or core_name(self.company),
            },
            # Keywords drive relevance scoring downstream. Lower-cased by Area itself.
            "keywords": terms,
        })
