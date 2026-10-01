# All Sources — cascading multi-source answering + ClinicalTrials.gov ingest

**Status:** design + build plan
**Scope:** (1) load 1 year of ClinicalTrials.gov data for Eugene's research themes into
Neo4j, (2) add an **All Sources** tab that answers by cascading Eugene KG →
ClinicalTrials.gov → PubMed.

---

## 1. Why this is net-new

The current source selector is **exclusive single-select**. `ToolChips.tsx` documents it:

> "Source selector — behaves like a single-select tab strip. Picking a source switches to
> ONLY that source."

and `build_source_directive()` in `eugene_data_agent.py` enforces **STRICT SOURCE
ISOLATION** — "use ONLY the tools belonging to the enabled source(s)". Conversation memory
is even keyed per source-set (`_source_key`) so answers never bleed across sources.

That is the opposite of what All Sources needs. All Sources is a *cascade*: try the graph,
and only escalate outward when the graph genuinely can't answer. So this is a new mode, not
a checkbox that ticks the three existing ones.

## 2. Architecture

```
                     ┌─────────────────── All Sources turn ───────────────────┐
  user prompt ──────►│ TIER 1  Eugene KG  (MCP graph tools)                   │
                     │   ├─ resolved + sufficient ──────────────► answer      │
                     │   └─ empty / partial ─┐                                │
                     │ TIER 2  ClinicalTrials.gov (search_clinical_trials)    │
                     │   ├─ sufficient ────────────────────────► answer       │
                     │   └─ still thin ─────┐                                 │
                     │ TIER 3  PubMed / Europe PMC (search_pubmed, europepmc) │
                     └────────────────────────────────────────────────────────┘
                              every tier tagged in the "Sources:" footer
```

**Cascade is enforced by directive, not by hard-coded orchestration.** Rationale: the
existing agent is a Strands ReAct loop with the tool-call budget, duplicate-input breaker,
and streaming tool-event harvesting already built around it (`_register_tool_call`,
`_harvest_messages`). Bolting a hand-rolled orchestrator alongside it would fork the
tool-trace path that the UI's context graph depends on. A tier-ordered directive keeps one
code path and keeps the reasoning graph intact.

**Trade-off, stated plainly:** a directive-driven cascade is a strong bias, not a hard
guarantee — the model can in principle skip a tier. Mitigations: (a) the tier order is
stated as a numbered HARD RULE, (b) the escalation criteria are explicit and testable
("empty result", "no `evaluated_in` edge"), (c) the mandatory `Sources:` footer makes any
skipped tier visible to the user. If we later need a hard guarantee, the escalation becomes
a server-side loop over three scoped sub-agent calls — the directive stays as the prompt for
each.

## 3. Work items

### A — ClinicalTrials.gov data pipeline

| # | Item |
|---|---|
| A1 | `bin/ctgov/download_ctgov.py` — batched API v2 client: `pageSize=1000`, `while`-loop on `x-next-page-token`, 1-year `StartDate` window, one theme per run, resumable, retry/backoff |
| A2 | Themes from `lib/atlas/areas.ts` (hematology, nephrology, immunology, oncology) — the same taxonomy the Atlas intelligence feed already uses |
| A3 | `bin/ctgov/build_ctgov_csv.py` — raw JSON → `ctgov_nodes.csv` + `ctgov_edges.csv`, node ids offset ≥ 900,000, labels lowercase (`clinical_trial`) to match PrimeKG convention |
| A4 | Link edges to **existing** `drug` / `disease` nodes by normalized name match — an unlinked trial island is useless for graph traversal |
| A5 | `bin/ctgov/load_ctgov.cypher` — indexes first, then `MERGE` in `CALL { } IN TRANSACTIONS OF 1000` (idempotent; re-runnable) |
| A6 | `docker-compose.yml` — mount `./dumps/ct_import` → `/var/lib/neo4j/import` (currently absent, so `LOAD CSV file:///` cannot read anything) |

Existing scripts reused/superseded: the fixup+load convention comes from
`eugene/src/fix_clinical_trial_nodes_csv.py` and
`eugene/saved_queries/ingest_csv/clinical_trials.cypher`. The old
`src/clinicaltrail/` provider is left in place (it backs
`Neo4jClinicalTrialAdapter`) but is not on the new path — its recursive pagination,
per-page CSV header duplication, and `pageSize=25` make it unfit for a 1-year pull.

### B — Backend (`eugene-agent-ws`)

| # | Item |
|---|---|
| B1 | `ToolRequestEnum.ALL_SOURCES = "all_sources"` |
| B2 | `build_source_directive()` — new `all_sources` branch with the tiered cascade policy |
| B3 | `_init_agent()` — All Sources loads MCP graph tools **+** `search_clinical_trials` **+** `search_pubmed` **+** `search_europepmc` (no `http_request`: arbitrary URL fetch is not a research source and adds loop surface) |
| B4 | `classify_intent()` — All Sources is authoritative and never silently expanded |
| B5 | `_clarity_message()` — mention All Sources as the "not sure?" default |

### C — UI (`eugene-agent-ui-next`)

| # | Item |
|---|---|
| C1 | `ToolSelection` type += `"all_sources"` |
| C2 | `AskView.tsx` `SOURCES` — All Sources tab in first position. The *default* selection stays `eugene`, so existing behaviour is unchanged for anyone who doesn't pick the new tab |
| C3 | `ToolChips.tsx` — matching chip + hint |
| C4 | `Message.tsx` `SOURCE_META` — badge |
| C5 | `SettingsView.tsx`, `LibraryView.tsx` — labels |

### D — Verification

Build both images, run the stack, and drive real queries through `/query/stream` with
`include_tools: ["all_sources"]`. Assert: tier-1 hit answers from the graph; a
"currently recruiting" question reaches CT.gov; a "what does the literature say" question
reaches PubMed; every answer carries a `Sources:` footer.

---

## 4. The prompts

### 4.1 Cascade directive (goes into `build_source_directive`, All Sources branch)

> MODE = ALL SOURCES (CASCADING). You have every research source available this turn:
> the Eugene knowledge graph (MCP `lookup_*`/`fetch_*`/`find_*` tools), ClinicalTrials.gov
> (`search_clinical_trials`), and biomedical literature (`search_pubmed`,
> `search_europepmc`). You MUST consult them in strict tier order and escalate only on a
> real miss.
>
> TIER 1 — EUGENE KNOWLEDGE GRAPH (always first, never skip).
> Resolve the entities with `lookup_node_by_value` (fuzzy_match=true), then use
> `fetch_facts` / `fetch_node_relationships` / `find_organization_*`. The graph is the
> authoritative internal source: when it answers the question, that answer wins.
> Escalate to Tier 2 ONLY when one of these is true, and say which one:
>   (a) `lookup_node_by_value` returned nothing for the key entity;
>   (b) the entity resolved but the graph has no edges of the type asked for;
>   (c) the user explicitly asked for *current*, *recent*, *recruiting*, *latest*, or
>       *this year* information — the graph is a static snapshot and cannot answer that.
>
> TIER 2 — CLINICALTRIALS.GOV. Call `search_clinical_trials(query, max_results)` for live
> trial status, phases, sponsors, and enrollment. Cite real NCT ids and URLs the tool
> returned. Escalate to Tier 3 when the question is about mechanism, efficacy, safety
> findings, or published evidence rather than trial registration facts — or when Tier 2
> returned nothing.
>
> TIER 3 — PUBMED / EUROPE PMC. Call `search_pubmed(query, max_results)` and, for
> patent-adjacent or preprint coverage, `search_europepmc(query, max_results,
> patents_only)`. Cite real PMIDs and URLs.
>
> SYNTHESIS RULES.
> 1. Do not stop at Tier 1 merely because it produced *something* — if the graph answer is
>    materially incomplete for what was asked, continue to the next tier and combine.
> 2. Attribute every fact inline to the tier that produced it. Never present a live CT.gov
>    or PubMed fact as a graph fact, or vice versa.
> 3. When tiers disagree (e.g. the graph shows a trial as completed and CT.gov shows it
>    recruiting), surface the disagreement explicitly and prefer the live source for
>    status, noting the graph snapshot is static.
> 4. Never fabricate a source, id, or URL. Only cite what a tool actually returned.
> 5. Respect the global tool-call budget: at most ~20 calls. Prefer 2-4 precise calls per
>    tier over exhaustive sweeps.
>
> End with a `Sources:` footer listing every tier you actually queried, e.g.
> `Sources: Eugene knowledge graph — Emicizumab, Hemophilia A · ClinicalTrials.gov
> NCT04158648 (https://clinicaltrials.gov/study/NCT04158648) · PubMed PMID 38421789
> (https://pubmed.ncbi.nlm.nih.gov/38421789/)`. Naming a tier you did not query is a bug.

### 4.2 Download scoping prompt (drives A1/A2 theme queries)

> Pull every interventional and observational study on ClinicalTrials.gov whose study start
> date falls in the last 12 months, restricted to CSL Behring's research themes as already
> encoded in `lib/atlas/areas.ts`: hematology (hemophilia, factor VIII/IX, gene therapy,
> bleeding disorders), nephrology (IgA nephropathy, complement, C3 glomerulopathy),
> immunology (immunoglobulin, CIDP, immunodeficiency, plasma-derived therapy), and oncology
> (bispecific antibodies, CAR-T, lymphoma, myeloma). Capture per study: NCT id, title,
> overall status, phase, study type, enrollment, lead sponsor, conditions, interventions,
> start/completion dates, and the canonical URL. Deduplicate by NCT id across themes, since
> a study may match more than one theme.

---

## 4a. Tier 1 is FUSED retrieval (Neo4j ⊕ Milvus)

Tier 1 is not "the graph" — it is both internal stores, fused.

### What was broken

Milvus was **entirely non-functional** and had been since at least 2026-07-19. Three
independent faults, each sufficient on its own:

1. **Env var collision.** `docker-compose.yml` set `MILVUS_URI=/app/.db/knowledge_graph_db`.
   pymilvus reads a bare `MILVUS_URI` into its own global `Config` *at import time* and
   requires an `http(s)://` address, so `import pymilvus` raised
   `ConnectionConfigException`. The guarded import in `eugene_ws.py` caught it and silently
   skipped every `/vector` route — `/vector/health` returned 404 and nobody noticed.
   Fixed by renaming to **`EUGENE_MILVUS_URI`**.
2. **Illegal milvus-lite path.** milvus-lite requires the file to end in `.db`;
   `knowledge_graph_db` does not. Now `/app/.db/eugene_vectors.db`, with a defensive
   suffix-append in `VectorSearchService`.
3. **Volume ownership.** `/app/.db` and `/app/.hf_cache` only came into existence when
   Docker mounted the named volumes, so they were created **root-owned** while the process
   runs as uid 1000 → `PermissionError` on milvus-lite's `.lock`. Fixed by creating and
   `chown`ing both directories in the Dockerfile so the volume inherits the right owner.

And even fixed, there was nothing to fuse: the collection held **8 hardcoded seed
summaries**.

### What exists now

| Piece | Location |
|---|---|
| Corpus ingest (graph → embeddings) | `src/foundation/vector/corpus_ingest_service.py` |
| Fusion retrieval + RRF | `src/foundation/vector/fusion_search_service.py` |
| HTTP API | `GET /vector/fusion/{query}`, `GET /vector/fusion/health` |
| MCP tool | `EugeneVectorTools.search_fused` |

**28,147 documents** embedded with `all-MiniLM-L6-v2` (384-dim, cosine via normalized IP):
3,110 clinical trials, 7,957 drugs, 17,080 diseases — the same entities the graph holds, so
both stores describe the same world. Ingest takes ~3 minutes on CPU.

### Why reciprocal rank fusion

The two retrievers return incomparable scores: Lucene relevance from Neo4j full text and
cosine similarity from Milvus share no unit, so you cannot simply sort a concatenation.
RRF fuses on **rank** instead of score:

```
score(d) = Σ_retrievers  weight / (K + rank_in_that_retriever)     K = 60
```

Graph hits carry a mild 1.2 weight (exact entity matches are worth slightly more than a
semantic neighbour); the weighting is deliberately gentle because over-tuning defeats the
robustness that makes RRF worth using. Documents found by **both** retrievers accumulate
both contributions and rise to the top — that corroboration is surfaced to the model as a
`retrievers: ["graph", "vector"]` tag and a `corroborated` count, and the directive tells it
to lead with those.

Observed on `"rituximab lymphoma trial"`: 18 graph hits, 18 vector hits, **4 corroborated** —
and all four corroborated items ranked above every single-retriever hit.

### A lexical-retrieval fix this exposed

The first implementation matched with `toLower(node_name) CONTAINS toLower($query)`, which
tests the **whole query string** against each name — so the natural-language query
"rituximab lymphoma trial" matched nothing at all and the graph leg returned 0 hits. Now it
uses a full-text index, which tokenizes and returns a relevance score (the rank RRF needs).
The pre-existing `entity_names` full-text index does **not** cover `clinical_trial`, so a
dedicated `eugene_fusion_fulltext` index is created rather than dropping a shared one.

### Operational caveat

milvus-lite is an **embedded, single-process** store. The ingest CLI runs out-of-process, so
the long-lived API process does not see a newly built collection until it is restarted.
Sequence: run the ingest, then `docker compose restart eugene_ws`. This is a real constraint
of milvus-lite, not a bug in the ingest — a server-mode Milvus would not have it.

## 5. Risks

- **Name-match linkage is lossy.** CT.gov intervention strings ("BIVV001", "efanesoctocog
  alfa", "rFVIIIFc-VWF-XTEN") won't all match graph `drug` node names. Expected linkage is
  partial; the loader reports the hit rate rather than silently dropping. Unlinked trials
  still land as nodes so they're searchable, just not traversable.
- **Directive-driven cascade** is a bias not a guarantee — see §2.
- **CT.gov API has no auth/rate limit documented but is throttleable.** The downloader
  backs off on 429/5xx.
