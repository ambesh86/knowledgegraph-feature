# UC1 — Code Walkthrough

One line per step. Read top to bottom to follow a signal from a public API into the Radar.

Two services: **`agents/eugene-scout/`** (Python, scans and scores) and
**`agents/eugene-agent-ui-next/`** (Next.js, displays). S3 is the only database.

---

## A. Boot — container starts

| # | Where | What happens |
|---|---|---|
| A1 | `docker/eugene_scout/Dockerfile` | Copies `src/` to `/app/src`, and `ingestion/.../research_areas.yaml` to `/app/config` so the taxonomy is never retyped |
| A2 | `CMD uvicorn scout.api:app` | Starts FastAPI on port 8000 (published as **18300**) |
| A3 | `api.py :: lifespan()` | Registers two APScheduler cron jobs and starts the scheduler |
| A4 | `api.py :: lifespan()` | Job 1 = `execute_scan` daily at `SCOUT_CRON_HOUR` (02:00 UTC, after ingestion's 01:00) |
| A5 | `api.py :: lifespan()` | Job 2 = `execute_weekly_digest` on `SCOUT_WEEKLY_DIGEST_DOW` (Monday) |
| A6 | `api.py :: lifespan()` | Calls `index.refresh()` to warm the in-memory index from S3 so the first request isn't a cold read |
| A7 | `index.py :: SignalIndex.refresh()` | Reads `curated/index/_areas.json`, then one `index.json` per area, into RAM |
| A8 | `areas.py :: load_areas()` | Parses `research_areas.yaml` into `Area` objects (cached for the process lifetime) |

---

## B. A scan runs — cron at 02:00, or `POST /scan`

| # | Where | What happens |
|---|---|---|
| B1 | `api.py :: execute_scan()` | Checks `_lock`; if a scan is already running, returns `{"status":"skipped"}` instead of queueing |
| B2 | `api.py :: execute_scan()` | Runs the orchestrator in a threadpool so blocking I/O never occupies the event loop |
| B3 | `orchestrator.py :: Orchestrator.run()` | Mints `run_id` = UTC timestamp (lexical order = chronological, so listing runs needs no parsing) |
| B4 | `store.py :: Store.load_config()` | Loads `config/scan_config.json` from S3; falls back to defaults if absent **or malformed** |
| B5 | `orchestrator.py :: _select_areas()` | Picks enabled areas from the YAML, narrowed by `config.enabled_areas` |
| B6 | `store.py :: Store.save_run()` | Writes `runs/<id>/manifest.json` with `status="running"` — the audit trail starts before the work does |
| B7 | `orchestrator.py :: run()` | Loops areas, calling `_run_area()`; a failing area is caught and does **not** abort the run |

---

## C. Collection — four sources, per area, concurrently

| # | Where | What happens |
|---|---|---|
| C1 | `orchestrator.py :: _collect()` | `ThreadPoolExecutor` fans out to every enabled source at once |
| C2 | `collectors/__init__.py :: build()` | Resolves `SourceId` → collector class from `REGISTRY` (adding a source is one line here) |
| C3 | `collectors/base.py :: BaseCollector.collect()` | Wraps `_fetch()` in try/except — **collectors return a `SourceReport`, they never raise** |
| C4 | `collectors/trials.py :: _fetch()` | `GET clinicaltrials.gov/api/v2/studies`, over-fetches 5×, drops observational studies |
| C5 | `collectors/trials.py :: _to_signal()` | Maps nctId/phase/sponsor; attributes a company **only** if `leadSponsor.class == "INDUSTRY"` |
| C6 | `collectors/literature.py :: _fetch()` | `GET ebi.ac.uk/europepmc` with `FIRST_PDATE:[start TO today]` pushed upstream, `resultType=core` for abstracts |
| C7 | `collectors/patents.py :: _fetch()` | `GET api.uspto.gov` with `X-API-KEY` header; keyword clause **parenthesised** so the date range binds to all terms |
| C8 | `collectors/patents.py :: _is_empty_result()` | Treats USPTO's HTTP 404 as "no matches", not as a failure |
| C9 | `collectors/edgar.py :: _fetch()` | `GET efts.sec.gov` for 8-K/S-1/424B4; filters to biotech SIC codes so a bank's filing can't rank |
| C10 | `collectors/base.py :: http_get_json()` | Per-host `RateLimiter`, retry with jittered backoff on 429/5xx only |
| C11 | `collectors/base.py :: freshest()` | **Filters** by absolute date window, then sorts locally, then caps — never trusts upstream ordering |
| C12 | `collectors/base.py :: within_window()` | Drops undated records outright (this is what stopped 2002 patents appearing as "overnight") |

---

## D. Staging — S3 `raw/`, before any judgement

| # | Where | What happens |
|---|---|---|
| D1 | `orchestrator.py :: _run_area()` | Calls `stage_raw()` per source **immediately after collection**, before enrichment or scoring |
| D2 | `store.py :: Store.stage_raw()` | Skips empty batches (a zero-row object is pure cost) |
| D3 | `storage.py :: key_raw()` | Builds `raw/dt=<date>/run=<id>/area=<area>/source=<src>/records.jsonl.gz` (Hive-partitioned for future Athena) |
| D4 | `storage.py :: put_jsonl_gz()` | Gzips newline-delimited JSON with `mtime=0` so identical input yields identical bytes |

> **Why here:** raw must record what upstream *said*, not what the pipeline *concluded* — otherwise an enrichment bug corrupts the archive that exists to recover from enrichment bugs.

---

## E. Enrichment and filtering

| # | Where | What happens |
|---|---|---|
| E1 | `enrich.py :: enrich()` | Returns a **new** `RawSignal` (the model is frozen — staged and enriched stay separately inspectable) |
| E2 | `enrich.py :: is_commercial()` | Drops attribution for universities/hospitals/agencies — keeps the signal, removes the non-partner |
| E3 | `text.py :: matched_keywords()` | Re-matches area keywords across title + summary + payload |
| E4 | `text.py :: normalize()` | Folds `haemophilia→hemophilia`, `factor VIII→factor 8`, collapses punctuation — **punctuation before roman numerals** |
| E5 | `text.py :: matches()` | Word-boundary aware, so `ig` doesn't match inside `light` |
| E6 | `enrich.py :: is_relevant()` | Rejects zero-keyword matches, and matches that are **only** generic terms like "gene therapy" |
| E7 | `dedupe.py :: dedupe_identity()` | Collapses re-fetches by `sha256(source:external_id)` — keyed on id, **not title**, so copy-edits don't resurface |
| E8 | `dedupe.py :: group_corroborated()` | Buckets by publication month, then groups the same event reported by different sources |
| E9 | `dedupe.py :: _group_within()` | Indexes candidates by source and only compares **across** sources (this is the O(n²) fix: 14.6s → <1s) |
| E10 | `dedupe.py :: _similar()` | Cheap checks first (date, company), Jaccard title overlap ≥0.80 last |
| E11 | `dedupe.py :: primary_of()` | Picks the richest record to represent a group: Trials > EDGAR > Patents > Literature |

---

## F. Scoring — the deterministic core

| # | Where | What happens |
|---|---|---|
| F1 | `orchestrator.py :: _build_signal()` | Calls `score()` with `today` **injected** — no clock read inside, so results are reproducible |
| F2 | `scoring.py :: score()` | Evaluates six factors; each returns `(value, inputs)` or `None` for "not applicable" |
| F3 | `scoring.py :: _area_fit()` | Saturating curve over matched keywords — 6 matches isn't twice as relevant as 3 |
| F4 | `scoring.py :: _stage_fit()` | Phase II = 1.00, Phase I = 0.95, Phase III = 0.65 — peaks where a deal is still available |
| F5 | `scoring.py :: _recency()` | Linear decay against **that source's own** window, so patents stay competitive with papers |
| F6 | `scoring.py :: _modality_fit()` | Overlap with CSL capability — separates "CSL could build this" from "interesting science" |
| F7 | `scoring.py :: _corroboration()` | 1 source = 0.35, 2 = 0.80, 3+ = 1.00 |
| F8 | `scoring.py :: _company_context()` | Returns `None` when unattributed, so papers aren't penalised for having no corporate author |
| F9 | `scoring.py :: score()` | `100 × Σ(weight×value) ÷ Σ(weight of factors that APPLIED)` — N/A ≠ zero |
| F10 | `config.py :: Thresholds.priority_for()` | Score → `high` ≥75 / `med` ≥55 / `watch` |
| F11 | `models.py :: ScoreResult.breakdown()` | Serialises every factor **with its inputs** — this is what the UI's "Why" panel renders |

---

## G. Rationale — the only LLM call, fenced

| # | Where | What happens |
|---|---|---|
| G1 | `orchestrator.py :: _build_signal()` | Only generates for `high`/`med` — a watch-tier signal nobody opens doesn't justify a call |
| G2 | `rationale.py :: build()` | Builds `_facts()` — the **closed set** the model may use — and a deterministic template as fallback |
| G3 | `rationale.py :: _llm_enabled()` | Returns False unless a provider is configured; template path runs and is labelled as such |
| G4 | `rationale.py :: _bedrock()` | Bedrock Converse API, defaulting to `amazon.nova-lite-v1:0` (Anthropic is blocked in this account) |
| G5 | `rationale.py :: _verify()` | **Every digit in the output must appear in the input** — else discard and fall back to template |
| G6 | `rationale.py :: _verify()` | Also rejects refusals and runaway length |
| G7 | `models.py :: RationaleKind` | Stores `llm` or `template` so the UI can badge it AI-WRITTEN vs COMPUTED |

> The LLM never produces a score, a rank, a date or a company name. It writes prose about a decision already made.

---

## H. Company aggregation

| # | Where | What happens |
|---|---|---|
| H1 | `enrich.py :: company_id_for()` | `"co-" + sha256(normalize_company(name))` — deterministic, so a rebuild from staging keeps every id |
| H2 | `text.py :: normalize_company()` | Strips ownership clauses ("a Sanofi company"), legal suffixes (Inc/GmbH/N.V.), industry words (Therapeutics/Pharmaceuticals) |
| H3 | `text.py :: normalize_company()` | Deliberately keeps `products`/`diagnostics` — Roche Holding ≠ Roche Products |
| H4 | `store.py :: baseline_company_scores()` | Walks back ~30 days through `curated/snapshots/` to find a delta baseline |
| H5 | `companies.py :: aggregate()` | Score = **best signal + bounded support bonus**, so extra evidence can never lower a rank |
| H6 | `companies.py :: aggregate()` | `delta_30d = 0.0` and `has_baseline=False` when no snapshot exists — never a fabricated arrow |

---

## I. Publish — S3 `curated/`

| # | Where | What happens |
|---|---|---|
| I1 | `store.py :: publish_area()` | Writes the **dated snapshot first** — a crash mid-publish must not leave the index without a baseline |
| I2 | `store.py :: publish_area()` | Then `curated/signals/…`, `curated/companies/…` as gzipped JSONL |
| I3 | `store.py :: _build_index()` | Builds the per-area `index.json` carrying full rows + priority/type counts |
| I4 | `store.py :: publish_area()` | Updates `curated/index/_areas.json` so boot knows what to load without a LIST |
| I5 | `orchestrator.py :: run()` | Sets run status: `ok`, `degraded` (a source failed), or `failed` (nothing published) |
| I6 | `api.py :: execute_scan()` | Calls `index.refresh()` **before** notifying, so a recipient clicking through finds the signal |
| I7 | `notify.py :: Notifier.dispatch()` | No-op unless `SCOUT_NOTIFY_ENABLED=true`; idempotent per `(run_id, signal_id)` via an S3 ledger |

---

## J. Serving a Radar page load

| # | Where | What happens |
|---|---|---|
| J1 | `components/atlas/views/RadarView.tsx` | Builds a query string from the filter chips |
| J2 | `hooks/useScout.ts :: useScoutData()` | Fetches with a sequence number so a slow earlier response can't repaint over a newer one |
| J3 | `app/api/atlas/signals/route.ts` | `currentUser()` → **401** if no `atlas_session` JWT cookie |
| J4 | `app/api/atlas/signals/route.ts` | Sets `ui_area` from `user.focusArea` — **server-controlled**, a client can't widen its own scope |
| J5 | `lib/atlas/scoutClient.ts :: call()` | On any failure returns a well-formed empty payload with `degraded:true` — never throws into a render |
| J6 | `api.py :: get_signals()` | Resolves areas via `areas_for_ui_area()` (UI taxonomy → scan taxonomy bridge) |
| J7 | `index.py :: query_signals()` | Filters in memory, computes counts **before** applying the priority filter, sorts by score then recency |
| J8 | `RadarView.tsx :: SignalRow` | Renders every `signal.sources[]` as an individual external link |
| J9 | `RadarView.tsx :: ScoreBreakdownPanel` | "Why" expands the factor bars + inputs + provenance-badged rationale |
| J10 | `RadarView.tsx` | `degraded` renders an explicit banner — an empty Radar must never look like a quiet night |

---

## K. Actions

| # | Where | What happens |
|---|---|---|
| K1 | `RadarView.tsx :: rescan()` | `POST /api/atlas/scout/scan` → `triggerScan()` → scanner (single-flight, 300s route budget) |
| K2 | `RadarView.tsx :: dismiss()` | `PATCH /api/atlas/signals/<id>` |
| K3 | `api.py :: patch_signal()` | Rewrites the **curated tier**, so the 02:00 scan reads the dismissal forward instead of undoing it |
| K4 | `orchestrator.py :: _build_signal()` | Carries `dismissed`, `detected_at` and `first_seen_run` forward from the prior signal |
| K5 | `ScanningSettings.tsx :: save()` | `PUT /api/atlas/scout/config` → validated by `ScanConfig` → **400** on bad input, never silently ignored |
| K6 | `api.py :: put_config()` | Strips client-supplied `version`/`updated_at` so the audit trail can't be rewound |

---

## L. Weekly briefing — UC1's headline deliverable

| # | Where | What happens |
|---|---|---|
| L1 | `api.py :: execute_weekly_digest()` | Monday cron builds a briefing per area and writes `curated/digests/…` |
| L2 | `digest.py :: build()` | Ranks companies ≥50, attaches rationale, sources consulted and a next action |
| L3 | `digest.py :: _next_action()` | Rule-derived, most-specific-condition-first, so a reader can see which fact produced it |
| L4 | `digest.py :: build()` | Sets `below_target` when fewer than 8 clear the bar — never pads the list to hit a number |
| L5 | `app/(atlas)/briefing/page.tsx` | The page, reachable at `/briefing` (⌘6) |
| L6 | `app/api/atlas/scout/briefing/route.ts` | `GET` → briefing JSON or Markdown, scoped by the session's focus area |
| L7 | `api.py :: get_digest()` | Accepts `ui_area` so the taxonomy bridge stays in the scanner, not duplicated in TS |
| L8 | `BriefingView.tsx :: publish()` | `POST` → `createArtifact()` → redirect to `/a/<id>` |
| L9 | `lib/atlas/artifacts.ts` | Gives the briefing a shareable URL plus MD / HTML / DOCX / PDF export, no second renderer |

---

## Key invariants

| Invariant | Enforced in |
|---|---|
| A collector never raises | `collectors/base.py :: BaseCollector.collect()` |
| Upstream ordering is never trusted | `collectors/base.py :: freshest()` |
| Scoring is pure and reproducible | `scoring.py :: score()` (`today` injected) |
| The LLM cannot invent a number | `rationale.py :: _verify()` |
| Company ids survive a rebuild | `enrich.py :: company_id_for()` |
| Only scout touches the scout bucket | UI talks HTTP via `lib/atlas/scoutClient.ts` |
| Unreachable ≠ empty | `degraded` flag through every BFF route |

## Entry points

| To change… | Edit |
|---|---|
| What is searched | `ingestion/src/pipeline/config/research_areas.yaml` |
| How signals rank | `scoring.py`, or the weights in Settings › Scanning |
| Which sources run | `collectors/__init__.py :: REGISTRY` + Settings |
| When it runs | `SCOUT_CRON_HOUR` in `docker-compose.yml` |
| What the Radar shows | `components/atlas/views/RadarView.tsx` |
