"""Build a ground-truth QA set from indexed table cells, read from Neo4j.

Why table cells: they are the only part of this corpus where the correct answer
is knowable without a human labeller, and `indexer.py` deliberately exempts them
from the length floor so every cell is a retrievable, citable node.

Why Neo4j rather than the S3 artifacts: the graph is what retrieval actually
serves from. A gold answer read out of S3 can describe a chunk that was never
indexed, which scores the extractor instead of the system under test.

Two properties every question here must have, because without them no prompt can
be graded honestly:

  * **Table-scoped.** Cells are grouped by `parent_chunk_id`, not by page. Two
    tables on one page share row indices — grouping by page interleaves their
    rows and produces gold answers that belong to the wrong table.
  * **Unambiguous.** The question names the row label AND the column header, and
    the row label must be unique inside its table. "What value was reported for
    injection site reactions?" has five defensible answers in a five-column row;
    a model that gives a different correct one is marked wrong for no reason.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

NEO4J_HTTP = os.environ.get("EVAL_NEO4J_HTTP", "http://localhost:17474")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "eugene_local_2024")

# A cell worth asking about holds a number.
_DECIMAL = re.compile(r"\d+\.\d+")
# A cell that is ONLY digits and statistical punctuation — "7", "26/41",
# "1.74 (1.01, 3.00)", "<0.0001". Distinguishing these from prose that merely
# contains a digit ("Liu 59 (2025)") is what separates a data row from a header
# row; the cruder "contains a digit" test rejected 44 of 66 tables outright,
# because study labels and reference numbers carry digits too.
_NUMERIC_CELL = re.compile(r"^[\s\d.,%/()\[\]<>=±+– -]*\d[\s\d.,%/()\[\]<>=±+– -]*$")
_MIN_LABEL_CHARS = 6
_MAX_HEADER_ROWS = 3


def cypher(statement: str, **params) -> list[dict]:
    body = json.dumps({"statements": [{"statement": statement, "parameters": params}]}).encode()
    req = urllib.request.Request(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic "
            + base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode(),
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    result = payload["results"][0]
    cols = result["columns"]
    return [dict(zip(cols, d["row"])) for d in result["data"]]


def _fetch_tables() -> dict[str, str]:
    """Markdown text of each table chunk, keyed by chunk id."""
    return {
        r["chunk_id"]: r["text"] or ""
        for r in cypher(
            "MATCH (c:paper_chunk) WHERE c.chunk_type = 'table' "
            "RETURN c.chunk_id AS chunk_id, c.text AS text"
        )
    }


def _fetch_cells() -> list[dict]:
    return cypher(
        "MATCH (p:paper)-[:has_chunk]->(c:paper_chunk) "
        "WHERE c.chunk_type = 'table_cell' AND c.parent_chunk_id <> '' "
        "RETURN c.doc_id AS doc_id, c.chunk_id AS chunk_id, "
        "       c.parent_chunk_id AS table_id, c.page AS page, "
        "       c.table_row AS row, c.table_col AS col, c.text AS text, "
        "       p.title AS paper_title"
    )


def _split_header(rows: dict[int, dict[int, dict]]) -> tuple[list[int], list[int]]:
    """Leading all-text rows are the header; everything after is data.

    Headers span more than one row more often than not — "Disease of" sits above
    "Interest", and only the pair reads as a column name. Taking just row 0 gives
    a question that asks about a column called "Disease of", which is not a thing
    a reader could locate in the table.
    """
    ordered = sorted(rows)
    header: list[int] = []
    for r in ordered:
        if len(header) >= _MAX_HEADER_ROWS:
            break
        if any(_NUMERIC_CELL.match(c["text"].strip()) for c in rows[r].values()):
            break
        header.append(r)
    data = [r for r in ordered if r not in header]
    return header, data


# A column header is a NAME, not a value. Cells like "(RAINIER)" or
# "NCT06564142" end up in the header row when the parser splits a table whose
# real header lives in a sibling chunk; asking "what is the value in the
# NCT06564142 column" is unanswerable by construction and would cap accuracy
# below the target for a reason that has nothing to do with retrieval.
_HEADER_WORD = re.compile(r"[A-Za-z]{3,}")
_ID_LIKE = re.compile(r"^(NCT\d+|[A-Z]\d[A-Z0-9]{3,}|\(?[A-Z]{3,}\)?)$")
# Arrows and comparison glyphs are table DATA — "↓ hsCRP" is a result, not the
# name of a column. When they turn up in the header row, the parser has folded a
# data row into the header, and every question built from that table asks about a
# column that does not exist.
_DATA_GLYPH = re.compile(r"[↑↓↔≈≥≤→←□■●○]")


def _clipped(text: str) -> bool:
    """True when a cell's brackets don't balance — i.e. it was split mid-token.

    "(JAK-STAT" is not a row label a reader could match against the printed
    table; it is the left half of one, produced when the parser cut a cell at a
    line wrap. Whatever else is in that table's grid was cut the same way, so the
    row/column association cannot be trusted.
    """
    return text.count("(") != text.count(")") or text.count("[") != text.count("]")


def _plausible_header(text: str) -> bool:
    t = text.strip()
    if not _HEADER_WORD.search(t) or _DATA_GLYPH.search(t) or _clipped(t):
        return False
    return not any(_ID_LIKE.match(tok) for tok in t.split())


def _coherent(q: dict, table_md: str) -> bool:
    """Confirm the row/column association against the table's own markdown.

    The cell grid and the rendered Markdown are two independent products of the
    same parse. If the expected value does not sit on the same Markdown row as
    the label we keyed it to, the grouping is wrong and the gold answer is wrong
    — exactly the failure that grouping by page instead of by table produced.
    """
    if not table_md:
        return False
    label, value = q["row_label"], q["expected_text"]
    for line in table_md.splitlines():
        if label in line and value in line:
            return True
    return False


def build() -> list[dict]:
    cells = _fetch_cells()
    table_md = _fetch_tables()
    tables: dict[str, dict[int, dict[int, dict]]] = {}
    meta: dict[str, dict] = {}
    for c in cells:
        t = tables.setdefault(c["table_id"], {})
        t.setdefault(c["row"], {})[c["col"]] = c
        meta.setdefault(
            c["table_id"],
            {"doc_id": c["doc_id"], "page": c["page"], "paper_title": c["paper_title"] or ""},
        )

    questions: list[dict] = []
    for table_id, rows in tables.items():
        header_rows, data_rows = _split_header(rows)
        if not header_rows or len(data_rows) < 2:
            continue

        headers: dict[int, str] = {}
        for r in header_rows:
            for col, cell in rows[r].items():
                part = cell["text"].strip()
                if part:
                    headers[col] = (headers.get(col, "") + " " + part).strip()
        headers = {c: h for c, h in headers.items() if _plausible_header(h)}
        if len(headers) < 2:
            continue

        label_col = min(headers)
        # A row label that repeats cannot identify a row, so the question it
        # produces is unanswerable however good the retrieval is.
        label_counts: dict[str, int] = {}
        for r in data_rows:
            lab = (rows[r].get(label_col, {}).get("text") or "").strip()
            label_counts[lab] = label_counts.get(lab, 0) + 1

        # Cell values that repeat anywhere in the table are excluded for the same
        # reason from the other direction: the grader cannot tell a lucky hit on a
        # different row from a correct answer.
        value_counts: dict[str, int] = {}
        for r in rows.values():
            for cell in r.values():
                v = cell["text"].strip()
                value_counts[v] = value_counts.get(v, 0) + 1

        for r in data_rows:
            label = (rows[r].get(label_col, {}).get("text") or "").strip()
            if len(label) < _MIN_LABEL_CHARS or label_counts[label] != 1:
                continue
            # The label has to identify a row to a human reader. Accession codes
            # ("P01946") qualify; a glyph run or a bare statistic does not.
            if _DATA_GLYPH.search(label) or _NUMERIC_CELL.match(label) or _clipped(label):
                continue
            # The answer cell must be a STATISTIC, not prose that happens to
            # contain a digit. This is the premise the whole gold set rests on:
            # "30.94" has exactly one correct answer, whereas a wrapped prose
            # fragment like "40% ($ composite failure) kidney decline," is a
            # symptom of a scrambled parse and has no correct answer at all.
            candidates = [
                (col, cell)
                for col, cell in sorted(rows[r].items())
                if col != label_col
                and col in headers
                and _NUMERIC_CELL.match(cell["text"].strip())
                and value_counts[cell["text"].strip()] == 1
            ]
            if not candidates:
                continue
            # Prefer a decimal-bearing cell: "30.94" is a sharper grading target
            # than "7", which can coincide with an unrelated number the model
            # happened to emit.
            col, cell = next(
                ((c, x) for c, x in candidates if _DECIMAL.search(x["text"])), candidates[0]
            )
            decimal = _DECIMAL.search(cell["text"])
            m = meta[table_id]
            q = {
                "id": f"{m['doc_id']}-{table_id[:8]}-r{r}c{col}",
                "question": (
                    f"In the paper \"{m['paper_title']}\", the table on page {m['page']} "
                    f"has a row where the \"{headers[label_col]}\" column reads "
                    f"\"{label}\". What is the value in the \"{headers[col]}\" column "
                    f"for that row? Answer with the cell's exact contents and nothing else."
                ),
                # The same question asked the way a person would ask it. The
                # quoted form above hands a lexical matcher the exact spans to
                # look for, which flatters any reranker that keys off them; this
                # form removes that crutch and is the honest stress test.
                "question_natural": (
                    f"In {m['paper_title'].rstrip('.')}, what {headers[col].lower()} "
                    f"is reported for {label}?"
                ),
                "row_label": label,
                "column_header": headers[col],
                "expected_text": cell["text"].strip(),
                "expected_value": decimal.group(0) if decimal else cell["text"].strip(),
                "gold_chunk_id": cell["chunk_id"],
                "table_chunk_id": table_id,
                "doc_id": m["doc_id"],
                "page": m["page"],
                "paper_title": m["paper_title"],
            }
            if _coherent(q, table_md.get(table_id, "")):
                questions.append(q)
    questions.sort(key=lambda q: q["id"])
    return questions


if __name__ == "__main__":
    qs = build()
    out = os.environ.get("EVAL_GOLD_PATH", "eval/gold.json")
    with open(out, "w") as fh:
        json.dump(qs, fh, indent=1)
    docs = len({q["doc_id"] for q in qs})
    tables = len({q["table_chunk_id"] for q in qs})
    print(f"{len(qs)} questions from {tables} tables across {docs} documents -> {out}")
