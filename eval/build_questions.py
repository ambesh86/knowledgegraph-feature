"""Generate a ground-truth evaluation set from extracted table cells.

SUPERSEDED by `gold.py` — do not use for new measurements. Two defects make its
output unsafe to grade against:

  * it groups cells by ``(page, table_row)``, but two tables on one page share
    row indices, so rows from different tables are interleaved and the "answer"
    frequently belongs to a different table than the label;
  * its question ("what value was reported?") does not name a column, so a row
    with five numeric cells has five defensible answers and only one is scored
    correct.

Kept for provenance. `gold.py` reads the same cells from Neo4j — the store
retrieval actually serves from — and validates every question against the table's
own Markdown before emitting it.

Why table cells: they are the only part of this corpus where the correct answer
is knowable without a human labeller. A row reading
"Injection site reactions | 4 | 26/41 | 0/38 | 30.94 (6.43, 148.75) | <0.0001"
gives an unambiguous question ("what odds ratio was reported for injection site
reactions?") and an unambiguous answer ("30.94"), anchored to a specific chunk
whose bounding box we can render. That makes retrieval, correctness and citation
all checkable programmatically.

The alternative — hand-writing questions and grading answers by eye — is what the
research brief did, and it explicitly called 15 such questions "a pilot, not a
benchmark". This is bounded too, but it is at least reproducible and honest about
what it measures.
"""
from __future__ import annotations

import collections
import json
import re
import sys

sys.path.insert(0, "/app/src")

from ade import storage  # noqa: E402

# A cell must contain a decimal to be a statistic worth asking about.
_STAT = re.compile(r"\d+\.\d+")
_MIN_LABEL = 8


def build(doc_ids: list[str]) -> list[dict]:
    st = storage.storage()
    questions: list[dict] = []

    for doc_id in doc_ids:
        try:
            chunks = st.get_json(storage.key_chunks(doc_id))
            manifest = st.get_json(storage.key_manifest(doc_id))
        except Exception:
            continue
        title = (manifest.get("metadata") or {}).get("title", "")

        cells = [c for c in chunks if c.get("chunk_type") == "table_cell"]
        rows: dict[tuple, dict] = collections.defaultdict(dict)
        for c in cells:
            rows[(c["page"], c["table_row"])][c["table_col"]] = c

        for (page, row), cols in rows.items():
            if 0 not in cols:
                continue
            label = cols[0]["text"].strip()
            if len(label) < _MIN_LABEL or label[0].isdigit():
                continue
            # The first statistic-bearing cell after the label is the answer.
            stat_cell = next(
                (v for k, v in sorted(cols.items()) if k > 0 and _STAT.search(v["text"])),
                None,
            )
            if not stat_cell:
                continue
            value = _STAT.search(stat_cell["text"]).group(0)  # type: ignore[union-attr]
            questions.append({
                "id": f"{doc_id}-p{page}-r{row}",
                "question": (
                    f"In the study reporting on {label}, what value was reported? "
                    f"Answer with the number."
                ),
                "label": label,
                "expected_value": value,
                "expected_text": stat_cell["text"],
                "gold_chunk_id": stat_cell["chunk_id"],
                "doc_id": doc_id,
                "page": page,
                "paper_title": title,
            })
    return questions


if __name__ == "__main__":
    docs = sys.argv[1:] or ["41402784", "pmc13202553", "pmc13241882", "pmc13206652"]
    qs = build(docs)
    print(json.dumps(qs, indent=1))
