"""Is the answer actually supported by the evidence it cites?

Retrieval accuracy asks "did the right passage arrive". Answer accuracy asks "was
the final string correct". Neither asks the question a researcher actually cares
about, which is: **every claim in this answer — can I trace it to a source?**

That gap is where the dangerous failure lives. An answer can cite nine real
passages, none of which support the sentence they are attached to, and score
perfectly on both existing metrics. In a biomedical BD context the specific
failure that costs credibility is a fabricated statistic: a hazard ratio, an n, a
p-value that appears nowhere in the cited paper. It reads exactly like a correct
one.

So the primary check here is deterministic and needs no model:

    every number in the answer must appear in a passage the answer cites

That is narrow, and narrowness is the point — it is auditable, reproducible,
cheap, and it cannot itself hallucinate. A stakeholder can verify any flagged
claim by eye in seconds. An LLM judge is offered alongside for prose claims that
carry no numbers, but it never overrides the deterministic result, and its own
agreement with human labels is measured before its output is quoted (see
metrics.cohen_kappa).

Four things are measured, kept separate because they fail for different reasons
and are fixed by different people:

  * numeric groundedness  — are the figures real?            (retrieval + prompt)
  * citation validity     — do the markers point at passages that exist? (plumbing)
  * claim support         — does the cited passage discuss the claim?    (ranking)
  * abstention            — does it say "I don't know" when it should?   (prompt)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

# Matches 26, 26.5, 1,234, 0.0001, 30.94, 4.5e-3 — with optional leading sign.
_NUMBER = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")

# A bare four-digit number in 1900..2100 is almost always a year or a reference,
# not a finding. Counting those as unsupported claims would bury the real
# failures under noise, and counting them as supported would be dishonest — so
# they are classified out and reported separately.
_YEAR = re.compile(r"^(19|20)\d{2}$")

# Journal-citation debris: "2017;377(9):809-818", "doi:10.1056/NEJMoa1703068".
# The numbers inside a reference are bibliographic, not claims about the world.
#
# `[Evidence 5, Evidence 7]` is in this list because of a false alarm this module
# produced against a real answer on its first run: the marker indices were being
# read as findings, so a correctly-cited answer was reported as five fabricated
# statistics. A faithfulness metric that fires on correct behaviour is worse than
# none, because the first thing a reader does is stop believing it.
_CITATION_SPAN = re.compile(
    r"\[\s*(?:Evidence\s+\d+\s*,?\s*)+\]"              # our own citation markers
    r"|\b\d{4};\s*\d+\s*\(\d+\)\s*:\s*\d+[-–]\d+"      # vol(issue):pages
    r"|doi:\s*\S+"                                     # doi
    r"|\bNCT\d{8}\b"                                   # trial ids
    r"|\bPMC?\d{5,}\b",                                # pubmed / pmc ids
    re.IGNORECASE,
)


def _normalise(token: str) -> str:
    """Canonical form so 1,234 == 1234 and 0.50 == 0.5.

    Without this the check produces false alarms on formatting alone, and a
    faithfulness metric that cries wolf is one nobody reads twice.
    """
    t = token.replace(",", "").strip().lstrip("+")
    if not t or t in {"-", "."}:
        return ""
    try:
        f = float(t)
    except ValueError:
        return t
    # Integers keep integer form; floats drop trailing zeros.
    if f == int(f) and abs(f) < 1e15 and "e" not in t.lower():
        return str(int(f))
    return repr(f)


@dataclass
class NumericClaim:
    raw: str
    normalised: str
    kind: str          # "statistic" | "year" | "bibliographic"
    context: str       # surrounding text, so a human can adjudicate a flag
    supported: bool = False


def extract_numbers(text: str) -> list[NumericClaim]:
    """Pull every number out of an answer, classified by what it is."""
    # Blank out bibliographic spans first so their internals are not read as
    # findings, but keep offsets stable by replacing with same-length filler.
    masked = _CITATION_SPAN.sub(lambda m: "\x00" * len(m.group(0)), text)

    claims: list[NumericClaim] = []
    for m in _NUMBER.finditer(masked):
        raw = m.group(0)
        norm = _normalise(raw)
        if not norm:
            continue
        start, end = m.span()
        kind = "year" if _YEAR.match(raw.replace(",", "")) else "statistic"
        claims.append(
            NumericClaim(
                raw=raw,
                normalised=norm,
                kind=kind,
                context=text[max(0, start - 40) : min(len(text), end + 40)].replace("\n", " "),
            )
        )

    # Numbers inside masked (bibliographic) spans, recorded so the accounting is
    # complete and a reader can see nothing was quietly dropped.
    for m in _CITATION_SPAN.finditer(text):
        for num in _NUMBER.finditer(m.group(0)):
            norm = _normalise(num.group(0))
            if norm:
                claims.append(
                    NumericClaim(num.group(0), norm, "bibliographic", m.group(0)[:80])
                )
    return claims


def _evidence_numbers(passages: list[str]) -> set[str]:
    out: set[str] = set()
    for p in passages:
        for m in _NUMBER.finditer(p or ""):
            n = _normalise(m.group(0))
            if n:
                out.add(n)
    return out


# ---------------------------------------------------------------------------
# Claim support (prose, no numbers)
# ---------------------------------------------------------------------------

_STOP = set(
    ("a an the and or but if then than that this these those of in on at to for with by from as is "
     "are was were be been being it its we our you your they their he she his her not no also can "
     "may might will would should could have has had do does did which who what when where how why "
     "into over under about between both each more most other some such only own same so too very "
     "just study patients results shown reported").split()
)


def _terms(text: str) -> set[str]:
    return {
        w for w in re.sub(r"[^a-z0-9\s-]", " ", (text or "").lower()).split()
        if len(w) > 2 and w not in _STOP
    }


def sentence_support(sentence: str, passages: list[str]) -> float:
    """Best term-overlap between a sentence and any single cited passage.

    Deliberately compared against ONE passage rather than the union of all of
    them: a sentence whose terms are scattered across nine unrelated passages is
    not supported by any of them, and unioning would score exactly that case as
    well-grounded. This is the same reasoning the UI's citation anchoring uses.
    """
    st = _terms(sentence)
    if not st:
        return 0.0
    best = 0.0
    for p in passages:
        pt = _terms(p)
        if not pt:
            continue
        best = max(best, len(st & pt) / len(st))
    return best


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 15]


# ---------------------------------------------------------------------------
# The per-answer report
# ---------------------------------------------------------------------------


@dataclass
class FaithfulnessReport:
    numeric_total: int = 0
    numeric_supported: int = 0
    ungrounded: list[NumericClaim] = field(default_factory=list)
    sentences_total: int = 0
    sentences_supported: int = 0
    unsupported_sentences: list[str] = field(default_factory=list)
    citations_total: int = 0
    citations_valid: int = 0
    invalid_citations: list[str] = field(default_factory=list)
    abstained: bool = False

    @property
    def numeric_groundedness(self) -> float:
        return self.numeric_supported / self.numeric_total if self.numeric_total else 1.0

    @property
    def claim_support(self) -> float:
        return self.sentences_supported / self.sentences_total if self.sentences_total else 1.0

    @property
    def citation_validity(self) -> float:
        return self.citations_valid / self.citations_total if self.citations_total else 1.0

    def as_dict(self) -> dict:
        return {
            "numeric_groundedness": round(self.numeric_groundedness, 4),
            "numeric_total": self.numeric_total,
            "numeric_supported": self.numeric_supported,
            "ungrounded_numbers": [
                {"value": c.raw, "context": c.context} for c in self.ungrounded
            ],
            "claim_support": round(self.claim_support, 4),
            "sentences_total": self.sentences_total,
            "sentences_supported": self.sentences_supported,
            "unsupported_sentences": self.unsupported_sentences[:5],
            "citation_validity": round(self.citation_validity, 4),
            "citations_total": self.citations_total,
            "citations_valid": self.citations_valid,
            "invalid_citations": self.invalid_citations,
            "abstained": self.abstained,
        }


_EVIDENCE_MARKER = re.compile(r"\[\s*Evidence\s+(\d+)\s*\]", re.IGNORECASE)
_ABSTENTION = re.compile(
    r"\b(i (do not|don't) (have|know)|no (relevant )?(evidence|information|data) "
    r"(was )?(found|available)|cannot (answer|determine)|not enough (evidence|information))\b",
    re.IGNORECASE,
)


def evaluate(answer: str, passages: list[str], support_threshold: float = 0.30) -> FaithfulnessReport:
    """Score one answer against the passages it was given.

    `passages` is what retrieval actually returned for this question — the model's
    permitted universe. A claim traceable to nothing in that list is unsupported,
    whether or not it happens to be true in the world. That distinction is the
    whole point: we are measuring whether the system can show its work, not
    whether it got lucky.
    """
    rep = FaithfulnessReport()
    answer = answer or ""

    rep.abstained = bool(_ABSTENTION.search(answer))

    # 1. Numbers — the deterministic core.
    evidence_nums = _evidence_numbers(passages)
    for claim in extract_numbers(answer):
        if claim.kind != "statistic":
            continue  # years and bibliography are not findings
        rep.numeric_total += 1
        if claim.normalised in evidence_nums:
            claim.supported = True
            rep.numeric_supported += 1
        else:
            rep.ungrounded.append(claim)

    # 2. Prose claims.
    for sentence in split_sentences(answer):
        rep.sentences_total += 1
        if sentence_support(sentence, passages) >= support_threshold:
            rep.sentences_supported += 1
        else:
            rep.unsupported_sentences.append(sentence)

    # 3. Citation markers must resolve to a passage that exists. An answer citing
    #    "[Evidence 12]" when eight passages were retrieved is fabricating a
    #    reference, which is worse than not citing at all.
    for m in _EVIDENCE_MARKER.finditer(answer):
        rep.citations_total += 1
        n = int(m.group(1))
        if 1 <= n <= len(passages):
            rep.citations_valid += 1
        else:
            rep.invalid_citations.append(m.group(0))

    return rep
