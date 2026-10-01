"""Biomedical text normalisation for keyword matching.

This module exists because of a measured failure, not a hypothetical one. On the first
live run of the literature collector, a Europe PMC result titled *"Quality of Life in
People With Haemophilia"* matched **zero** of the hemophilia area's keywords. The
declared keyword is `hemophilia`; the journal is British and wrote `haemophilia`. Every
paper from a European journal was scoring `area_fit = 0` and sinking to the bottom of
the Radar — a silent, systematic bias against half the world's literature that no error
message would ever have reported.

The transforms below are the small set that actually matter for this corpus:

  * **British → American medical spelling.** `haemophilia`/`hemophilia`,
    `oedema`/`edema`, `tumour`/`tumor`, `anaemia`/`anemia`. These are the same word.
  * **-ise → -ize.** `immunise`/`immunize`.
  * **Punctuation and hyphenation.** `CAR-T`, `CAR T`, and `CART` are one concept;
    `factor-VIII` and `factor VIII` likewise.
  * **Roman/Arabic numeral equivalence for factors.** `factor VIII` and `factor 8`
    both appear in filings and abstracts.

Deliberately NOT done here: stemming, lemmatisation, or synonym expansion. Those
change meaning. `inhibitor` and `inhibition` are different claims in hematology — an
"inhibitor" is a specific, serious clinical complication in hemophilia, not a generic
description of a mechanism — and collapsing them would produce matches an analyst
would rightly call wrong.
"""
from __future__ import annotations

import functools
import re

# Ordered longest-first so `haemophilia` is rewritten before a shorter `haem` rule
# could fire inside it and corrupt the token.
_SPELLING = (
    ("haemophilia", "hemophilia"),
    ("haemorrhage", "hemorrhage"),
    ("haematolog", "hematolog"),
    ("haemostas", "hemostas"),
    ("haemoglobin", "hemoglobin"),
    ("anaemia", "anemia"),
    ("oedema", "edema"),
    ("oesophag", "esophag"),
    ("paediatric", "pediatric"),
    ("tumour", "tumor"),
    ("leukaemia", "leukemia"),
    ("immunoglobulin", "immunoglobulin"),
    ("globulin", "globulin"),
    ("caesarean", "cesarean"),
    ("fibre", "fiber"),
    ("centre", "center"),
    ("licence", "license"),
    ("analyse", "analyze"),
    ("immunise", "immunize"),
    ("randomise", "randomize"),
    ("characterise", "characterize"),
)

# Coagulation factors are written both ways in the same corpus; `factor VIII` in a
# journal title and `factor 8` in a filing are the same molecule.
_ROMAN = (
    ("factor xiii", "factor 13"),
    ("factor xii", "factor 12"),
    ("factor xi", "factor 11"),
    ("factor x", "factor 10"),
    ("factor ix", "factor 9"),
    ("factor viii", "factor 8"),
    ("factor vii", "factor 7"),
    ("factor v", "factor 5"),
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")

# Trailing industry words that describe what a company does rather than which company
# it is. `Regeneron Pharmaceuticals` and `Regeneron` are one filer; so are
# `Bioverativ Therapeutics` and `Bioverativ`.
#
# What is deliberately ABSENT matters as much as what is present. `products`,
# `diagnostics`, `devices` and `ventures` are excluded because they routinely
# distinguish sibling legal entities of one parent — `Roche Products` and `Roche
# Holding` are different companies with different pipelines, and merging them would
# attribute one's assets to the other. The rule throughout this module: a false merge
# destroys evidence invisibly, a false split merely looks redundant.
_INDUSTRY_DESCRIPTORS: tuple[tuple[str, ...], ...] = (
    ("therapeutics",),
    ("therapeutic",),
    ("pharmaceuticals",),
    ("pharmaceutical",),
    ("pharma",),
    ("biopharmaceuticals",),
    ("biopharmaceutical",),
    ("biopharma",),
    ("biosciences",),
    ("bioscience",),
    ("biotherapeutics",),
    ("biologics",),
    ("biotechnology",),
    ("biotech",),
    ("laboratories",),
    ("laboratory",),
    ("labs",),
    ("medicines",),
    ("medicine",),
    ("genomics",),
    ("genetics",),
)

# "Bioverativ, a Sanofi company" / "Acme (a subsidiary of Zeta)". The parent is
# ownership metadata; the entity being described is the one before the comma.
_OWNERSHIP_PHRASE = re.compile(
    r"[,(]\s*(?:an?\s+)?[\w\s.&'-]*?"
    r"\b(?:company|subsidiary|group|business|affiliate|unit|brand|division)\b\s*\)?\s*$",
    re.IGNORECASE,
)
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*")


def _strip_ownership_descriptor(name: str) -> str:
    """Remove a trailing ownership clause before normalisation.

    Runs on the raw string because it depends on punctuation — the comma and the
    parentheses are the signal, and `normalize()` collapses both away.
    """
    if not name:
        return ""
    out = _OWNERSHIP_PHRASE.sub("", name).strip()
    out = _PARENTHETICAL.sub(" ", out).strip()
    # If stripping consumed everything, the clause WAS the name. Keep the original
    # rather than returning an empty identity that every such filer would share.
    return out.strip(" ,-") or name


@functools.lru_cache(maxsize=8192)
def normalize(text: str) -> str:
    """Fold a string into the comparison form used on both sides of a match.

    Cached because the same area keywords are normalised against every one of the
    hundreds of records in a scan; recomputing per record turned out to dominate the
    enrichment step's runtime.
    """
    if not text:
        return ""
    out = text.lower()
    for british, american in _SPELLING:
        if british in out:
            out = out.replace(british, american)

    # Punctuation is collapsed BEFORE the roman-numeral pass, not after. "FACTOR-VIII"
    # must become "factor viii" before the rule looking for "factor viii" can fire;
    # running the passes the other way round left hyphenated forms unconverted while
    # the keyword side converted fine, so "FACTOR-VIII deficiency" failed to match the
    # keyword "factor viii".
    out = _NON_ALNUM.sub(" ", out)
    out = _WS.sub(" ", out).strip()

    for roman, arabic in _ROMAN:
        if roman in out:
            out = out.replace(roman, arabic)
    return _WS.sub(" ", out).strip()


def matches(keyword: str, haystack_normalized: str) -> bool:
    """Whether a keyword occurs in an already-normalised haystack.

    Word-boundary aware, so the keyword `ig` does not match inside `light` and
    `pcc` does not match inside `pccx`. Substring matching here was the first
    implementation and it produced matches an analyst would call nonsense.
    """
    kw = normalize(keyword)
    if not kw or not haystack_normalized:
        return False
    return f" {kw} " in f" {haystack_normalized} "


def matched_keywords(keywords: tuple[str, ...] | list[str], *parts: str) -> tuple[str, ...]:
    """Which of `keywords` appear anywhere in `parts`. Returns the ORIGINAL keyword
    spellings, not the normalised ones — the UI shows these to analysts, and
    displaying `hemophilia` when the declared term was `haemophilia` (or vice versa)
    would look like a bug even though the match was correct."""
    haystack = normalize(" ".join(p for p in parts if p))
    if not haystack:
        return ()
    return tuple(k for k in keywords if matches(k, haystack))


def normalize_company(name: str) -> str:
    """Canonical form for company identity.

    Three classes of noise are removed, in order, because each one was observed
    splitting a single company into multiple watchlist rows with a fraction of the
    evidence each:

      1. **Ownership descriptors.** `Bioverativ, a Sanofi company` is Bioverativ.
         The parent's name is metadata, not part of the identity.
      2. **Legal suffixes.** `Inc`, `GmbH`, `N.V.` — `Sangamo Therapeutics, Inc.`
         and `SANGAMO THERAPEUTICS INC` are one company.
      3. **Industry descriptors.** `Regeneron Pharmaceuticals` is Regeneron;
         `Bioverativ Therapeutics` is Bioverativ. This is what finally merged the
         two Bioverativ rows a live run produced.

    Resolution is **deterministic per name** rather than clustered across a run.
    That distinction matters: `company_id_for` hashes this output, so an id derived
    from which other names happened to co-occur in one scan would change between
    runs and orphan every stored reference. A pure function of one string survives
    a full rebuild from staging.

    The stripping is bounded by design. Only descriptors that are genuinely generic
    across the industry are removed, and `products`, `holding`'s sibling terms and
    anything else that can distinguish two real subsidiaries are deliberately left
    in — a false merge silently attributes another company's pipeline, which is far
    worse than a duplicate row an analyst can see.
    """
    out = normalize(_strip_ownership_descriptor(name))
    if not out:
        return ""
    # Multi-token entries are listed because punctuation collapse turns "N.V." into
    # "n v" — two tokens. Checking only the final token left "Acme Bio N.V." as
    # "acme bio n v" while "ACME BIO NV" became "acme bio", so one company split into
    # two watchlist rows.
    suffixes = (
        ("incorporated",), ("inc",), ("corporation",), ("corp",), ("company",), ("co",),
        ("limited",), ("ltd",), ("llc",), ("lp",), ("plc",),
        ("nv",), ("n", "v"), ("sa",), ("s", "a"), ("bv",), ("b", "v"),
        ("ag",), ("gmbh",), ("ab",), ("as",), ("a", "s"), ("oy",), ("spa",), ("s", "p", "a"),
        ("holdings",), ("holding",), ("group",),
    )
    # Longest first so ("n", "v") is tried before ("v",) could ever match a fragment.
    ordered = sorted(suffixes + _INDUSTRY_DESCRIPTORS, key=len, reverse=True)

    words = out.split()
    stripped = True
    while words and stripped:
        stripped = False
        for suffix in ordered:
            # `len(words) > len(suffix)` — never strip down to nothing. A filer
            # genuinely named "Therapeutics Inc" keeps "therapeutics" as its identity
            # rather than collapsing to the empty string and colliding with every
            # other name that also reduced to nothing.
            if len(words) > len(suffix) and tuple(words[-len(suffix):]) == suffix:
                del words[-len(suffix):]
                stripped = True
                break

    while words and words[0] == "the":
        words.pop(0)
    return " ".join(words)
