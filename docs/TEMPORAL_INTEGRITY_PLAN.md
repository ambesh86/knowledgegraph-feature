# Temporal integrity — "research has no value if it is old"

**Problem observed:** asked what "as of now" meant for Atacicept, the agent answered
**"as of now means June 2024"** and cited a PubMed search as confirmation. Today is
2026-08-01. The answer was two years stale and the citation implied a freshness it never had.

## 1. Root causes (all three are real, and independent)

### RC-1 — The agent has no idea what day it is
Nothing injects the current date into the system prompt. `current_time` is gated off by
default (`EUGENE_ALLOW_UTILITY_TOOLS=false` in `eugene_data_agent.py`) — correctly so, it
caused runaway ReAct loops. So when the model needs a date it has exactly one source left:
**its own training cutoff**. June 2024 is not a data property; it is the model talking about
itself. No amount of live tool calling fixes this, because the model reconciles fresh tool
output against a "now" it believes is 2024.

### RC-2 — Every external tool retrieves by relevance, never by recency
- `search_pubmed` calls E-utilities `esearch` with **no `sort` parameter** → NCBI defaults
  to relevance, which is heavily weighted toward older, well-cited papers.
- `search_clinical_trials` passes only `query.term` and `pageSize` — **no sort**.
- `search_europepmc` passes no `sort` either.

So even a correctly-dated agent would be handed stale records and would faithfully report
them.

### RC-3 — Nothing carries a timestamp, so staleness is invisible
No tool returns *when* it retrieved, no result set reports its own date range, and the
internal graph/vector snapshot has no recorded ingest date. There is no way for the model —
or the user — to tell a live 2026 result from a cached 2024 one.

## 2. Design

### 2.1 Authoritative clock (fixes RC-1)
`query/util/temporal.py` builds a temporal directive injected as the **very first block** of
the system prompt on **every** turn:

> TODAY IS {date}. This is authoritative and overrides your training data. Your training
> cutoff is NOT the current date and must never be presented as "now"/"currently"/"as of
> now"/"to date". If you cannot verify something against a live source, say when your
> information is actually from — never imply it is current.

This is prompt-level, not tool-level, precisely because the failure is the model reasoning
about itself. It costs one small block of tokens per turn and cannot be skipped or
loop-abused the way a `current_time` tool call can.

### 2.2 Recency-first retrieval (fixes RC-2)
| Tool | Change |
|---|---|
| `search_pubmed` | `sort=date` (most recent first) + optional `reldate`/`mindate` window via a `recent_days` arg |
| `search_clinical_trials` | `sort=LastUpdatePostDate:desc` |
| `search_europepmc` | `sort=P_PDATE_D desc` |

Each keeps a `sort_by_relevance` escape hatch, because "the seminal paper on X" is a
legitimate query that recency ranking would answer badly. Default is recency.

### 2.3 Freshness metadata on every result (fixes RC-3)
Every external tool response gains:
```json
"retrieved_at": "2026-08-01T13:40:00Z",
"freshness": {"newest": "2026-07", "oldest": "2025-11", "as_of": "2026-08-01", "live": true}
```
The internal stores gain a recorded snapshot date: the CT.gov loader writes a
`(:DataSnapshot)` node, `search_fused` returns it, and `/health/data-freshness` exposes it
for the UI. So "as of" always resolves to a real, sourced date.

### 2.4 Offline degradation with honest disclosure
`query/util/connectivity.py` runs a cached (60s TTL) reachability probe. When the internet is
unreachable, tools return `{"offline": true, ...}` and the temporal directive switches to:

> Today is {date}, but I could not reach the internet, so this answer comes only from the
> internal Eugene snapshot dated {snapshot}. It may be out of date.

This is the user's explicit requirement: fall back to stale data **only** when offline, and
say so plainly.

### 2.5 Mandatory dating in the answer
The directive requires every answer to state what date its information is for — live results
dated to today, internal results dated to the snapshot, and any mix attributed per claim.

### 2.6 UI
A **data-freshness indicator** in Ask, fed by a new `/api/atlas/freshness` route proxying
`/health/data-freshness`. It shows today's date, the internal snapshot date, and online/offline
state — structural, not regex-scraped from prose.

## 3. Non-goals
- Re-downloading CT.gov on every query. The graph stays a snapshot; the fix is that its
  snapshot date is *recorded and disclosed*, and live tiers are consulted for recency.
- Removing relevance ranking. It stays available behind an explicit flag.
