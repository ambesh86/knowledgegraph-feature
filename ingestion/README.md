# Eugene Ingestion Pipeline

Standalone nightly pipeline that prepares research evidence **before** the backend
sees it. Modular and separately deployable, modelled on `bt-agentcore-ingestion`.

**Runs on `http://localhost:18200`** · sweeps at **01:00 UTC daily**

| Reference architecture | Eugene |
|---|---|
| Amazon Neptune | **Neo4j** |
| Redis Vector Search | **Milvus** |
| LandingAI ADE (API key) | **Local ADE** — PyMuPDF + DocLayout-YOLO |

## Why it's a separate module

The backend answers questions; this manufactures the evidence it answers from.
Different dependencies, different failure profile, different schedule. Ingestion
owns **writing**; the backend owns **reading**. The handoff is the graph and the
vector index — nothing else.

It orchestrates rather than re-parses: extraction happens in `eugene_ade` over
HTTP. Duplicating a YOLO parser in two processes would mean two sets of weights to
keep in sync and two places for a chunking bug to hide.

## Flow

```
research_areas.yaml
      │
      ▼
 discover (Europe PMC) ──► extract (eugene_ade) ──► index (Neo4j + Milvus)
                                                          │
                                                          ▼
                                              centrality (M4/M5) — once, last
```

Centrality runs **last and once**, after every document is in the graph:
structural importance is a property of the whole corpus, so per-document scoring
would measure the wrong thing.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | schedule, last run, current state |
| POST | `/ingest/run` | force a sweep now (async; poll `/health`) |
| POST | `/ingest/dry-run` | discovery only — what *would* be fetched |
| POST | `/ingest/centrality` | **refresh ranking without touching documents** |

That last one is the practical payoff of M5: parsing is the expensive stage,
ranking is the cheap one, so the whole corpus can be retuned in seconds.

```bash
curl localhost:18200/health
curl -X POST localhost:18200/ingest/dry-run     # safe: no writes
curl -X POST localhost:18200/ingest/centrality  # re-rank only
```

## Research areas

`src/pipeline/config/research_areas.yaml`. Declared in advance on purpose — the
pipeline does not decide what to look for, and the list is auditable. Adding an
area is a config edit, not a code change.

## Mechanisms implemented

| | Mechanism | Where |
|---|---|---|
| **M1** | Chunk as dual-typed graph object w/ bbox, confidence, content hash | `ade/parser.py`, `ade/indexer.py` |
| **M2** | Deterministic id shared by Neo4j and Milvus | `pipeline/util/identity.py`, `ade/parser.py` |
| M3 | Parser-emitted evidence links | *scaffolded, disabled* |
| **M4** | 7-metric self-renormalizing composite centrality | `pipeline/graph/centrality.py` |
| **M5** | Centrality as replaceable graph properties | `pipeline/graph/centrality.py` |
| **M6** | Intent-conditioned pre-ranking + asymmetric RRF | `foundation/vector/intent.py` |
| **M7** | Backend-issued evidence labels | `foundation/vector/fusion_search_service.py` |

### M2 — why deterministic ids matter

```
chunk_id = sha1(f"{doc_id}:{ordinal}:{element_id}")[:32]
```

The same string is the Neo4j `chunk_id` **and** the Milvus primary key. No join
map between the stores, because a join map is what drifts on re-ingestion and
silently points a citation at the wrong paragraph.

> This replaced `uuid.uuid4()`. Every re-ingest used to mint fresh ids and orphan
> every stored evidence link, with nothing in the system noticing.

### M4 — the self-renormalizing composite

Seven metrics (PageRank 0.28, degree 0.16, betweenness 0.16, closeness 0.12,
harmonic 0.12, eigenvector 0.10, Katz 0.06). A node-count guard skips the
infeasible ones and the composite **renormalizes over whichever actually ran**, so
the 0–1 contract holds at any corpus size. Above the guard, (0.28, 0.16, 0.16)
becomes (0.467, 0.267, 0.267) automatically.

## Config

| Variable | Default | Purpose |
|---|---|---|
| `INGESTION_HOUR` / `INGESTION_MINUTE` | `1` / `0` | sweep time |
| `INGESTION_TZ` | `UTC` | UTC by default so it doesn't shift with DST |
| `EUGENE_ADE_URL` | `http://eugene_ade:8000` | extraction service |
| `CENTRALITY_BETWEENNESS_MAX` | `4000` | node-count guard per metric |

## Known limits

- **Discovery is Europe PMC only.** ClinicalTrials.gov sweeps still run through
  `bin/ctgov/`; folding them into this scheduler is the next step.
- **M3 is scaffolded, not running.** Interface fixed; no fact layer yet.
- **One run at a time.** Extraction is CPU-saturating; overlapping sweeps would
  compete for cores doing identical work.
