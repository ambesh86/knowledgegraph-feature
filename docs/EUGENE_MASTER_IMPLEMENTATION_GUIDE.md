# Eugene — Master Implementation Guide

**Audience:** an engineer who has just joined and has never seen this codebase.
No prior knowledge of RAG, knowledge graphs, or document AI is assumed. Concepts
are explained the first time they appear.

**How to read this:** Part I explains *why the system is shaped the way it is* and
walks four end-to-end journeys. Part II is a function-by-function reference. Read
Part I completely before Part II — the reference will not make sense otherwise.

**Ground rule for this document:** everything here was read out of the code. Where
a number appears (a threshold, a measurement, a timing), it comes from the source
or from a recorded measurement, not from an estimate.

---

## Table of contents

- [0. The one-paragraph mental model](#0-the-one-paragraph-mental-model)
- [1. What runs: the service map](#1-what-runs-the-service-map)
- [2. How many agents, and what framework](#2-how-many-agents-and-what-framework)
- [Part I — The logic, end to end](#part-i--the-logic-end-to-end)
  - [3. Journey A: the nightly sync](#3-journey-a-the-nightly-sync)
  - [4. Journey B: a PDF becomes knowledge](#4-journey-b-a-pdf-becomes-knowledge)
  - [5. Journey C: a question becomes an answer](#5-journey-c-a-question-becomes-an-answer)
  - [6. Journey D: an answer becomes proof](#6-journey-d-an-answer-becomes-proof)
- [Part II — Function reference](#part-ii--function-reference)
  - [7. `ade/fetch.py`](#7-adefetchpy--identifier--pdf-bytes)
  - [8. `ade/storage.py`](#8-adestoragepy--the-key-layout)
  - [9. `ade/parser.py`](#9-adeparserpy--pymupdf-structural-parse)
  - [10. `ade/layout.py`](#10-adelayoutpy--doclayout-yolo-semantics)
  - [11. `ade/tables.py`](#11-adetablespy--rebuilding-the-grid)
  - [12. `ade/detectors.py`](#12-adedetectorspy--visual-chunk-types)
  - [13. `ade/verify.py`](#13-adeverifypy--the-agentic-checking-loop)
  - [14. `ade/enrich.py`](#14-adeenrichpy--domain-tagging)
  - [15. `ade/pipeline.py`](#15-adepipelinepy--the-orchestrator)
  - [16. `ade/indexer.py`](#16-adeindexerpy--writing-into-the-graph)
  - [17. `ade/render.py`](#17-aderenderpy--evidence-images-on-the-fly)
  - [18. `ade/api.py`](#18-adeapipy--the-http-surface)
  - [19. `ingestion/` — the scheduler](#19-ingestion--the-scheduler-and-orchestrator)
  - [20. `foundation/vector/` — retrieval](#20-foundationvector--retrieval)
  - [21. `query/agent/` — the LLM agent](#21-queryagent--the-llm-agent)
- [Part III — The accuracy harness](#part-iii--the-accuracy-harness)
- [Appendix A — Configuration reference](#appendix-a--configuration-reference)
- [Appendix B — Glossary](#appendix-b--glossary)

---

## 0. The one-paragraph mental model

Eugene answers biomedical competitive-intelligence questions and **proves every
answer against the original document**. Each night it discovers new research
papers, downloads the PDFs, and takes them apart into small labelled pieces
("chunks") that each remember exactly where on which page they came from. Those
chunks go into a graph database next to the drugs, diseases and trials they
mention. When a user asks a question, two different search engines run at once —
one lexical, one semantic — and their results are merged into a single ranked
evidence list. A language model reads that evidence and writes the answer, citing
passages by a label the backend issued. When the user clicks a citation, the
system re-opens the original PDF, draws a highlight box at the stored coordinates,
and hands back a PNG. The user sees the actual page.

The last sentence is the whole design goal. Everything else exists to make it
possible.

---

## 1. What runs: the service map

Nine containers, defined in [docker-compose.yml](../docker-compose.yml).

| # | Service | Container | Port (host) | What it is |
|---|---|---|---|---|
| 1 | `neo4j` | `eugene-neo4j` | 17474 / 17687 | Graph database. Entities, relationships, and paper passages. |
| 2 | `atlas_postgres` | `atlas-postgres` | 15432 | Relational store for the workspace UI (conversations, users, artifacts). |
| 3 | `eugene_ws` | `eugene-ws` | 18000 | **Core API.** Graph queries, the vector store, fused retrieval, reranking. |
| 4 | `eugene_mcp` | `eugene-mcp` | 18443 | **Tool server.** Exposes the graph to the LLM as callable tools. |
| 5 | `eugene_agent_ws` | `eugene-agent-ws` | 18001 | **The LLM agent.** Runs the reasoning loop, streams answers. |
| 6 | `eugene_agent_ui_next` | `eugene-agent-ui-next` | 18502 | Next.js web app (the "Atlas" workspace). |
| 7 | `eugene_agent_ui` | `eugene-agent-ui` | 18501 | Older Streamlit UI, still running. |
| 8 | `eugene_ade` | `eugene-ade` | 18100 | **Document extraction.** PDF → chunks → graph, and evidence rendering. |
| 9 | `eugene_ingestion` | `eugene-ingestion` | 18200 | **The nightly scheduler.** |

Two stores sit behind `eugene_ws`:

- **Neo4j** — a *graph* database. Instead of tables and rows it stores **nodes**
  (a drug, a disease, a paper, a passage) and **relationships** between them
  (`(:paper)-[:mentions]->(:drug)`). Good at "what is connected to what", and at
  exact keyword matching through its full-text index.
- **Milvus** (embedded as *milvus-lite*, a single file on disk) — a *vector*
  database. It stores each passage as a list of 384 numbers called an **embedding**
  that captures its meaning, and finds passages whose numbers are close to the
  question's numbers. Good at "find me things that mean roughly this", even when
  no words match.

They are complementary, and §5 explains why the system runs both.

---

## 2. How many agents, and what framework

The word "agent" is used loosely across this repo, so here is the precise answer.

### There is exactly **one** LLM agent

**`EugeneDataAgent`**, in
[agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py](../agents/eugene-agent-ws/src/query/agent/eugene_data_agent.py).

- **Framework:** the **Strands Agents SDK** (`from strands import Agent`), plus
  `strands_tools` for its built-in tools (`current_time`, `http_request`,
  `calculator`, `python_repl`).
- **Pattern:** **ReAct** — *Reason → Act → Observe*. The model thinks about what
  it needs, calls a tool, reads the result, and repeats until it can answer. The
  loop is capped (`max_iterations`) so it cannot spin forever.
- **Memory:** `SlidingWindowConversationManager(window_size=10)` — only the last
  ten turns are kept, so a long conversation cannot overflow the model's context.
  A fresh manager is created *per conversation*, not shared (a shared one leaked
  history between concurrent users).
- **Model:** chosen at runtime by `llm_provider()` in
  [query/conf/conf.py](../agents/eugene-agent-ws/src/query/conf/conf.py) from the
  `LLM_PROVIDER` env var — `bedrock` (default `amazon.nova-lite-v1:0`),
  `anthropic` (default `claude-sonnet-4-20250514`), or `openai` (default
  `gpt-4.1-mini`). The running stack is configured for `openai` / `gpt-4.1`.

### There is one **tool server** (not an agent)

**`eugene-mcp`**, built on **FastMCP**. MCP (Model Context Protocol) is a standard
way to expose functions to a language model. It registers **17 tools**:

`fetch_identity`, `fetch_by_label`, `fetch_similar`, `lookup_node_by_value`,
`fetch_node_details`, `fetch_drug_aliases`, `fetch_facts`,
`fetch_node_relationships`, `has_reachable_path`, `fetch_paths`,
`find_organization_names`, `find_organization_assets`, `search_summaries`,
`search_fused`, `fetch_graph_stats`, `fetch_top_connected_proteins`,
`fetch_shared_gene_diseases`.

The agent connects to it over authenticated streamable HTTP via
`strands.tools.mcp.MCPClient`.

### There is one **"agentic" pipeline that contains no LLM at all**

`eugene-ade` is described as *agentic document extraction*. That word means
something specific here, and it is worth being clear about it because the name
misleads: **no language model participates in extraction.** What makes it agentic
is that it does not blindly run a pipeline and accept the result — it *checks its
own work against quality thresholds and retries differently when the check fails*
([ade/verify.py](../agents/eugene-ade/src/ade/verify.py), §13). That is an
orchestrator with a feedback loop, not a model.

### Summary

| | Count | Framework |
|---|---|---|
| LLM agents | **1** | Strands Agents SDK (ReAct) |
| MCP tool servers | 1 (17 tools) | FastMCP |
| Non-LLM "agentic" pipelines | 1 | Custom verify/retry loop |
| Supporting HTTP services | 6 | FastAPI, Next.js, Streamlit |

---

# Part I — The logic, end to end

---

## 3. Journey A: the nightly sync

**Question this answers: what wakes the system up at 1 a.m., and what does it do?**

### 3.1 Why a container, not a crontab

The scheduler is its own service
([ingestion/scheduler/service.py](../ingestion/scheduler/service.py)) rather than
a `cron` line on the host machine. The reasoning is recorded in the module
docstring: a crontab entry is invisible to `docker compose`, and it was *quietly
lost the first time the box was reprovisioned*. A container ships with the stack,
survives a rebuild, and shows up in `docker compose ps` like everything else.

### 3.2 The trigger

The scheduler uses **APScheduler**, a Python job-scheduling library.

```python
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
scheduler.add_job(
    _execute,
    CronTrigger(hour=CRON_HOUR, minute=CRON_MINUTE, timezone=TIMEZONE),
    id="nightly_ingestion",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)
```

Defaults: **01:00 UTC, daily** (`INGESTION_HOUR=1`, `INGESTION_MINUTE=0`,
`INGESTION_TZ=UTC`). UTC on purpose, so the run time does not shift twice a year
with daylight saving.

Three settings deserve explanation, because they are what makes a scheduler
survive contact with reality:

- **`max_instances=1`** — never run two copies at once.
- **`coalesce=True`** — if the machine was asleep and *five* nightly windows were
  missed, run the job **once** on wake-up, not five times.
- **`misfire_grace_time=3600`** — if the job starts up to an hour late (a slow
  boot, a busy host), still run it. Later than that, skip to tomorrow.

This is registered inside FastAPI's **`lifespan`** — a startup/shutdown hook. The
scheduler starts when the web server starts and shuts down cleanly with it.

### 3.3 Single-flight locking

```python
if _lock.locked():
    return {"status": "skipped", "reason": "run already in progress"}
```

`_lock` is an `asyncio.Lock`. Extraction saturates the CPU, so two overlapping
sweeps would fight for the same cores while doing identical work. APScheduler's
`max_instances=1` covers the cron path; this lock also covers the **manual**
trigger, so a human pressing the button during a scheduled run cannot start a
second one.

The actual work runs via `run_in_threadpool(orchestrator.run)`. This matters: the
orchestrator is *blocking* code (network calls, CPU work). Running it directly
inside an `async` function would freeze the whole event loop and make the service
stop answering health checks. `run_in_threadpool` moves it to a background thread.

### 3.4 What the sweep actually does

[ingestion/src/pipeline/orchestrator.py](../ingestion/src/pipeline/orchestrator.py),
function `run()`:

```
load research_areas.yaml
  └─ for each enabled area:
       ├─ _discover_papers()  → ask Europe PMC for recent papers
       ├─ drop any paper id already seen this run
       └─ for each new paper: _ade_ingest() → POST to eugene-ade
  └─ once, at the end: _refresh_centrality()
```

**The areas are declared in advance**, in
[research_areas.yaml](../ingestion/src/pipeline/config/research_areas.yaml). They
mirror CSL Behring's actual portfolio (hemophilia, hereditary angioedema,
immunoglobulins, and the competitors filed against them). The comment states the
principle plainly: *"the pipeline does not decide what to look for, and the list
is auditable. Adding an area is a config edit, not a code change."*

Defaults per area: `recency_days: 365`, `max_papers_per_area: 12`.

**Why Europe PMC and not PubMed.** PubMed indexes *abstracts*; most of its records
have no downloadable PDF at all. Europe PMC mirrors PubMed **and** exposes
`fullTextUrlList` with per-record PDF links and an open-access flag. Measured
during design: 8 of 8 results carried a PDF link, 6 of 8 were open access. Through
PubMed alone that number would have been near zero — and a pipeline whose job is
to parse PDFs needs PDFs.

**Deduplication.** A paper matching two research areas must not be extracted
twice. The `seen` set handles that. Note the comment: the pipeline *is* idempotent
server-side, but the orchestrator deduplicates anyway rather than relying on it —
belt and braces, because the wasted work would be a full YOLO inference.

**Centrality runs last, and once.** Centrality is a measure of how structurally
important a node is in the graph. That is a property of the **whole corpus**, so
computing it per-document would measure the wrong thing.

### 3.5 Separation of concerns

The orchestrator is deliberately **not a second parser**. It calls
`eugene-ade` over HTTP. The docstring gives the reason: duplicating a YOLO parser
in two processes would mean two model downloads, two sets of weights to keep in
sync, and *two places for a chunking bug to hide*.

> **Ingestion owns *what to fetch and when*. ADE owns *how to parse*.**

### 3.6 Manual controls

| Endpoint | Purpose |
|---|---|
| `GET /health` | Schedule, whether a run is in flight, last result |
| `POST /ingest/run` | Force a sweep now. Returns immediately; poll `/health` |
| `POST /ingest/dry-run` | Discovery only — shows what *would* be fetched, writes nothing |
| `POST /ingest/centrality` | Re-rank the corpus without re-parsing anything |

The last one exists because **parsing is expensive and ranking is cheap**.
Decoupling them lets the whole corpus be retuned without re-extracting it. It is
backgrounded because a synchronous version *died mid-computation the moment a
client timed out*, losing the work with nothing written back.

---

## 4. Journey B: a PDF becomes knowledge

**Question this answers: how does a research paper turn into something searchable
and citable?**

This is the heart of the system. The pipeline is in
[ade/pipeline.py](../agents/eugene-ade/src/ade/pipeline.py), function
`_run_pipeline()`.

```
1. FETCH      resolve an id → download the PDF
2. STORE      put the original bytes in S3, unmodified
3. PARSE      PyMuPDF: exact text + exact coordinates
4. LAYOUT     DocLayout-YOLO: semantic labels, merged onto the chunks
4b. CELLS     rebuild table grids; one chunk per cell
4c. VERIFY    score the extraction; retry differently if it is poor
4d. ENRICH    tag chunks with the drugs/diseases they name
5. ARTIFACTS  write parse.md, chunks.json, grounding.json
6. INDEX      write papers + passages into Neo4j
```

### 4.1 Step 1–2: fetch and store

`fetch_pdf()` queries Europe PMC, picks an open-access record if there is one,
collects candidate PDF URLs (open-access ones first), and downloads.

Two details worth noticing:

**Magic-byte validation.** The downloader checks that the bytes start with
`%PDF-`. It does *not* trust the `Content-Type` header, because *publishers return
HTML paywall pages with a PDF content type*. The first four bytes are the only
trustworthy signal.

**A paywall is a normal outcome, not an error.** `PdfUnavailable` carries a
human-readable reason and the publisher link, so the UI can say "no open-access
PDF — read at publisher" instead of showing a failure. The pipeline records this
as `status: "unavailable"` and moves on.

Then the original bytes go to S3 **unmodified**. This is *the evidence of record*.
Everything downstream is derived; this is the thing that can be checked.

### 4.2 The `doc_id`: why determinism matters

```python
def doc_id_for(source: str, ident: str) -> str:
    raw = re.sub(r"^https?://", "", f"{ident}".strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return slug[:120] or f"{source}_unknown"
```

Same paper in → same id out, forever. That single property gives the pipeline
**idempotency**: re-ingesting a paper hits the same S3 prefix, finds the cached
manifest, and returns immediately.

Why it matters concretely: the UI auto-ingests every result of every literature
search. Without idempotency, a user running the same query twice would pay for the
entire pipeline twice.

**The caching rule is subtle and worth reading carefully:**

```python
if cached and cached.get("status") != "failed":
    return cached          # cache hit
```

- `unavailable` (paywalled) **is** cached — that answer will not change on retry,
  and re-fetching it on every search is pure waste.
- `failed` (network blip, killed container) is **not** cached — it must stay
  retryable, or one bad moment becomes permanent.

The cache check sits deliberately **outside** the concurrency gate, so an
already-extracted document costs one S3 `HEAD` and never queues behind live
extractions.

### 4.3 Step 3: the structural parse (PyMuPDF)

[ade/parser.py](../agents/eugene-ade/src/ade/parser.py) reads the PDF's own
**content stream** — the instructions the PDF itself contains for drawing text.
Nothing here is a model guess. The text and the coordinates are *exact*.

What it **cannot** do is tell you a block is an *abstract* rather than a
*paragraph*. That is semantics, and it needs a model (§4.4).

#### Normalized coordinates — the key idea

Every bounding box is stored as four numbers between 0 and 1, with (0,0) at the
top-left of the page:

```python
{"left": x0/pw, "top": y0/ph, "right": x1/pw, "bottom": y1/ph}
```

A box at `left: 0.1` means "10% across the page", not "72 points from the left".

**This is what makes on-the-fly evidence rendering possible.** The viewer
rasterizes pages at whatever resolution the screen asks for — 96 DPI on a laptop,
300 DPI when zoomed. A pixel coordinate would be wrong at every size except the
one it was captured at. A *fraction* is correct at all of them. §6 shows the
payoff.

#### Deterministic chunk IDs

```python
def _chunk_id(doc_id, ordinal, element_id):
    return hashlib.sha1(f"{doc_id}:{ordinal}:{element_id}".encode()).hexdigest()[:32]
```

Re-parsing an unchanged document reproduces **byte-identical** IDs.

This replaced `uuid.uuid4()`, and the comment explains the bug that forced the
change: the same string is the Neo4j `chunk_id` **and** the Milvus primary key.
There is no join table between the two stores. With random IDs, *every re-ingest
minted new IDs and orphaned every stored evidence link, with nothing in the system
noticing.*

`element_id` is position-based (`p3-blk7`) rather than content-based, on purpose:
a passage whose wording is corrected in a revised PDF is still the same passage in
the same place, so it should keep its identity.

Alongside it, `content_hash` is the SHA-256 of the verbatim text — so a citation
stored years ago can be *proven* to reference the exact same bytes.

#### `markdown_range` — linking chunks to the Markdown

As the parser assembles the Markdown document, it tracks a running character
offset and records the span each chunk occupies:

```python
def _span(text):
    start = md_cursor
    md_cursor += len(text) + 2   # +2 for the "\n\n" join
    return {"start": start, "end": start + len(text)}
```

So a fact extracted from the Markdown can point straight back at the chunk it came
from — by character offset, with no re-searching of the document.

#### Three filters applied during parsing

1. **Marginalia.** Anything entirely within the top or bottom **8%** of the page
   (`_MARGIN_BAND`) is labelled `marginalia`. Running heads and page numbers are
   not evidence and must never be cited as such.

2. **Table overlap.** A text block overlapping a detected table by more than
   **50%** (`_TABLE_OVERLAP`) is skipped, so table content is not emitted twice —
   once inside the table and once as loose text.

3. **Renderable geometry.** A box must have both sides longer than **0.001**
   (`_MIN_BOX_SIDE`, about 0.1% of a page). The reason is specific: rotated text
   — vertical figure labels, sidebar watermarks — comes back from PyMuPDF with
   coordinates *outside* the page rectangle. Normalization clamps those to the
   edge, collapsing the box to zero height. Observed on a real document: 23 chunks
   with `top == bottom == 1.0`, one per rotated trial name. A chunk with no area
   cannot be shown to a user, so emitting it *creates a passage that can be
   retrieved but never proven* — precisely the failure this system exists to
   prevent.

The parser also flags `text_layer: False` when a document yields under 50
characters. That means it is a **scanned image**, not a digital PDF. OCR is not
implemented; the flag makes the gap visible instead of silently returning an empty
parse.

### 4.4 Step 4: the semantic layer (DocLayout-YOLO)

[ade/layout.py](../agents/eugene-ade/src/ade/layout.py) runs an **object detection
model** over a picture of each page. Object detection is normally "find the cats in
this photo"; here it is "find the titles, tables, figures and captions on this
page". The model is `DocLayout-YOLO-DocStructBench`, ~40.7 MB of weights pulled
from HuggingFace and cached on a Docker volume.

It returns labelled boxes and **no text**. PyMuPDF returns text and **no labels**.
Neither is sufficient alone, which is the entire justification for running both.

#### `merge()` — joining the two halves with IoU

**IoU** = *Intersection over Union*. Given two rectangles, it is the area they
share divided by the total area they cover. It is 1.0 for identical boxes and 0.0
for boxes that do not touch — a standard, scale-free way to ask "are these the
same region?"

Each PyMuPDF chunk adopts the label of whichever detected region it overlaps most,
provided the IoU clears **0.15** (`_MIN_IOU`). Below that the region is not really
describing the chunk, and adopting its label would be worse than keeping the
structural default.

One exception, and it is important:

```python
if ch["chunk_type"] != "table":
    ch["chunk_type"] = best["label"]
```

A `table` found structurally by PyMuPDF carries **real cell geometry** read from
the PDF. A predicted box does not. Exact geometry is never downgraded to a
prediction.

#### Measured effect

On a 13-page paper:

| | chunk types |
|---|---|
| PyMuPDF only | `text: 190, marginalia: 28` |
| + DocLayout-YOLO | `text: 167, title: 5, table: 8, caption: 7, footnote: 3, marginalia: 28` |

#### Graceful degradation

If the model or its weights cannot load, `_load_failed` is set **permanently** and
the service logs a warning and returns structural labels only. Retrying the
download on every request would turn a missing model into a latency bug. *A
missing optional model must never take extraction offline.*

### 4.5 Step 4b: rebuilding table grids

This is the cleverest part of the pipeline, and the reason it exists is worth
stating plainly.

**The problem.** PyMuPDF's `find_tables()` returns **zero tables** on the academic
PDFs in this corpus. It works by looking for *ruling lines*, and journal tables are
typically borderless. Measured on page 10 of a real meta-analysis: `find_tables()`
found nothing, while the region genuinely contained **199 positioned words**.

So the only reliable signal that a region *is* a table is the layout model's
label — and the grid inside it has to be derived from scratch, from nothing but
word positions.

**The method** ([ade/tables.py](../agents/eugene-ade/src/ade/tables.py)):

1. Take every word inside the table region, with its rectangle.
2. **Cluster words into rows by vertical overlap** — not by exact `y`, because
   baselines wobble and superscripts sit high. Two words share a row if their
   vertical spans overlap by ≥ **35%** of the shorter one (`_ROW_OVERLAP`).
3. **Derive column boundaries from gaps that recur down the table.** A single
   row's gaps are unreliable (one row may just have a short value). A gap
   appearing at roughly the same *x* in many rows is a real column edge. The
   threshold is **2.2×** the median character width (`_COL_GAP_FACTOR`).
4. **Assign each word to (row, column).** A cell's box is the union of its words'
   boxes.

Guards: fewer than **12 words** (`_MIN_WORDS`) means the region is a caption or a
mis-labelled paragraph — emitting a fake grid would be worse than leaving it
alone. A **400-cell** cap bounds runaway tables.

**Why bother.** A table chunk with one box around the whole table is weak
evidence. A claim like *"injection-site reactions had an odds ratio of 30.94"*
would highlight a 20-row table and leave the reader to find the row. Cell-level
grounding highlights **that cell**.

**Both are kept.** `_expand_table_cells()` keeps the parent table chunk *and* adds
one chunk per cell:

- the **parent** gets its text replaced by a reconstructed Markdown grid
  (`to_markdown()`), because an LLM reading the answer wants the table as a
  readable whole;
- the **cells** carry the fine geometry that makes a single number citable.

Cell IDs derive from the parent's `element_id` plus `(row, col)`, so they are as
deterministic as everything else.

One line in that function fixes a bug worth remembering:

```python
if grounding is not None:
    grounding[cid] = {"page": pno, "box": cell["bbox"], "type": "chunkTableCell"}
```

The renderer (§6) resolves a chunk through `grounding`, **not** through `chunks`.
Without this line a cell would exist but be impossible to render — a 404 on the
one thing cell-level grounding is for.

### 4.6 Step 4c: verification — what makes it "agentic"

[ade/verify.py](../agents/eugene-ade/src/ade/verify.py) scores every extraction on
four measures, each catching a failure the others miss:

| Metric | What it catches | Floor/ceiling |
|---|---|---|
| **text recovery** | characters captured ÷ characters PyMuPDF can see. Catches layout regions that miss whole columns — text present in the PDF, absent from the graph. | ≥ 0.70 |
| **area coverage** | fraction of page area inside chunk boxes. Catches *figures and tables dropped entirely*, which text recovery cannot see because they have no text. | ≥ 0.10 |
| **geometry sanity** | degenerate, inverted or out-of-range boxes. A wrong box points evidence at the wrong part of the page — *worse than no evidence at all*. | ≤ 0.02 |
| **duplication** | the same text under several chunk IDs, which inflates retrieval and double-counts in fusion. | ≤ 0.25 |

If the document fails, the pipeline **retries with different settings** rather
than accepting the result:

```python
{2: {"layout_conf": 0.15, "reason": "lower layout confidence to admit missed regions"},
 3: {"layout_enabled": False, "reason": "structural-only fallback"}}
```

Attempt 2 lowers the detector's confidence threshold to admit regions it was
unsure about — the usual cause of low recovery is a column the model declined to
call text. Attempt 3 abandons the model entirely and falls back to pure structural
parsing.

And critically:

```python
if retry_verdict.score > verdict.score:
    chunks, verdict, parsed = retry_chunks, retry_verdict, reparsed
```

**Keep the better attempt, not merely the last one.**

The verdict is written to the manifest **whether it passed or not**, so a poor
extraction is visible rather than silently degrading every answer built on it.

#### Two lessons encoded in the duplication metric

The duplication check excludes short text and non-indexed types, and both
exclusions were learned from correct documents *failing*:

- Table cells legitimately repeat values — a column of study counts holds "7" many
  times, at different coordinates.
- Short repeated labels are document structure, not error. In a real
  meta-analysis, "Intervention group:" appears 60 times and "Control group:" 23
  times, because each study row carries them. Counting those put duplication at
  **28.6%** and *burned every retry attempt on a problem that did not exist*.

The metric also measures only what will actually be **indexed**. The indexer drops
marginalia and figures, so counting them flagged documents whose furniture had
already been correctly identified and demoted — *the metric disagreed with the
thing it was meant to describe.*

### 4.7 Page furniture: repetition beats position

`_demote_page_furniture()` in `pipeline.py` catches what the 8% margin band
misses: rotated sidebar watermarks and footers sitting just inside the band.

The signal is **repetition across pages, not position**. Text appearing on ≥ 34%
of pages (`_FURNITURE_PAGE_FRACTION`) is furniture whatever its coordinates,
because *a real passage is not reprinted on two-thirds of the document*.

Measured on one PMC manuscript: "Author Manuscript" was emitted 51 times and a
journal footer 50 times, all indexed as substantive text — **101 junk chunks**
each competing for retrieval against real passages.

### 4.8 Step 4d: domain enrichment

[ade/enrich.py](../agents/eugene-ade/src/ade/enrich.py) tags each chunk with the
drugs and diseases it names, so structured retrieval can filter *before* ranking.

The vocabulary is read **from the graph itself** (7,957 drugs, 17,080 diseases)
rather than hardcoded, so it stays in step with whatever has been ingested.

Two guards, both about precision over recall:

- **`_MIN_TERM_LEN = 6`** — short names generate false positives inside ordinary
  prose ("Iron", "Oxygen", "Gold"). *A missed tag is recoverable; a wrong one
  silently pollutes structured filtering.*
- **`_MAX_TAGS = 8`** per chunk — a references section can name forty drugs
  without being *about* any of them.

Matching is word-boundary exact on a normalized form: "Rituximab" is tagged,
"rituximab-adjacent" is not.

### 4.9 Step 5: the artifacts

Four files per document, plus cached renders. The key layout lives in exactly one
place, [ade/storage.py](../agents/eugene-ade/src/ade/storage.py) — scattering
`f"documents/{id}/..."` across modules is how layouts silently drift between the
writer and the reader.

```
documents/{doc_id}/source.pdf                    the original bytes, unmodified
documents/{doc_id}/document.json                 the manifest (metadata, counts, timings)
documents/{doc_id}/parse.md                      the full Markdown
documents/{doc_id}/chunks.json                   chunks with bbox, type, ids, provenance
documents/{doc_id}/grounding.json                chunk_id → {page, box, type}
documents/{doc_id}/renders/{chunk_id}@{dpi}.png  cached evidence images
```

#### What the Markdown looks like

Assembled per page, in reading order:

```markdown
## Page 1

Complement activation and fibrinolysis dysregulation drive contrast-induced...

ABSTRACT Contrast-induced acute kidney injury (CI-AKI) is a major cause of...

## Page 8

| Accession |  | Protein description |  | Gene | (CI-AKI/Sham) |  | p Value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D4A1J3 | Paralemmin 3 |  | Palm3 |  |  | 0.144 | 0.0398 |
```

Reading order is enforced by sorting blocks top-to-bottom then left-to-right, with
coordinates **rounded to one decimal** so blocks on the same visual line are not
split by sub-pixel differences in `y`.

#### What a chunk record looks like

Every chunk in `chunks.json` carries:

| Field | Meaning |
|---|---|
| `chunk_id` | deterministic 32-char SHA-1 — the join key to Neo4j *and* Milvus |
| `chunk_type` | `text`, `title`, `table`, `table_cell`, `caption`, `footnote`, `figure`, `formula`, `marginalia`, `scan_code` |
| `page`, `page_start`, `page_end` | 0-based page index |
| `bbox` | `{left, top, right, bottom}`, all normalized 0–1 |
| `text` | the verbatim text |
| `order` | reading-order position within the document |
| `element_id` | the parser's native handle, e.g. `p3-blk7` |
| `content_hash` | SHA-256 of the text — proves a citation unchanged |
| `markdown_range` | `{start, end}` character span in `parse.md` |
| `parser_confidence` | 1.0 for structural extraction (it is not a guess) |
| `layout_label`, `layout_confidence`, `layout_iou` | what the DL model said, and how well it matched |
| `table_row`, `table_col`, `parent_chunk_id` | cell-level grounding (table cells only) |
| `drugs`, `diseases` | domain tags from enrichment |
| `scan_code_payload`, `visual_confidence`, `heuristic` | visual detectors |
| `doc_id`, `source` | provenance — so a chunk lifted out of context still knows where it belongs |

#### What the manifest contains

`document.json` records `doc_id`, `status`, `metadata` (title, authors, year,
journal, DOI, PMID, PMCID, open-access flag, publisher and Europe PMC URLs),
`pdf_uri`, `pdf_sha256`, `pdf_bytes`, `page_count`, `chunk_count`, `chunk_types`,
`text_layer`, the `verification` verdict, `therapeutic_areas`,
`cell_level_tables`, `layout_model`, per-stage `timings`, `ingested_at`, and
`artifact_version`.

### 4.10 Step 6: indexing into the graph

[ade/indexer.py](../agents/eugene-ade/src/ade/indexer.py) writes the paper and its
passages into Neo4j.

```
(:paper {doc_id, title, doi, pmid, pmcid, year, journal, url})
  -[:has_chunk]-> (:paper_chunk {chunk_id, doc_id, page, bbox_*, text, chunk_type})
(:paper) -[:mentions]-> (:drug | :disease)
```

Without this step the extraction is a dead end: the agent could *cite* a paper but
not *retrieve* what it says.

Four implementation points:

**Batched writes.** Chunks are written with one `UNWIND` — one round trip per
document instead of one per chunk. Documents run to 643 chunks.

**Table cells bypass the length floor.** Ordinary chunks need ≥ 80 characters to
be indexed. Table cells are exempt, because `"30.94 (6.43, 148.75)"` is short and
is *exactly the thing a numeric claim needs to cite*.

**Stale-chunk reconciliation.** Re-extracting a document used to leave its
previous chunks behind: `MERGE` created nodes for the new IDs and the old ones
stayed attached. Observed when 12 documents were re-ingested — the graph grew from
**5,235 to 6,375 chunks**, silently holding two copies of every passage, and
retrieval returned both. The fix deletes chunks not in the current ID set, so
re-ingestion *converges instead of accumulating*.

**Failure is non-fatal.** `index_document` never raises. A graph-write failure
must not invalidate an extraction whose artifacts are already durable in S3. The
result is recorded on the manifest either way.

**Entity linking is name-match only** (~4.5 mentions/paper), scoped to the title
and opening passages, capped at 40 — so a long review cannot emit hundreds of weak
edges. It will miss entities named only by synonym. This is a known limit, not an
oversight.

### 4.11 Concurrency

```python
_ingest_slots = threading.Semaphore(_MAX_CONCURRENT)   # default 2
```

Measured without this cap: a 5-document batch fired **5 concurrent YOLO
inferences** and pushed the container to **1211% CPU**. Every individual document
got slower and the box had nothing left for the graph and vector services sharing
it. Layout detection is CPU-saturating by nature, so the useful concurrency is
small — *queueing is strictly better than thrashing*.

### 4.12 Vector embedding happens elsewhere

Milvus embedding is **not** done by ADE. It runs in `eugene_ws`
(`corpus_ingest_service --labels paper_chunk`), because **milvus-lite is an
embedded single-process store and only one service may open it**. This is a hard
constraint of the storage engine, not a stylistic choice.

---

## 5. Journey C: a question becomes an answer

### 5.1 Why two search engines

Ask: *"which trials evaluate anti-CD20 therapy in lupus?"*

- **Neo4j** is exact and structural. It knows Rituximab **is** a drug node and
  which trials link to it. But a lexical match on "anti-CD20 therapy" misses
  "Rituximab" entirely — the words do not overlap.
- **Milvus** is semantic and fuzzy. It retrieves conceptually related passages
  regardless of wording, so it *does* connect "anti-CD20" to "Rituximab". But it
  has no notion of graph structure or truth.

Running them separately and concatenating gives you two **incomparable score
scales** — a cosine similarity of 0.63 and a Lucene score of 8.07 cannot be
sorted together.

### 5.2 Reciprocal Rank Fusion

[foundation/vector/fusion_search_service.py](../src/foundation/vector/fusion_search_service.py)
merges them with **RRF**:

```
score(d) = Σ over retrievers   weight / (K + rank_in_that_retriever)
```

The trick is that RRF operates on **ranks, not scores**. Cosine similarity and a
Lucene score share no unit — but *"was ranked 3rd"* is perfectly comparable across
both. `K=60` is the value from the original Cormack et al. paper and is the de
facto default; it dampens the influence of the very top ranks so one retriever
cannot dominate.

Weights are deliberately asymmetric: **graph 1.12, vector 1.00**. RRF was designed
assuming sources are interchangeable; that is inverted on purpose. The 12% boost
is enough that a structurally important passage is not buried under generically
similar prose, and small enough that it cannot override strong textual evidence.

Documents found by **both** retrievers are counted as `corroborated` — independent
lexical *and* semantic agreement is the strongest signal available.

### 5.3 Citations the model cannot fake

```python
for i, r in enumerate(results, start=1):
    r["evidence_label"] = f"Evidence {i}"
```

The **backend** issues the citation label. The agent's system prompt forbids it
from ever constructing a URL, document ID or chunk ID for internal evidence — it
may only write `[Evidence 3]`, and the interface resolves that label to the
highlighted region.

This is **prevention rather than detection**. The model has no mechanism for
emitting a false citation, so it cannot emit one. As the prompt puts it: *"A
citation you invent is a fabricated citation even when the underlying fact is
right."*

### 5.4 Optional cross-encoder reranking

Both retrievers are **bi-encoders** in effect: Milvus compares two *independently*
embedded vectors, and Neo4j's index scores term overlap. Neither ever reads the
question and a passage *together*, so neither can tell whether a passage actually
*answers* the question rather than merely resembling it.

A **cross-encoder** does read them together, which is what buys the precision. It
is far more expensive — it must run once per candidate rather than once per query
— so it runs only over the shortlist, after fusion.

[foundation/vector/rerank_service.py](../src/foundation/vector/rerank_service.py)
implements this, opt-in via `?rerank=true`. Two design points matter:

**The model is not an MS MARCO cross-encoder,** which is the obvious default and
is wrong here. MS MARCO is web prose; most evidence in this corpus is tabular. On
the question *"what p value is reported for D4A1J3"*, `ms-marco-MiniLM-L-6-v2`
scored the table **containing** D4A1J3 at −7.49 and the paper's abstract — which
contains no p-values at all — at −1.46. Applied to the whole evaluation set it
drove retrieval@10 **down**, from 43.5% to 6.5%. `BAAI/bge-reranker-base` scores
the same pair 0.99 to 0.20.

**Passages are scored in overlapping windows (MaxP).** The model's 512-token limit
is not a 2000-character limit for a table: Markdown grids tokenize far worse than
prose (`| --- | --- |` is all separators), so a 1422-character table was silently
cut around character 850 and every row below that point was invisible. Scoring
600-character windows and keeping the best score per passage fixed it.

Reranking degrades rather than fails: if the model cannot load, the RRF order
stands.

### 5.5 The agent loop

The agent receives the fused evidence and reasons over **one** ranked,
deduplicated, provenance-tagged list rather than two disjoint blobs.

Its system prompt is assembled fresh per turn from three parts:

1. **A temporal directive** — the current date, *first*, ahead of everything else.
   Without it the model answers "as of now" with its training cutoff (observed: a
   2026 deployment reporting *"as of now means June 2024"*).
2. **A source directive** — which data sources the user enabled (Eugene KG, web,
   PubMed, clinical trials). Under strict source isolation, if the graph lacks the
   answer the agent must **ask for consent** before going outside.
3. **The main system prompt** — tool guide, citation rules, output format.

Safety rails encoded as hard rules: never call the same tool with the same
arguments twice; ≤ 20 tool calls per turn; never invent data; resolve alias nodes
to their canonical entity before declaring "no connection".

---

## 6. Journey D: an answer becomes proof

**This is the payoff, and it is where PyMuPDF earns its place a second time.**

The user clicks `[Evidence 3]`. The browser requests:

```
GET /ade/evidence/{doc_id}/{chunk_id}.png?dpi=150
```

[ade/render.py](../agents/eugene-ade/src/ade/render.py), `render_evidence()`:

```python
1. cache_key = f"documents/{doc_id}/renders/{chunk_id}@{dpi}.png"
   if it exists in S3 → return those bytes. Done.

2. load grounding.json  → {chunk_id: {page, box, type}}
3. look up this chunk   → which page, which normalized box
4. load source.pdf from S3
5. open it with PyMuPDF, seek to that page
6. map the normalized box onto this page's actual rectangle
7. add a translucent highlight annotation
8. rasterize the page to PNG at the requested DPI
9. cache the PNG in S3 (best-effort) and return it
```

### Why rendering on the fly is the right call

A document has hundreds of chunks and only a handful are ever cited. Pre-rendering
every chunk at ingest time would mean hundreds of images per paper, almost all of
them never viewed. Rendering on demand means you pay only for what is actually
looked at — and because renders are cached in S3 afterwards, the *second* view of
the same evidence is a straight object fetch.

### Why normalized boxes are what make it work

```python
def _rect_for(page, box):
    pr = page.rect
    return fitz.Rect(
        pr.x0 + box["left"]   * pr.width,
        pr.y0 + box["top"]    * pr.height,
        pr.x0 + box["right"]  * pr.width,
        pr.y0 + box["bottom"] * pr.height,
    )
```

The stored geometry is a *fraction of the page*. Multiply by the page's real
dimensions at render time and it is correct at 96 DPI, at 300 DPI, and at every
value in between. Had the parser stored pixel coordinates, they would be valid at
exactly one zoom level.

DPI is clamped to **96–300** (`_DPI_MIN`, `_DPI_MAX`) so a malicious or careless
caller cannot request a 10,000-DPI render and exhaust the container's memory.

The highlight is a PyMuPDF **rectangle annotation** with an olive stroke, a lime
fill, and **0.38 opacity** — translucent, so the text underneath stays readable.
The border scales with page width (`page.rect.width * 0.0035`) so it looks the
same on A4 and on US Letter.

### The safety net

```python
pno = max(0, min(doc.page_count - 1, int(entry.get("page", 0))))
```

The page index is clamped to the document's real range. A corrupt grounding entry
produces the wrong page, not a crash.

Caching is wrapped in `try/except` with a warning — *caching is an optimization,
never a hard dependency*. If S3 rejects the write, the user still gets their image.

`render_page()` is the same machinery without the annotation, for plain page
browsing.

### How the browser reaches it

`eugene-ade` is internal to the Docker network. The Next.js app proxies it through
a single catch-all route,
[app/api/atlas/ade/[...path]/route.ts](../agents/eugene-agent-ui-next/app/api/atlas/ade/%5B...path%5D/route.ts).
One pass-through rather than one route per endpoint, so the ~8 ADE routes are not
duplicated in two places. Binary responses (PNGs, PDFs) are streamed through
**untouched** — the whole point of the evidence viewer is that the user sees the
original bytes.

---

# Part II — Function reference

Modules in pipeline order. For each: what it does, why it exists, and the
parameters that matter.

---

## 7. `ade/fetch.py` — identifier → PDF bytes

| Function | Purpose |
|---|---|
| `doc_id_for(source, ident)` | Deterministic, URL-safe slug. Lowercases, strips the scheme, replaces non-alphanumerics with `_`, truncates to 120 chars. **The foundation of idempotency.** |
| `_epmc_query(ident)` | Builds the right Europe PMC query for the identifier flavour: `PMCID:` for `PMC\d+`, `EXT_ID:… AND SRC:MED` for a 5–9 digit PMID, `DOI:"…"` for anything starting `10.`, free text as a last resort. |
| `_select_record(records)` | Prefers an open-access record; otherwise takes the first. |
| `_pdf_urls(record)` | Collects PDF links from `fullTextUrlList`. Open-access links are **inserted at the front** — they are the ones that actually serve bytes. Appends the Europe PMC render endpoint as a fallback. |
| `_metadata_of(record, pdf_url)` | Flattens the Europe PMC record into the metadata dict stored on the manifest. |
| `_download_pdf(url)` | Streams in 64 KB blocks, caps at **60 MB** (`_MAX_PDF_BYTES`), and validates the `%PDF-` magic bytes. |
| `fetch_pdf(source, ident)` | Orchestrates the above. Tries every candidate URL. Raises `PdfUnavailable` when none work. |

`PdfUnavailable` is an **expected outcome** carrying `reason` and `metadata`, not
an error condition.

---

## 8. `ade/storage.py` — the key layout

Six pure functions define every S3 key: `key_pdf`, `key_manifest`, `key_markdown`,
`key_chunks`, `key_grounding`, `key_render(doc_id, chunk_id, dpi)`.

The `Storage` class wraps boto3: `put_bytes`, `get_bytes`, `exists`, `put_json`,
`get_json`, `presign`, `health`.

Two behaviours worth knowing:

- `exists()` treats **404/NoSuchKey/NotFound as a normal answer** (`False`), and
  re-raises anything else as `StorageError`. Swallowing all errors would make a
  permissions failure look like a missing document.
- `health()` **returns** its error rather than raising — a health endpoint that
  500s is useless for diagnosis.

Raw botocore exceptions never escape this module.

---

## 9. `ade/parser.py` — PyMuPDF structural parse

| Function | Purpose |
|---|---|
| `_element_id(page, block_index, kind)` | `p{page}-{kind}{index}` — the parser's native, position-based handle. |
| `_chunk_id(doc_id, ordinal, element_id)` | 32-char SHA-1. Deterministic; the join key between Neo4j and Milvus. |
| `_content_hash(text)` | SHA-256 of verbatim text — proves a stored citation unchanged. |
| `_norm_box(rect, pw, ph)` | Pixel rect → normalized 0–1 box, clamped. **The DPI-independence mechanism.** |
| `_overlap_fraction(a, b)` | Fraction of rect `a`'s area covered by `b`. Used to suppress text inside tables. |
| `_is_renderable(box)` | Rejects zero-area boxes from clamped rotated text. Prevents unprovable passages. |
| `_classify(box)` | `marginalia` if entirely in the top/bottom 8%, else `text`. |
| `parse_pdf(...)` | The main entry point. Returns `markdown`, `chunks`, `pages`, `grounding`, `page_count`, `text_layer`. |

`parse_pdf` processes each page in this order: **tables first** (so overlapping
text can be suppressed), then text and image blocks in reading order, then
page-wide scan-code detection.

Scan codes are detected **page-wide rather than per-region**, because codes are
commonly dropped into margins the layout model calls `abandon` and would be missed
entirely if only figure regions were inspected.

---

## 10. `ade/layout.py` — DocLayout-YOLO semantics

| Function | Purpose |
|---|---|
| `available()` | `True` when enabled and the model has not failed to load. |
| `_get_model()` | Lazy, thread-safe, **sticky-failure** load from HuggingFace. Honours `TORCH_NUM_THREADS` explicitly, because the `OMP_NUM_THREADS` env var alone is not always respected once torch has initialised — and unbounded inference saturates every core. |
| `warm()` | Called from the FastAPI lifespan so the *first user request* is not the one that pays for a 40 MB download. |
| `detect_page(page, dpi=120)` | Rasterizes the page, converts RGB→BGR for OpenCV, runs inference, maps DocStructBench class names to our vocabulary, returns normalized boxes. |
| `_iou(a, b)` | Intersection over Union. |
| `merge(chunks, regions_by_page)` | Assigns each chunk its best-overlapping region's label above IoU 0.15. Never downgrades a structural `table`. |

Label map: `plain text→text`, `abandon→marginalia`, `figure_caption→caption`,
`table_caption→caption`, `table_footnote→footnote`, `isolate_formula→formula`.

---

## 11. `ade/tables.py` — rebuilding the grid

| Function | Purpose |
|---|---|
| `_v_overlap(a, b)` | Fraction of the shorter vertical span two words share. |
| `_group_rows(words)` | Clusters words into visual rows. Compares against the row's **most recent** word, since rows are built left to right and the last word carries the current vertical band. |
| `_column_edges(rows)` | Derives column starts from gaps recurring down the table. Merges starts within 1.5 character widths — the same column, jittered by a proportional font. |
| `extract_cells(page, region, max_cells=400)` | Returns `[{row, col, text, bbox}]`. Allows a 2-point tolerance outside the region, because layout boxes are *predicted* and a word may sit fractionally outside the region it clearly belongs to. |
| `to_markdown(cells)` | Renders cells as a Markdown table with a header separator after the first row. |

---

## 12. `ade/detectors.py` — visual chunk types

Supplies four types DocStructBench does not cover. **Their confidence values are
not comparable, and the module is explicit about it:**

- **`scan_code`** is **real detection**. OpenCV's QR and barcode detectors either
  find and decode a symbol or they do not. Confidence **1.0**, decoded payload
  attached, `heuristic: false`.
- **`logo`, `attestation`, `card`** are **heuristic classifiers** over regions the
  layout model already called `figure`. They score geometry and ink statistics —
  position, aspect ratio, stroke density, colourfulness — and are explicitly
  labelled `heuristic: true` with sub-1.0 confidence so nothing downstream
  mistakes them for model output.

The reasoning: training a real detector would need a labelled corpus that does not
exist here. *A transparent heuristic beats an unlabelled guess, and beats not
detecting them at all.*

They run only on figure regions, so cost scales with the number of images, not
page count.

---

## 13. `ade/verify.py` — the agentic checking loop

| Function | Purpose |
|---|---|
| `_page_text_lengths(pdf_bytes)` | Ground truth for recovery: characters PyMuPDF can see per page. |
| `verify(pdf_bytes, chunks, attempt)` | Computes all four metrics, compares to thresholds, returns a `Verdict`. |
| `retry_settings(attempt)` | The parameter change for the next attempt. |

The composite score is weighted so **recovery dominates**:

```
0.45 × text_recovery
+ 0.25 × min(1, area_coverage / 0.10)
+ 0.15 × (1 − min(1, bad_geometry / 0.02))
+ 0.15 × (1 − min(1, duplication / 0.25))
```

*A document missing half its text is broken even if every box it did emit is
geometrically perfect.*

`text_recovery` is clamped to 1.0, because a table emitted both as a parent and as
cells can exceed it — the clamp keeps the score meaningful rather than rewarding
duplication.

---

## 14. `ade/enrich.py` — domain tagging

| Function | Purpose |
|---|---|
| `tag_chunk(text)` | Returns `{drugs: [...], diseases: [...]}` for one chunk. |
| `document_areas(chunks)` | Rolls chunk tags up into document-level therapeutic areas. |

Vocabulary is loaded from Neo4j once and cached behind a lock.

---

## 15. `ade/pipeline.py` — the orchestrator

| Function | Purpose |
|---|---|
| `ingest(source, ident, force)` | Public entry. Checks the cache **outside** the concurrency gate, then acquires a semaphore slot. |
| `_run_pipeline(...)` | The eight numbered stages, with per-stage timings. |
| `_demote_page_furniture(chunks, page_count)` | Reclassifies text repeated on ≥ 34% of pages as marginalia. |
| `_expand_table_cells(pdf_bytes, chunks, doc_id, grounding)` | Adds one chunk per cell; replaces the parent's text with reconstructed Markdown; **writes cell grounding entries**. |
| `_detect_layout(pdf_bytes)` | Runs the detector over every page. |
| `get_manifest(doc_id)` | Reads `document.json`, or `None`. |
| `reindex(doc_id)` | Re-runs **only** graph indexing from existing S3 artifacts. |
| `list_documents()` | Paginates S3 prefixes to list every ingested `doc_id`. |
| `ingest_safe(source, ident, force)` | `ingest` that **persists** unexpected errors as a `failed` manifest. |

`reindex` exists because extraction is expensive (YOLO ~40 s/document) and
indexing is cheap. A schema change must not force a full re-extraction of the
corpus.

`ingest_safe` matters more than it looks. *Returning* an error is not enough: a
background task's return value goes nowhere. A document whose pipeline died midway
left `source.pdf` in S3 with **no manifest**, and read as "never ingested" forever
— observed after a container restart killed an in-flight extraction. Writing the
failure means the UI can say "extraction failed, retry" instead of silently
offering nothing. The record carries `retryable: True`.

---

## 16. `ade/indexer.py` — writing into the graph

| Function | Purpose |
|---|---|
| `available()` | Whether graph indexing is enabled. |
| `_normalize(name)` | Lowercase, strip parentheses and non-word characters, collapse whitespace. |
| `ensure_schema()` | Idempotent constraints and indexes, including the `paper_chunk_fulltext` full-text index the graph retriever hits. |
| `index_document(manifest, chunks)` | Writes the paper node, batches chunks via `UNWIND`, reconciles stale chunks, links entities. Never raises. |
| `_link_entities(drv, doc_id, meta, chunks)` | Word-boundary name matching against drug/disease nodes, scoped and capped. |

Entity linking is scoped to the title plus the first few substantive chunks —
scanning every chunk of a 643-chunk review would match dozens of incidentally
mentioned drugs and *make `mentions` meaningless*. Names shorter than 6 characters
are excluded because they match far too eagerly inside prose.

---

## 17. `ade/render.py` — evidence images on the fly

| Function | Purpose |
|---|---|
| `_rect_for(page, box)` | Maps a normalized box onto the page's coordinate rect. **The DPI-independence payoff.** |
| `render_evidence(doc_id, chunk_id, dpi=150)` | Cache → grounding → PDF → annotate → rasterize → cache → return PNG. |
| `render_page(doc_id, page_no, dpi=150)` | Plain page render, no highlight. |

`EvidenceUnavailable` is raised when the document was never ingested or the chunk
has no grounding entry; `api.py` maps it to a 404.

---

## 18. `ade/api.py` — the HTTP surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + S3 reachability + layout-model status |
| POST | `/ade/ingest` | Run the pipeline for one document (idempotent) |
| POST | `/ade/ingest/batch` | Queue up to 25 documents for background extraction |
| POST | `/ade/reindex` | Re-index from S3 artifacts; `?doc_id=` for one |
| GET | `/ade/documents/{doc_id}` | The manifest |
| GET | `/ade/documents/{doc_id}/chunks` | Chunks, filterable by `chunk_type` and `page` |
| GET | `/ade/documents/{doc_id}/markdown` | `parse.md` |
| GET | `/ade/documents/{doc_id}/pdf` | The original PDF |
| GET | `/ade/evidence/{doc_id}/{chunk_id}.png` | **The highlighted proof image** |
| GET | `/ade/page/{doc_id}/{page_no}.png` | Plain page render |

**Every handler that touches PDF work uses `run_in_threadpool`.** PyMuPDF, YOLO
and S3 are all blocking and CPU-bound; doing that work inline would stall the
event loop and make concurrent requests queue behind a single 40-page parse.

The batch endpoint exists to pre-warm evidence for a whole result set, so the
paper is already extracted by the time the user clicks it.

Evidence responses carry `Cache-Control: public, max-age=86400` — renders are
deterministic for a given `(doc, chunk, dpi)`.

---

## 19. `ingestion/` — the scheduler and orchestrator

**`scheduler/service.py`**

| Function | Purpose |
|---|---|
| `_execute(trigger)` | Single-flight guard, then `run_in_threadpool(orchestrator.run)`. Records timing and result in `_state`. |
| `lifespan(app)` | Registers the cron job at startup, shuts the scheduler down cleanly. |
| `health()` | Schedule + `_state`. |
| `trigger(background)` | `POST /ingest/run` — queues a sweep, returns immediately. |
| `dry_run()` | `POST /ingest/dry-run` — discovery only. |
| `_centrality(trigger)` / `centrality_only(...)` | `POST /ingest/centrality` — re-rank without re-parsing. |

**`src/pipeline/orchestrator.py`**

| Function | Purpose |
|---|---|
| `load_config(path)` | Reads `research_areas.yaml`. |
| `_discover_papers(query, limit, recency_days)` | Europe PMC search with a `FIRST_PDATE` window. Prefers PMCID (resolves directly to the OA PDF endpoint), falls back to PMID. |
| `_ade_ingest(item)` | `POST /ade/ingest`, 600 s timeout — extraction is minutes-scale per document. |
| `_refresh_centrality()` | Delegates to `centrality_step.run()`. |
| `run(config_path, dry_run)` | The full sweep. Returns a summary with per-area counts and elapsed time. |

---

## 20. `foundation/vector/` — retrieval

**`vector_search_service.py`** — the Milvus client and the embedding model
(`all-MiniLM-L6-v2`, 384 dimensions, forced to CPU because the shared provider
hardcodes `device='mps'`, which only exists on macOS).

> A hard-won note preserved in that file: the environment variable is
> `EUGENE_MILVUS_URI`, **not** `MILVUS_URI`. pymilvus reads a bare `MILVUS_URI`
> into its own global config at *import* time and demands an `http(s)://` address
> — so pointing it at a milvus-lite file path made `import pymilvus` raise and
> **silently disabled the entire vector subsystem**.

**`fusion_search_service.py`**

| Function | Purpose |
|---|---|
| `_ensure_fulltext_index()` | Creates the fusion indexes once. Passages are indexed on `text`, not `node_name` — the name is only a 200-char preview, so indexing it would make most of a paper unsearchable. |
| `_graph_search(query, top_k, boost)` | Lucene full-text over two unioned indexes. Escapes Lucene special characters so user text cannot break the parser or inject query syntax. |
| `_corpus_count()` / `_doc_freq(term)` / `_boosted_query(safe)` | IDF term boosting (see below). Document frequencies are cached — they change only on ingest. |
| `_vector_search(query, top_k)` | Milvus nearest neighbours. Degrades to graph-only if the corpus collection is missing. |
| `fuse(graph_hits, vector_hits, top_k)` | Weighted RRF, deduplicated by `node_index`. |
| `search(query, top_k, candidates, rerank)` | Runs both retrievers concurrently, pre-ranks by intent, fuses, optionally reranks, issues evidence labels. |
| `health()` | Readiness of **both** retrievers. |

Two subtleties in `search()` worth understanding:

**Intent pre-ranking happens *before* fusion, not after.** RRF consumes rank
position, so re-ordering the graph hits beforehand is what actually changes the
fused result. Doing it afterwards would have no effect at all.

**IDF boosting is gated behind `rerank`.** BM25 already weights terms by inverse
document frequency, but it *sums* those weights across every matching term. A
natural question carries the paper's whole title, so a passage repeating fifteen
ordinary title words outscores the one passage containing the single identifier
being asked about — measured, the right table fell from rank 2 to rank 133.
Boosting each term by its IDF a second time fixes that. But *on its own it made
things worse* (fused retrieval@10 fell from 38.5% to 28.3%), because RRF
re-dilutes the sharpened ordering. So it is applied only when the caller will
rerank; the default path is unchanged.

**`rerank_service.py`**

| Function | Purpose |
|---|---|
| `available()` | Enabled and not permanently failed. |
| `_get_model()` | Lazy, thread-safe, sticky-failure load of `BAAI/bge-reranker-base`. |
| `_windows(text)` | Splits long passages into 600-char windows with 150-char overlap, max 6. |
| `_passage(hit)` | The passage body **only** — deliberately *not* prefixed with the paper title (see below). |
| `rerank(query, hits, top_k)` | One flat batch across every window of every candidate; keeps the max score per candidate. |

Why `_passage` excludes the title: questions routinely *name the paper*, so
attaching the title makes every chunk of that paper carry a span matching the
question. Measured, ten passages from one paper came back at 0.9994–0.9999 and the
table holding the answer did not make the top ten. Scoring the bare body separates
them — the same table scores 0.9948 against 0.1336 for prose from the same paper.

The candidate cap (default **60**) *is* the latency budget: this model costs
roughly 0.46 s per candidate on CPU, so 200 candidates measured 91 s.

---

## 21. `query/agent/` — the LLM agent

| Function | Purpose |
|---|---|
| `EugeneDataAgent.execute(...)` | Synchronous run. Builds an MCP client, initialises the agent, runs one turn. |
| `EugeneDataAgent.execute_stream(...)` | Streaming run with retries. Nova models occasionally emit an invalid tool-use sequence; each retry gets a **fresh session id** so the failed turn's partial state is not replayed into the model. |
| `_init_agent(...)` | Selects tools from the enabled sources, deduplicates by identity, assembles the three-part system prompt, caps ReAct iterations. |
| `_build_mcp_client(token)` | Authenticated streamable-HTTP MCP client. TLS verification defaults to **on**; dev can opt out via `EUGENE_MCP_VERIFY_SSL=false`. |
| `_snapshot_date()` | Reads `/health/data-freshness` from the core API, cached 15 minutes, so the agent can **date internal facts honestly** instead of implying they are current. |
| `build_temporal_directive(...)` / `build_source_directive(...)` | The first two prompt sections. |
| `_extract_tool_events(...)` | Turns Strands events into the tool-chip stream the UI renders. |

---

# Part III — The accuracy harness

[eval/](../eval/) measures whether any of this actually works. Full detail is in
[eval/README.md](../eval/README.md); the summary:

**Ground truth comes from table cells**, because they are the only part of the
corpus where the correct answer is knowable without a human labeller. A cell
reading `0.0398` under the header `p Value` in the row `D4A1J3` yields an
unambiguous question and an unambiguous answer, anchored to a chunk with a
bounding box.

**Two numbers are reported separately**, because they fail for different reasons:
*retrieval@k* (did the evidence reach the model?) and *answer accuracy* (given
what arrived, was the cell reproduced exactly?). A low retrieval number is a
ranking problem; a high retrieval number with a low answer number is a prompt
problem.

**Final result on the 46-question set:** 100% retrieval@15 and 100% answer
accuracy on natural phrasing, reproduced identically across three runs. Baseline
was 26.1%.

Files: `gold.py` (builds the question set from Neo4j), `harness.py` (runs and
scores), `prompts.py` (versioned answer prompts — superseded versions stay
runnable so an improvement can be *shown* rather than asserted), `rerank.py`
(reranker registry, including a Cohere client that needs only `COHERE_API_KEY`).

---

# Appendix A — Configuration reference

### Extraction (`eugene_ade`)

| Variable | Default | Effect |
|---|---|---|
| `ADE_S3_BUCKET` | — | **Required.** Artifact bucket |
| `AWS_REGION` | `us-east-1` | |
| `ADE_LAYOUT_ENABLED` | `true` | `false` skips the DL model entirely |
| `ADE_LAYOUT_CONF` | `0.25` | YOLO confidence threshold |
| `ADE_LAYOUT_MIN_IOU` | `0.15` | Below this, a region does not relabel a chunk |
| `ADE_LAYOUT_IMGSZ` | `1024` | Inference image size |
| `ADE_MAX_CONCURRENT_INGESTS` | `2` | Extraction slots |
| `ADE_GRAPH_INDEX_ENABLED` | `true` | `false` skips the Neo4j write |
| `TORCH_NUM_THREADS` | unset | Caps torch intra-op threads |

### Scheduling (`eugene_ingestion`)

| Variable | Default | Effect |
|---|---|---|
| `INGESTION_HOUR` | `1` | Nightly hour |
| `INGESTION_MINUTE` | `0` | Nightly minute |
| `INGESTION_TZ` | `UTC` | Timezone |
| `INGESTION_ADE_TIMEOUT_S` | `600` | Per-document extraction timeout |
| `INGESTION_CONFIG` | `research_areas.yaml` | Which areas to sweep |

### Retrieval (`eugene_ws`)

| Variable | Default | Effect |
|---|---|---|
| `EUGENE_MILVUS_URI` | `/app/.db/eugene_vectors.db` | **Not** `MILVUS_URI` — see §20 |
| `EUGENE_RERANK_ENABLED` | `true` | Master switch for reranking |
| `EUGENE_RERANK_MODEL` | `BAAI/bge-reranker-base` | Cross-encoder |
| `EUGENE_RERANK_MAX_CANDIDATES` | `60` | Candidate cap == latency budget |
| `EUGENE_RERANK_WINDOW` | `600` | MaxP window size in characters |
| `HF_HOME` | `/app/.hf_cache` | Model cache volume |

### Agent (`eugene_agent_ws`)

| Variable | Default | Effect |
|---|---|---|
| `LLM_PROVIDER` | auto-detect | `bedrock` \| `anthropic` \| `openai` |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | |
| `ANTHROPIC_MODEL_ID` | `claude-sonnet-4-20250514` | |
| `OPENAI_MODEL_ID` | `gpt-4.1-mini` | |
| `EUGENE_MCP_VERIFY_SSL` | `true` | Dev-only opt-out |
| `EUGENE_AGENT_MODEL_RETRIES` | `3` | Retries on transient model errors |

---

# Appendix B — Glossary

**Bi-encoder** — a model that embeds the query and the document *separately*, then
compares the vectors. Fast (documents are embedded once, offline) but it never
sees the two together.

**BM25** — the standard lexical relevance formula. Scores a document by how many
query terms it contains, weighted by how rare each term is, adjusted for document
length.

**Bounding box (bbox)** — a rectangle locating something on a page. Here, always
four numbers between 0 and 1.

**Chunk** — one extracted piece of a document: a paragraph, a title, a table, a
single table cell. The unit of retrieval and of citation.

**Content stream** — the instructions inside a PDF that say what to draw and
where. Reading it gives exact text and exact geometry; nothing is inferred.

**Cross-encoder** — a model that reads the query and the document **together** in
one pass. Much more accurate than a bi-encoder, much more expensive: it must run
once per candidate rather than once per query.

**Embedding** — a list of numbers representing meaning. Similar meanings produce
nearby vectors. Here, 384 dimensions from `all-MiniLM-L6-v2`.

**Grounding** — the mapping from a chunk ID to its page and box. What makes an
answer provable.

**Idempotent** — doing it twice has the same effect as doing it once.

**IDF** — Inverse Document Frequency. How rare a term is across the corpus. Rare
terms carry more signal: "D4A1J3" says far more about which passage you want than
"kidney" does.

**IoU** — Intersection over Union. Overlap area ÷ total area. 1.0 = identical,
0.0 = disjoint.

**Lifespan** — FastAPI's startup/shutdown hook. Used here to warm the YOLO model
and to start the cron scheduler.

**Manifest** — `document.json`. Everything known about one extracted document.

**Marginalia** — running heads, footers, page numbers. Not evidence, never cited.

**MaxP** — scoring a long document by its best-scoring window rather than by its
first N tokens.

**MCP** — Model Context Protocol. A standard for exposing functions to a language
model as callable tools.

**Normalized coordinates** — positions as fractions of page size rather than
pixels. The reason evidence renders correctly at any DPI.

**ReAct** — Reason → Act → Observe. The agent loop: think, call a tool, read the
result, repeat.

**RRF** — Reciprocal Rank Fusion. Merges ranked lists from different systems using
rank position rather than score, so incomparable scales can be combined.

**Threadpool** — where blocking work runs so it does not freeze the async event
loop.
