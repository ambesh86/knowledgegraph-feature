# Eugene Scout

**Real-time pipeline intelligence & partnership opportunity scanning** — Use Case 1 of the
CSL BD AWS Bioinformatics Agentic Workflow.

A scheduled scanner that watches ClinicalTrials.gov, Europe PMC, USPTO and SEC EDGAR for
partnership signals in CSL's therapeutic franchises, scores them against a configurable
strategic filter, and ranks companies for the BD team. Everything it produces is traceable
back to a URL an analyst can open.

```
                                   ┌──────────────────────────────┐
  02:00 UTC  ──► APScheduler ──►   │        orchestrator          │
  POST /scan ──►                   │  (deterministic, not an LLM) │
                                   └───────────────┬──────────────┘
                                                   │
        ┌──────────────┬───────────────┬───────────┴────┐
        ▼              ▼               ▼                ▼
  ClinicalTrials   Europe PMC       USPTO ODP       SEC EDGAR
   (trials)        (literature)     (patents)       (filings)
        └──────────────┴───────────────┴────────────────┘
                            │  RawSignal[]
                            ▼
                    ┌───────────────┐
                    │  S3  raw/     │   STAGING — untouched upstream payloads
                    └───────┬───────┘   write-once, replayable, 90-day lifecycle
                            ▼
     enrich ─► relevance gate ─► dedupe ─► cross-source merge
                            ▼
                   score()  ← PURE FUNCTION, no I/O, no LLM
                            ▼
                  rationale() ← LLM writes prose ONLY, output verified
                            ▼
                    ┌───────────────┐
                    │ S3  curated/  │   FINAL — scored signals, company scores,
                    └───────┬───────┘   per-area index, dated snapshots
                            ▼
                  in-memory index ──► FastAPI ──► Next.js BFF ──► Radar / Watchlist
```

## Why it is built this way

**S3 is the only database.** The corpus is a few thousand signals, read-mostly, and rebuilt
wholesale by each scan — the shape object storage serves well and a relational store buys
nothing for. What Postgres would have provided (ad-hoc filtering) is provided instead by an
in-memory index rehydrated from one curated object per area. At two orders of magnitude more
data the honest answer would be a query engine; `index.py` is the seam where one goes.

**Scoring is deterministic; the LLM only writes prose.** The use case asks for
recommendations BD leaders can "interrogate and challenge". A ranking produced by a language
model cannot be interrogated — asked twice it answers differently, and asked why it invents a
reason. `scoring.py` is a pure function of six named factors whose inputs are all recorded, so
a score can be challenged factor-by-factor, replayed against last month's weights, and unit
tested. `rationale.py` runs *after* the number exists and cannot change it. Any generated
paragraph containing a digit that was not in its input is discarded in favour of the
deterministic template — checked in code, not merely requested in the prompt.

**A failing source degrades itself, nothing else.** Collectors return a report instead of
raising. One flaky public API costs its own column of the Radar, not the morning briefing.

## Sources

| Source | What it contributes | Auth | Window |
|---|---|---|---|
| ClinicalTrials.gov v2 | Trials with sponsor, phase, intervention | none | 45d |
| Europe PMC (`SRC:MED`) | Literature with abstracts | none | 45d |
| **USPTO Open Data Portal** | Patent applications with applicants | `USPTO_API_KEY` | 540d |
| SEC EDGAR full-text | 8-K / S-1 / 424B4 material events | none | 90d |

Every field each collector reads is recorded against a real captured response in
[docs/SOURCE_CONTRACTS.md](docs/SOURCE_CONTRACTS.md). Nothing is parsed that is not documented
there.

### Two upstream findings worth knowing

**Europe PMC ignores its own sort parameter.** Verified 2026-08-08: a 57,734-hit query with
`sort=P_PDATE_D desc` returned a two-month-old record first. Ordering from that API is never
trusted — collectors over-fetch, filter by an absolute date window, and sort locally.

**Europe PMC's patent index is abandoned.** It holds 139,427 patent records for 2011–2012 and
**zero from 2013 onward**. This is the real root cause of the "2002 patents under an overnight
heading" defect documented elsewhere in this codebase: no amount of client-side filtering can
make a frozen corpus fresh. The patent source was replaced with USPTO ODP, which is current,
honours `sort`, supports Lucene date ranges, and carries structured applicant names.

## Storage layout

```
s3://eugene-scout-087084717211/
  raw/dt=<date>/run=<id>/area=<area>/source=<source>/records.jsonl.gz   STAGING
  curated/signals/area=<area>/signals.jsonl.gz                          FINAL
  curated/companies/area=<area>/companies.jsonl.gz
  curated/index/area=<area>/index.json         ← loaded into memory, serves every query
  curated/snapshots/area=<area>/dt=<date>/…    ← immutable; the 30-day delta baseline
  curated/digests/area=<area>/dt=<date>/…      ← weekly partnership briefing
  runs/<run_id>/manifest.json                  ← audit trail
  config/scan_config.json                      ← BD-editable weights and thresholds
```

Hive-style partitioning throughout, so the same layout can later be crawled by Glue or queried
by Athena without a migration. Versioning is on; `raw/` expires at 90 days because staging is
reproducible, curated data is not.

## Scoring

```
score = 100 × Σ(weight_i × factor_i) / Σ(weight of factors that APPLIED)
```

Normalising by the applied weight — not the configured total — matters: a literature hit has no
development stage, and scoring it zero would systematically punish an entire source for lacking
a property it cannot have.

| Factor | Measures | Notes |
|---|---|---|
| `area_fit` | Keyword overlap with the declared taxonomy | Saturating, so length is not relevance |
| `stage_fit` | Development stage | Peaks at Phase I/II — the use case's thesis |
| `recency` | Age against that source's own window | Per-source, so patents stay competitive |
| `modality_fit` | Overlap with CSL capability | Separates "actionable" from "interesting" |
| `corroboration` | Independent sources for one event | The strongest evidence the system makes |
| `company_context` | Prior activity from this company | Small weight — the point is finding new names |

Weights, thresholds, source windows and the relevance gate all live in `config/scan_config.json`
and are editable from Settings — "configuration, not code", per the use case.

### The relevance gate

Two measured failures produced it, and both are regression-tested:

- An oncology checkpoint-inhibitor trial entered the hemophilia area on the word "inhibitor".
- USPTO patents for hearing loss and phenylketonuria entered on "gene therapy" alone.

A record must match at least one *specific* (non-generic) keyword to reach the curated tier.

## Running

```bash
# Local
pip install -r requirements.txt
export SCOUT_S3_BUCKET=eugene-scout-087084717211 USPTO_API_KEY=...
PYTHONPATH=src uvicorn scout.api:app --port 18300

# In the stack
docker compose up -d eugene_scout
curl localhost:18300/health
curl -X POST localhost:18300/scan          # ~17s for 5 areas across 4 sources
```

### Tests

```bash
pytest                    # 240 tests, hermetic (moto for S3, stubbed HTTP)
pytest -m "not stress"    # fast subset
pytest -m stress          # volume, latency and adversarial-input tests
```

The stress suite is what defines the scale at which the in-memory-index trade is sound: query
latency is asserted at 50,000 signals, and the dedup pass is guarded against accidental O(n²)
regression — a real one was caught and fixed there (14.6s → <1s for 3,000 records).

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` `GET /status` | Liveness, S3 reachability, schedule, source availability |
| `POST /scan` | Manual trigger. Single-flight; a concurrent call returns `skipped` |
| `GET /signals` | Filter by area / type / priority / company / date / free text |
| `PATCH /signals/{id}` | Dismiss — written through so the next scan honours it |
| `GET /companies` | Watchlist, ranked |
| `GET /stats` | Counters, including "new since" |
| `GET /digest?area=&format=markdown` | The ranked weekly partnership briefing |
| `GET /runs` | Audit trail with per-source outcomes |
| `GET`/`PUT /config` | BD-editable scan configuration |

## Mapping to the PDF's AWS architecture

The use case names managed AWS services; this stack runs on Docker Compose today. Each is
implemented by the equivalent already present, and the mapping is kept legible so the AWS path
stays open.

| PDF | Here | Why |
|---|---|---|
| EventBridge (scheduling) | APScheduler cron in-container | Matches `eugene_ingestion`; ships with the stack, survives a rebuild |
| Bedrock multi-agent orchestrator | Deterministic orchestrator + pluggable collectors | A ranking must be reproducible and auditable |
| Comprehend Medical | Keyword/ontology matching + Neo4j linkage | Not provisioned; structured applicants/sponsors are more exact for BD attribution anyway |
| HealthLake | Neo4j behind `eugene_ws` | Already the system of record |
| S3 data lake | S3 `raw/` + `curated/` | As specified |
| Lambda | FastAPI handlers | Same code, different envelope |
| Email / Slack push | Webhook + SMTP, **off by default** | A dev box must not be able to message the BD team |

Bedrock defaults to `amazon.nova-lite-v1:0`: Anthropic models are blocked in this account by a
missing Marketplace subscription, so defaulting to Claude would fail every call.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `SCOUT_S3_BUCKET` | `eugene-scout-087084717211` | The only datastore |
| `USPTO_API_KEY` | — | Free at developer.uspto.gov/apis. Absent → patents degrade, other sources unaffected |
| `SCOUT_CRON_HOUR` | `2` | After `eugene_ingestion`'s 01:00, so it sees the night's papers |
| `SCOUT_TZ` | `UTC` | Fixed so the schedule does not shift with DST |
| `SCOUT_WEEKLY_DIGEST_DOW` | `0` | Monday |
| `SCOUT_NOTIFY_ENABLED` | `false` | Deliberate opt-in |
| `SCOUT_LLM_ENABLED` | `true` | Rationale prose only; degrades to template |

## Adding a source

1. Verify the contract live and record a real response in `docs/SOURCE_CONTRACTS.md`.
2. Add a `SourceId` member and a collector subclassing `BaseCollector` (implement `_fetch`;
   the base class enforces the never-raise contract).
3. Register it in `collectors/__init__.py` and add a `SourceSettings` default.
4. Add fixture-driven tests using a real captured payload.

The pipeline never learns how many sources exist.
