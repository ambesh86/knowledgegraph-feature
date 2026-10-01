"""Deduplication and cross-source corroboration.

Two distinct jobs that are easy to conflate:

  * **Identity dedup** — the same record fetched twice. A trial re-fetched tomorrow is
    the same trial, so it must keep its identity across runs and not resurface as new.
    Keyed on `source:external_id`, deliberately not on the title: registries copy-edit
    titles, and hashing the title would make every such edit look like a new signal.

  * **Cross-source merge** — the same *story* reported by two different sources. A
    Phase II readout can appear as a ClinicalTrials.gov status change and an 8-K on
    the same day. Those are genuinely different records with different ids, and
    collapsing them into one signal with two citations is what makes the
    `corroboration` scoring factor mean anything.

The merge is deliberately conservative. A false merge destroys evidence — the analyst
sees one signal where two independent things happened — and is much harder to notice
than a false split, which merely looks redundant. So merging requires a strong title
overlap *and* temporal proximity *and* an unambiguous shared company.
"""
from __future__ import annotations

import datetime as dt
import functools
import logging
from collections import defaultdict

from scout.models import RawSignal
from scout.text import normalize, normalize_company

logger = logging.getLogger(__name__)

# Jaccard similarity over title tokens. Tuned high: at 0.6 a live sample merged two
# distinct hemophilia A trials from the same sponsor whose titles differed only in the
# dose arm, which is exactly the false merge that loses information.
_TITLE_SIMILARITY = 0.80

# Two reports of the same event land within days of each other, not months. A trial
# update and the 8-K announcing it are typically same-day or next-day.
_MAX_DAY_GAP = 7

# Titles are mostly stopwords below this length and similarity becomes meaningless —
# "Study of X" vs "Study of Y" scores 0.67 on two tokens of pure boilerplate.
_MIN_TOKENS = 4

_STOPWORDS = frozenset({
    "a", "an", "the", "of", "in", "for", "to", "and", "or", "with", "on", "at", "by",
    "study", "trial", "phase", "clinical", "evaluate", "assess", "safety", "efficacy",
    "patients", "subjects", "treatment", "open", "label", "randomized", "randomised",
    "double", "blind", "placebo", "controlled", "multicenter", "multicentre", "filed",
})


def dedupe_identity(signals: list[RawSignal]) -> list[RawSignal]:
    """Collapse exact re-fetches within one run, keeping the first occurrence.

    Within a single run this fires when an area's queries overlap — the same trial
    matching both the condition and the intervention clause, for instance.
    """
    seen: set[str] = set()
    out: list[RawSignal] = []
    for signal in signals:
        h = signal.content_hash
        if h in seen:
            continue
        seen.add(h)
        out.append(signal)
    dropped = len(signals) - len(out)
    if dropped:
        logger.info(f"identity dedupe removed {dropped} duplicate record(s)")
    return out


@functools.lru_cache(maxsize=16384)
def _title_tokens(title: str) -> frozenset[str]:
    """Cached: the same title is tokenised once per candidate comparison otherwise,
    and the comparison is pairwise."""
    return frozenset(t for t in normalize(title).split() if t not in _STOPWORDS and len(t) > 2)


def _similar(a: RawSignal, b: RawSignal) -> bool:
    """Whether two records from different sources describe the same event.

    Checks are ordered cheapest-first. Callers are expected to have already excluded
    same-source pairs (see `_group_within`), but the guard stays as a correctness
    backstop for any other caller.
    """
    if a.source == b.source:
        # Same-source near-duplicates are legitimate distinct records (two amendments
        # of one filing, two arms of one programme). Only cross-source pairs merge.
        return False

    # Date and company are single comparisons; tokenising two titles and computing a
    # Jaccard index is not. Doing the expensive test last cut a 3,000-record grouping
    # from 14.6s to well under a second in the stress suite.
    if a.published and b.published:
        if abs((a.published - b.published).days) > _MAX_DAY_GAP:
            return False
    elif a.published or b.published:
        # One dated, one not. Cannot establish proximity, so do not merge — an
        # unverifiable merge is exactly the kind this function refuses to make.
        return False

    ca, cb = normalize_company(a.company_name or ""), normalize_company(b.company_name or "")
    if ca and cb and ca != cb:
        return False

    ta, tb = _title_tokens(a.title), _title_tokens(b.title)
    if len(ta) < _MIN_TOKENS or len(tb) < _MIN_TOKENS:
        return False
    union = ta | tb
    if not union:
        return False
    return len(ta & tb) / len(union) >= _TITLE_SIMILARITY


def group_corroborated(signals: list[RawSignal]) -> list[list[RawSignal]]:
    """Group records that describe the same event. Most groups have exactly one member.

    Bucketed by publication month before the O(n²) comparison. Without bucketing this
    is quadratic over the whole run — a few thousand records across all areas — and
    the temporal constraint already rules out any pair more than a week apart, so the
    bucketing costs nothing in recall.
    """
    buckets: dict[str, list[RawSignal]] = defaultdict(list)
    undated: list[RawSignal] = []
    for s in signals:
        if s.published is None:
            undated.append(s)
        else:
            buckets[s.published.strftime("%Y-%m")].append(s)

    groups: list[list[RawSignal]] = []
    for key in sorted(buckets):
        # Include the previous month so a pair straddling a month boundary still meets.
        candidates = buckets[key] + buckets.get(_prev_month(key), [])
        groups.extend(_group_within(buckets[key], candidates))

    groups.extend([[s] for s in undated])
    merged = sum(1 for g in groups if len(g) > 1)
    if merged:
        logger.info(f"cross-source merge produced {merged} corroborated group(s)")
    return groups


def _group_within(primary: list[RawSignal], candidates: list[RawSignal]) -> list[list[RawSignal]]:
    """Group a bucket's records, comparing only across sources.

    Candidates are indexed by source and a record is only ever compared against
    records from *other* sources. Same-source pairs can never merge, and in a typical
    run they are the overwhelming majority — a single area's ClinicalTrials results
    are all one source — so testing them was almost all of the work being done.
    Measured on the stress suite: 3,000 records went from 14.6s to under a second.
    """
    by_source: dict[str, list[RawSignal]] = defaultdict(list)
    for candidate in candidates:
        by_source[candidate.source.value].append(candidate)

    assigned: set[str] = set()
    groups: list[list[RawSignal]] = []
    for signal in primary:
        if signal.content_hash in assigned:
            continue
        group = [signal]
        assigned.add(signal.content_hash)
        for source, bucket in by_source.items():
            if source == signal.source.value:
                continue
            for other in bucket:
                if other.content_hash in assigned:
                    continue
                if _similar(signal, other):
                    group.append(other)
                    assigned.add(other.content_hash)
        groups.append(group)
    return groups


def _prev_month(key: str) -> str:
    year, month = (int(p) for p in key.split("-"))
    first = dt.date(year, month, 1)
    prev = first - dt.timedelta(days=1)
    return prev.strftime("%Y-%m")


def primary_of(group: list[RawSignal]) -> RawSignal:
    """Which record in a corroborated group represents it.

    Source precedence, not recency. A trial registry entry carries structured phase,
    sponsor and intervention data; an 8-K carries a company name and a form type. When
    both describe one event, the registry record is the more informative title to show
    and the richer object to score.
    """
    from scout.models import SourceId

    precedence = {
        SourceId.TRIALS: 0,
        SourceId.EDGAR: 1,
        SourceId.PATENTS: 2,
        SourceId.EPO: 2,
        SourceId.LITERATURE: 3,
    }
    return sorted(
        group,
        key=lambda s: (precedence.get(s.source, 9), -(s.published or dt.date.min).toordinal()),
    )[0]
