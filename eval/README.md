# eval — measuring retrieval and answer accuracy

A reproducible accuracy harness for the fused-retrieval + answer path, built on
ground truth that needs no human labeller.

```bash
python eval/gold.py                                          # rebuild the gold set
PYTHONPATH=eval python eval/harness.py --k 10 --pool 200 \
    --rerank service --phrasing natural --prompt v2 --answer --workers 2
```

## Where the ground truth comes from

Table cells. They are the only part of this corpus where the correct answer is
knowable mechanically: a row reading
`Injection site reactions | 4 | 26/41 | 0/38 | 30.94 (6.43, 148.75) | <0.0001`
gives an unambiguous question and an unambiguous answer, anchored to a chunk with
a bounding box. `indexer.py` deliberately exempts table cells from the length
floor, so every cell is a real, retrievable, citable node — the eval scores the
same objects the product serves.

Ground truth is read from **Neo4j**, not from the S3 artifacts. The graph is what
retrieval actually queries; a gold answer read out of S3 can describe a chunk
that was never indexed, which measures the extractor rather than the system.

### What makes a question admissible

The generator is strict, because an ambiguous question caps accuracy for reasons
that have nothing to do with the system:

| Rule | Why |
|---|---|
| Cells grouped by `parent_chunk_id`, never by page | Two tables on one page share row indices; grouping by page interleaves them and yields gold answers from the wrong table |
| Question names both the row label and the column header | "What value was reported for X?" has five defensible answers in a five-column row |
| Row label unique within its table | A repeated label cannot identify a row |
| Answer cell unique within its table | Otherwise a lucky hit on another row grades as correct |
| Answer cell must be a **statistic**, not prose | A wrapped prose fragment is a symptom of a scrambled parse and has no single correct answer |
| Header must read as a name — no arrows, no `NCT…` ids | `↓ hsCRP` is table *data*; when it lands in the header row the parser folded a data row into the header |
| Row label and header must have balanced brackets | `(JAK-STAT` is the left half of a cell the parser cut at a line wrap |
| Row/column association confirmed against the table's own Markdown | The cell grid and the rendered Markdown are independent products of the same parse; if they disagree, the grouping is wrong |

**These filters reject the majority of candidate rows**, and that rejection rate
is itself a finding: it measures how often table extraction scrambles a grid, and
it is reported separately rather than hidden. It is not a way of deleting hard
questions — every rule is a property of the question, decidable without running
the system.

## What is measured

Two numbers, kept apart because they fail for different reasons:

* **retrieval@k** — did the evidence reach the model at all? A hit is the gold
  cell *or* its parent table chunk; both carry the value.
* **answer accuracy** — given what retrieval returned, was the cell reproduced
  exactly?

A low retrieval number is a reranking or recall problem. A high retrieval number
with a low answer number is a prompt problem. One combined score hides which
lever to pull.

Grading normalizes only what the PDF itself is inconsistent about — whitespace,
unicode dash variants, wrapping quotes. It never rounds: `0.0398` and `0.04` are
different answers.

## Two phrasings

`--phrasing quoted` asks with the row label and column header in quotes.
`--phrasing natural` asks the way a person would, with no quotes at all.

The distinction matters more than it looks. A lexical reranker that keys off
quoted spans scores 100% on the quoted form and **0%** on the natural one — the
quoted form silently hands it the answer. Any accuracy claim that does not say
which phrasing it used is not a claim about the product.

## Results

46 questions, 9 tables, 4 documents. Answer model `gpt-4.1` (the stack's
configured provider), temperature 0.

All figures below are on the **same final 46-question set**, so they are directly
comparable. (Intermediate numbers quoted during development were measured on
earlier, looser versions of the set and are not comparable to these.)

| Configuration | phrasing | retrieval@k | answer |
|---|---|---|---|
| Baseline — service defaults, deployed prompt, k=20 | natural | 26.1% | — |
| Baseline — service defaults, k=20 | quoted | 10.9% | — |
| Final — pool 200 + bge rerank + MaxP windows, k=15, prompt v2 | natural | **100%** | **100%** |
| Final config but prompt v1 | natural | 100% | 97.8% |
| Final config | quoted | 56.5% | 56.5% |

The final natural-phrasing configuration was run **three times** and produced
identical numbers each time (retrieval@15 100%, mean rank 3.87, answer 100%);
retrieval is deterministic and the answer model runs at temperature 0.

The v1-vs-v2 row is the prompt ablation: at *identical* retrieval, the reworked
prompt is worth 97.8% → 100%. That single question is the difference between
missing and clearing the 98% target, so the prompt work was necessary — but it
was the last 2%, not the first 74%.

### The quoted-phrasing caveat

The reranked configuration scores only 56.5% on the quoted phrasing. That form is
an artefact of the generator — it wraps the row label and column header in quotes
and appends answer-format instructions — and a cross-encoder handed an
instruction-laden string rather than a question degrades badly. Answer accuracy
*given retrieval* is still 100% there, so it is purely a reranking effect.

It is reported rather than tuned away, because it is a genuine robustness limit:
a user who writes a long, instruction-heavy prompt gets the weaker behaviour.

### What the failures actually were

Almost none of it was the prompt.

1. **The candidate pool was capped at 60 per retriever.** A reranker can only
   reorder what it is handed, so this capped recall at 73% before anything else
   ran.
2. **Query dilution.** Asking for accession `D4A1J3` alone ranks the right table
   2nd; asking inside a full sentence ranks it 133rd, because BM25 sums term
   weights and the paper's title contributes fifteen ordinary words. Boosting
   each term by its IDF a second time fixed it — but **only in combination with
   reranking**. On its own it moved fused retrieval@10 *down* (38.5% → 28.3%),
   because RRF re-dilutes the sharpened lexical ordering. It is therefore applied
   only when the caller asks for reranking; the default path is unchanged, and
   that was verified by re-measuring it after the change.
3. **Intent pre-ranking was shortlisting for the reranker.** Its `text` signal is
   unweighted term overlap, which favours long prose over a compact table, moving
   the answer from lexical rank 2 to 89.
4. **The obvious cross-encoder was the wrong one.** `ms-marco-MiniLM-L-6-v2`
   scored the table containing the answer at −7.49 and the abstract at −1.46, and
   *lowered* retrieval@10 from 43.5% to 6.5%. MS MARCO is web prose; most
   evidence here is tabular.
5. **Prepending the paper title to each passage destroyed discrimination.**
   Questions name the paper, so every chunk of it matched and ten passages came
   back at 0.9994–0.9999.
6. **512 tokens is not 2000 characters for a table.** Markdown grids tokenize ~6x
   worse than prose, so a 1422-character table was cut around character 850 and
   its lower rows were invisible. Scoring overlapping windows and keeping the best
   fixed every remaining retrieval miss.
7. **The evidence block was truncated as one joined string**, amputating whatever
   ranked last. A table retrieved at rank 8 reached the model as a header and
   three rows, and the model correctly said the answer was not there.

The prompt contributed one fix of the seven — v2 adds the row/column lookup
procedure and pins the output to exact cell contents. It is worth having, but the
accuracy was in the retrieval path.

## Cost

Reranking is opt-in (`?rerank=true`) and is **not** on by default, because on CPU
it costs ~30s per query at 60 candidates. That is fine for an offline eval and
too slow for an interactive answer. Before enabling it in the product, either put
the reranker on a GPU or use a hosted rerank API — `--rerank cohere` is already
wired and needs only `COHERE_API_KEY`.

## Knobs

| Flag | Meaning |
|---|---|
| `--k` | evidence items handed to the model |
| `--pool` | candidate depth per retriever before reranking |
| `--rerank` | `none`, `service` (the cross-encoder in eugene_ws), `cohere` (needs `COHERE_API_KEY`), `lexical` (dependency-free, quoted-form only) |
| `--prompt` | answer prompt version; superseded versions stay runnable so a change can be shown to be an improvement |
| `--workers` | parallel questions — keep at 2 with `--rerank service`, which is CPU-bound |

Prompt versions are never edited in place. A prompt change that fixes one failure
mode routinely breaks another, and without the earlier version still runnable
there is no way to tell a real improvement from a lucky rerun.
