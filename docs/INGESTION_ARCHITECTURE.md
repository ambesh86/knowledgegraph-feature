# Eugene Ingestion Pipeline — architecture

A standalone, modular nightly pipeline that prepares research evidence **before** the
backend ever sees it. Modelled on `bt-agentcore-ingestion`, with the two datastore
substitutions this project requires:

| Reference architecture | Eugene |
|---|---|
| Amazon Neptune (RDF) | **Neo4j** (property graph) |
| Redis Vector Search | **Milvus** (milvus-lite, embedded) |
| LandingAI ADE (API key) | **Local ADE** — PyMuPDF + DocLayout-YOLO |
| S3 | S3 (unchanged) |

## 1. Why ingestion is a separate module

The backend answers questions; the pipeline manufactures the evidence it answers from.
They have different dependency sets (YOLO/OpenCV vs a graph API), different failure
profiles (long-running batch vs request/response), and different schedules (nightly vs
always-on). Mixing them means a parser crash can take graph search offline, and a model
download can block a deploy.

So: `ingestion/` owns writing. The backend owns reading. The handoff is the graph and the
vector index — nothing else.

## 2. Pipeline stages

```
                    ┌─── nightly 01:00 ───────────────────────────────┐
research_areas.yaml │                                                 │
        │           ▼                                                 │
        └──► source_sync ──► parse_chunk ──► schema_extract(M3, off) ──┤
             (PubMed,        (PyMuPDF +      (LLM, evidence-linked)    │
              CT.gov,         DocLayout-                               │
              EuropePMC)      YOLO)                                    │
                                 │                                     │
                                 ▼                                     │
                       embed ──► neo4j_load ──► milvus_load            │
                                     │                                 │
                                     ▼                                 │
                              centrality (M4/M5) ──► manifest ─────────┘
                                     │
                                     ▼
                      Backend reads: graph + index (never writes)
```

Every step is a `BasePipelineStep` with `validate_config`, `validate_input`, `execute` —
the same contract the reference repo uses, so steps stay independently testable and
re-runnable.

## 3. The seven mechanisms, mapped to code

### M1 — the chunk is a graph object
`(:paper_chunk:evidence_span)` — dual-typed, carrying verbatim `text`, `page`,
normalized `bbox_*`, `chunk_type`, **`parser_confidence`**, and **`content_hash`** as
ordinary queryable properties. Not a sidecar; not JSON in a blob.

### M2 — one identity, two databases
```
chunk_id = sha1(f"{doc_id}:{ordinal}:{element_id}")[:32]
```
Deterministic from document identity, position and the parser's element id. The **same
string** is the Neo4j `chunk_id` and the Milvus primary key. No join map — the class of
bug where a citation drifts to the wrong paragraph is removed, not mitigated.

> **This replaces `uuid.uuid4()`, which the previous build used.** Re-parsing a document
> produced entirely new ids and silently orphaned every stored evidence link. Fixing this
> is the precondition for everything else.

### M3 — parser-emitted evidence links *(scaffolded, disabled)*
Interface fixed, execution off. When enabled: schema-constrained extraction returns, per
field, the element ids it read from; those become `(:fact)-[:evidence]->(:paper_chunk)`
edges, and a load-time constraint rejects any fact with zero evidence edges.

### M4 — composite centrality that degrades gracefully
Seven metrics, each normalized 0–1, blended with fixed weights:

| Metric | Weight | Answers |
|---|---|---|
| PageRank | 0.28 | globally authoritative passages |
| Degree | 0.16 | direct connectivity |
| Betweenness | 0.16 | bridging passages between topics |
| Closeness | 0.12 | reachability |
| Eigenvector | 0.10 | prestige via important neighbours |
| Katz | 0.06 | direct + indirect influence |
| Harmonic | 0.12 | reachability across disconnected components |

A **node-count guard** skips metrics that are infeasible at scale, and the composite
**renormalizes over whichever metrics actually ran**, preserving the 0–1 contract. Above
the threshold the surviving PageRank/degree/betweenness weights renormalize
(0.28, 0.16, 0.16) → (0.467, 0.267, 0.267) automatically.

### M5 — centrality written back as replaceable properties
Scores land on the existing nodes (`centrality_pagerank` … `centrality_composite`). Old
properties are deleted before new ones are written, so refreshes are repeatable and never
accumulate stale values. Consequence: **ranking can be retuned without re-parsing a single
PDF** — the expensive stage is decoupled from the cheap one.

### M6 — intent-conditioned pre-ranking, then asymmetric fusion
Graph results are pre-ranked by a weighted blend of evidence quality, composite
centrality, ontology match and query-term overlap, with weights selected by question
intent:

| Intent | Quality | Centrality | Ontology | Text |
|---|---|---|---|---|
| default | 0.40 | 0.22 | 0.20 | 0.18 |
| interpret | 0.36 | 0.24 | 0.22 | 0.18 |
| compare | 0.38 | 0.18 | 0.22 | 0.22 |
| quantify | 0.44 | 0.10 | 0.18 | 0.28 |
| diagnose | 0.32 | 0.26 | 0.24 | 0.18 |
| communicate | 0.42 | 0.14 | 0.20 | 0.24 |

Then RRF (k=60) with **unequal source weights: vector 1.00, graph 1.12**. The 12% boost is
large enough that a structurally important passage isn't buried under generically similar
prose, small enough that it can't override strong textual evidence.

*(The previous build used a flat 1.2 graph weight with no intent conditioning.)*

### M7 — the model cannot invent a citation
The LLM emits only `[Evidence N]` labels. The UI resolves each label against backend
metadata to produce the link. A model with no mechanism for emitting a URL cannot emit a
false one — structural, not statistical.

## 4. Research areas are declared, not discovered

`config/research_areas.yaml` lists the areas to sweep, each with its source queries and
recency window. The nightly run iterates them. Adding an area is a config edit, not a code
change.

## 5. Scheduling

A `eugene_ingestion` service in docker-compose runs a supervisor that fires the pipeline at
**01:00 daily**, plus an HTTP trigger for on-demand runs. Idempotent throughout: unchanged
documents are skipped by content hash, so a re-run costs almost nothing.

## 6. Honest position on accuracy

The brief reports citation accuracy 0.71 → 0.95 → 0.968 with centrality, on 15 questions
over 42 documents. That is a pilot, not a benchmark, and the same caveat applies here —
more so, since our corpus is currently 12 papers. What this pipeline delivers is the
*mechanism* for that gain (M4–M6) and the *traceability* that makes errors visible rather
than silent. Claiming a specific accuracy number before measuring it on this corpus would
be exactly the overclaiming the brief warns against.
