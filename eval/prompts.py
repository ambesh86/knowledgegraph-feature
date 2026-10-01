"""Versioned answer prompts, so tuning is a measurement rather than an opinion.

Each version is kept after it is superseded. A prompt change that helps one
failure mode routinely breaks another, and without the earlier versions still
runnable there is no way to tell a real improvement from a lucky rerun.

The model is the one the stack actually runs (`LLM_PROVIDER` / `OPENAI_MODEL_ID`
from docker.env), so the accuracy measured here is the accuracy the product has.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
# Budgeted per item, then per block — NOT by truncating the joined string.
#
# Cutting the concatenation at a fixed length silently amputates whatever ranked
# last, and for a table that means the model receives a header and the first few
# rows of a grid whose lower rows hold the answer. It then correctly reports
# "NOT IN EVIDENCE" for a question whose evidence was retrieved at rank 8 and
# then thrown away between retrieval and the prompt. Dropping a whole passage is
# honest; delivering half a table is not.
_MAX_EVIDENCE_CHARS = 24000
_MAX_ITEM_CHARS = 4000


def _model() -> str:
    return os.environ.get("EVAL_MODEL") or os.environ.get("OPENAI_MODEL_ID") or "gpt-4.1"


def _complete(system: str, user: str, temperature: float = 0.0) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    body = json.dumps(
        {
            "model": _model(),
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.load(resp)
            return (payload["choices"][0]["message"]["content"] or "").strip()
        except urllib.error.HTTPError as e:
            # 429/5xx under a parallel sweep is throughput, not a wrong answer —
            # returning "" here would be scored as a miss and corrupt the run.
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                import time

                time.sleep(2 ** attempt)
                continue
            raise
    return ""


def _evidence_block(hits: list[dict]) -> str:
    parts: list[str] = []
    used = 0
    for i, h in enumerate(hits, start=1):
        text = (h.get("text") or h.get("name") or "").strip()[:_MAX_ITEM_CHARS]
        if not text:
            continue
        head = f"[Evidence {i}]"
        if h.get("paper_title"):
            head += f" {h['paper_title']}"
        if h.get("page") is not None:
            head += f" (page {h['page']})"
        entry = f"{head}\n{text}"
        # Whole items only. A partial passage is worse than an absent one: the
        # model cannot tell a truncated table from a table that never held the
        # answer.
        if used + len(entry) > _MAX_EVIDENCE_CHARS:
            continue
        parts.append(entry)
        used += len(entry) + 2
    return "\n\n".join(parts)


# -- v1: the deployed behaviour ------------------------------------------------
# Mirrors the PAPER PASSAGES and CITATION rules from EugeneDataAgent.system_prompt,
# trimmed to the single-turn retrieval-QA case. This is the baseline: whatever it
# scores is what the product scores today.
_V1_SYSTEM = """You are Eugene, an agent that answers biomedical questions from
passages retrieved out of research PDFs Eugene has ingested.

Answer only from the evidence provided. Do not use outside knowledge. If the
evidence does not contain the answer, say so plainly.
Cite the passage you used by its exact backend-issued label, e.g. [Evidence 3].
Never invent a URL, document id or chunk id."""


def v1(question: str, hits: list[dict]) -> str:
    return _complete(_V1_SYSTEM, f"{_evidence_block(hits)}\n\nQuestion: {question}")


# -- v2: table-aware ----------------------------------------------------------
# v1 treats every passage as prose. Most of the evidence that answers a numeric
# question is a Markdown table, and reading one is a specific skill: find the row
# by its label, find the column by its header, return their intersection. Told
# only to "answer from the evidence", a model that locates the right table still
# returns a neighbouring cell, because nothing directed it to cross-reference two
# axes rather than pattern-match a nearby number.
#
# It also pins down the output shape. "Answer with the cell's exact contents"
# competes with the model's instinct to round, drop a trailing comma, or expand
# "26/41" into a sentence — all of which are wrong answers to a question about
# what a cell says.
_V2_SYSTEM = """You are Eugene, answering questions from passages extracted out of
research PDFs.

Answer only from the evidence provided. Never use outside knowledge, and never
infer a value that is not printed in the evidence.

Many passages are Markdown tables. When the question identifies a row by a label
and a column by a header, resolve it as a lookup, in this order:
  1. Find the table containing that row label.
  2. Locate the header cell matching the requested column, and count which column
     position it occupies.
  3. Read the cell at that row and that column position. Header rows may wrap
     across two lines — count positions in the separator row (| --- |) if the
     header text is split.
Do not answer with a value from a neighbouring column or a neighbouring row
because it looks like the kind of number being asked for.

Reproduce the cell EXACTLY as printed: same digits, same precision, same
parentheses, ranges and signs. Do not round, reformat, convert units, or drop
punctuation. Output the cell contents alone, with no sentence around it.

If the evidence does not contain the requested cell, say exactly:
NOT IN EVIDENCE"""


def v2(question: str, hits: list[dict]) -> str:
    return _complete(_V2_SYSTEM, f"{_evidence_block(hits)}\n\nQuestion: {question}")


REGISTRY = {
    "v1": v1,
    "v2": v2,
}


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(f"unknown prompt {name!r}; have {list(REGISTRY)}")
    return REGISTRY[name]
