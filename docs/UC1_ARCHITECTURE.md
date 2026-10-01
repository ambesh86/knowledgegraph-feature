# Use Case 1 — Architecture

Real-Time Pipeline Intelligence & Partnership Opportunity Scanning, as built.

Implementation lives in [`agents/eugene-scout/`](../agents/eugene-scout/) (scanner) and
[`agents/eugene-agent-ui-next/`](../agents/eugene-agent-ui-next/) (Radar, Watchlist, Today,
Settings). Source contracts are recorded in
[`agents/eugene-scout/docs/SOURCE_CONTRACTS.md`](../agents/eugene-scout/docs/SOURCE_CONTRACTS.md).

---

## 1. Component architecture

```mermaid
graph TB
  subgraph Browser["Browser — CSL Atlas"]
    RV["RadarView<br/>live signals + score breakdown"]
    WV["WatchlistView<br/>ranked companies"]
    TV["TodayView<br/>real counters"]
    SV["Settings › Scanning<br/>weights, sources, run history"]
  end

  subgraph BFF["eugene_agent_ui_next :18502 — Next.js BFF"]
    AUTH["currentUser() — atlas_session JWT<br/>scope derived from profile, not query string"]
    R1["/api/atlas/signals"]
    R2["/api/atlas/signals/[id]"]
    R3["/api/atlas/watchlist"]
    R4["/api/atlas/scout/stats"]
    R5["/api/atlas/scout/runs"]
    R6["/api/atlas/scout/config"]
    R7["/api/atlas/scout/scan"]
  end

  subgraph Scout["eugene_scout :18300 — FastAPI"]
    SCHED["APScheduler<br/>daily 02:00 UTC · weekly digest"]
    ORCH["orchestrator.run()<br/>single-flight asyncio.Lock"]
    IDX["SignalIndex<br/>in-memory, atomically swapped"]

    subgraph COL["Collectors — never raise, report instead"]
      C1["trials.py<br/>ClinicalTrials.gov v2"]
      C2["literature.py<br/>Europe PMC SRC:MED"]
      C3["patents.py<br/>USPTO Open Data Portal"]
      C4["edgar.py<br/>SEC EDGAR full-text"]
    end

    ENR["enrich.py — company attribution"]
    GATE["relevance gate<br/>specific-keyword requirement"]
    DED["dedupe.py<br/>identity + cross-source merge"]
    SCO["scoring.py<br/>PURE · deterministic · 6 factors"]
    RAT["rationale.py<br/>LLM prose only · output verified"]
    NTF["notify.py — off by default, idempotent"]
    STO["store.py — repository"]
  end

  subgraph S3["s3://eugene-scout-087084717211 — the only database"]
    RAW[("raw/ — STAGING<br/>untouched payloads, write-once")]
    CUR[("curated/ — FINAL<br/>signals · companies · index · snapshots")]
    RUNS[("runs/ — audit trail")]
    CFG[("config/ — BD-editable")]
  end

  subgraph Ext["External"]
    CT["ClinicalTrials.gov"]
    EP["Europe PMC"]
    US["api.uspto.gov"]
    SE["efts.sec.gov"]
    BR["Bedrock — Nova"]
  end

  RV & WV & TV & SV --> AUTH --> R1 & R2 & R3 & R4 & R5 & R6 & R7
  R1 & R2 & R3 & R4 & R5 & R6 & R7 -->|"HTTP, server-side only"| Scout

  SCHED --> ORCH
  ORCH --> COL
  C1 --> CT
  C2 --> EP
  C3 --> US
  C4 --> SE
  COL -->|RawSignal[]| RAW
  COL --> ENR --> GATE --> DED --> SCO --> RAT --> STO
  RAT -.optional.-> BR
  STO --> CUR & RUNS
  STO --> CFG
  SCO --> NTF
  CUR --> IDX --> Scout
```

**Ownership rule.** `eugene_scout` is the only process that reads or writes the scout bucket.
The UI never touches S3; it talks HTTP. Two owners of one store is how a layout silently
diverges between writer and reader.

---

## 2. Scheduled scan

```mermaid
sequenceDiagram
  autonumber
  participant CRON as APScheduler
  participant ORCH as orchestrator
  participant COL as collectors
  participant EXT as public APIs
  participant S3 as S3
  participant LLM as Bedrock Nova
  participant NTF as notifier

  CRON->>ORCH: run(trigger="cron") at 02:00 UTC
  ORCH->>ORCH: acquire lock — if held, return {status:"skipped"}
  ORCH->>S3: PUT runs/<id>/manifest.json (running)
  ORCH->>S3: GET config/scan_config.json

  loop per therapeutic area
    ORCH->>COL: collect(area, settings, today) — 4 sources concurrently
    COL->>EXT: HTTP (rate-limited, retried, descriptive UA)
    EXT-->>COL: payloads, or failure
    COL-->>ORCH: RawSignal[] + SourceReport[]
    Note over COL,ORCH: a collector NEVER raises —<br/>a dead source degrades itself alone

    ORCH->>S3: PUT raw/dt=…/run=…/source=… (STAGING, before any judgement)
    ORCH->>ORCH: enrich → relevance gate → dedupe → cross-source merge
    ORCH->>ORCH: score() — pure, no I/O, no clock

    alt priority is high or med
      ORCH->>LLM: rationale(score breakdown + evidence ONLY)
      LLM-->>ORCH: one paragraph
      ORCH->>ORCH: reject if it contains a number not in the input
    else watch tier
      ORCH->>ORCH: skip — not worth an LLM call
    end

    ORCH->>S3: GET snapshot ~30d ago → delta baseline
    ORCH->>ORCH: aggregate company scores
    ORCH->>S3: PUT snapshot, then signals, companies, index
    Note over ORCH,S3: snapshot FIRST — a crash mid-publish<br/>must not leave the index without a baseline
  end

  ORCH->>S3: PUT runs/<id>/manifest.json (ok | degraded)
  ORCH->>IDX: refresh in-memory index
  opt notifications enabled AND score ≥ threshold
    ORCH->>NTF: dispatch — idempotent per (run, signal)
  end
```

---

## 3. Analyst opens Radar

```mermaid
sequenceDiagram
  autonumber
  participant U as Analyst
  participant RV as RadarView
  participant BFF as /api/atlas/signals
  participant SC as eugene_scout
  participant IDX as in-memory index

  U->>RV: open /nextgen/radar
  RV->>BFF: GET ?type=&priority=&limit=200
  BFF->>BFF: currentUser() → 401 if absent
  BFF->>BFF: scope = user.focusArea (server-set, not client-supplied)
  BFF->>SC: GET /signals?ui_area=hematology&…
  SC->>IDX: filter → rank by score, then recency → page
  IDX-->>SC: rows + counts + last_run
  SC-->>BFF: JSON
  BFF-->>RV: SignalsResponse {degraded:false}
  RV->>U: ranked rows · priority badges · source links · "last scanned"

  alt scanner unreachable
    BFF-->>RV: {signals:[], degraded:true, reason}
    RV->>U: "Scanning service unavailable" banner
    Note over RV,U: an empty Radar because the scanner is down<br/>must never look like a quiet night
  end

  U->>RV: click "Why"
  RV->>U: factor-by-factor breakdown + rationale, labelled AI-WRITTEN or COMPUTED

  U->>RV: click a source badge
  RV->>U: opens the upstream record (ClinicalTrials / PubMed / Google Patents / SEC)

  U->>RV: dismiss
  RV->>BFF: PATCH /api/atlas/signals/<id> {dismissed:true}
  BFF->>SC: PATCH → rewrite curated tier
  Note over SC: written through, so the 02:00 scan<br/>honours the decision instead of undoing it
```

---

## 4. Data model

```mermaid
erDiagram
  SCAN_RUN ||--o{ SIGNAL : produced
  SIGNAL ||--|{ SIGNAL_SOURCE : "cited by"
  COMPANY_SCORE ||--o{ SIGNAL : "derived from"
  SCAN_RUN ||--o{ SOURCE_REPORT : "audit"

  SCAN_RUN {
    string run_id PK "timestamp-prefixed; lexical order = chronological"
    string trigger "cron | manual | startup | test"
    string status "ok | degraded | failed | skipped"
    int signals_new
    int companies_scored
  }
  SIGNAL {
    string id PK "sha256(source:external_id) — stable across runs"
    string area
    string type "Trial | Patent | Publication | Corporate"
    float score "0-100, deterministic"
    json score_breakdown "every factor + its inputs"
    string priority "high | med | watch"
    string rationale_kind "llm | template — provenance is shown"
    date published
    datetime detected_at "carried forward; NOT reset each scan"
    bool dismissed "carried forward; an analyst decision"
  }
  SIGNAL_SOURCE {
    string source "clinicaltrials | europepmc_lit | europepmc_pat | sec_edgar"
    string external_id
    string url "always http(s), validated at the boundary"
  }
  COMPANY_SCORE {
    string id PK "sha256(normalised name) — deterministic, survives rebuild"
    float score "best signal + bounded support bonus"
    float delta_30d "0 when no baseline snapshot exists"
    int signal_count
  }
  SOURCE_REPORT {
    string source
    bool ok
    int fetched
    int kept
    string error "why the column is thin, if it is"
  }
```

---

## 5. Scoring flow

```mermaid
flowchart LR
  A[RawSignal] --> B{area_fit<br/>keyword overlap}
  A --> C{stage_fit<br/>Phase I/II peaks}
  A --> D{recency<br/>vs source window}
  A --> E{modality_fit<br/>CSL capability}
  A --> F{corroboration<br/>independent sources}
  A --> G{company_context<br/>prior activity}

  B & C & D & E & F & G --> H["applicable factors only<br/>(N/A ≠ zero)"]
  H --> I["Σ weight×value ÷ Σ applied weight × 100"]
  I --> J{thresholds}
  J -->|≥75| K[HIGH]
  J -->|≥55| L[MED]
  J -->|else| M[WATCH]

  I --> N[score_breakdown<br/>persisted with every factor's inputs]
  K & L --> O[rationale via LLM]
  O --> P{contains a number<br/>not in the input?}
  P -->|yes| Q[discard → template]
  P -->|no| R[keep, label AI-WRITTEN]

  style I fill:#e8e4ff
  style P fill:#ffe8e8
```

The red node is the fence. It is the difference between a briefing an analyst can rely on and
one containing a confident, fabricated statistic.

---

## 6. Deployment

```mermaid
graph LR
  subgraph compose["docker compose — eugene-net"]
    UI["eugene_agent_ui_next<br/>:18502"]
    SCOUT["eugene_scout<br/>:18300"]
    WS["eugene_ws<br/>:18000"]
    ADE["eugene_ade<br/>:18100"]
    ING["eugene_ingestion<br/>:18200 · 01:00"]
    PG[("atlas_postgres<br/>auth, conversations")]
    NEO[("neo4j")]
  end

  S3[("s3://eugene-scout-…<br/>signals")]
  AWS["Bedrock · Nova"]

  UI --> SCOUT & WS & ADE
  UI --> PG
  SCOUT --> S3
  SCOUT -.rationale.-> AWS
  ING --> ADE --> NEO
  WS --> NEO
```

`eugene_scout` scans at **02:00**, after `eugene_ingestion`'s **01:00** sweep, so it sees the
papers that run has just indexed rather than racing it.

---

## 7. Where each PDF requirement landed

| Use-case requirement | Implementation |
|---|---|
| Scheduled orchestrator agent | `orchestrator.py` + APScheduler cron |
| Sub-agents across ClinicalTrials, PubMed, EDGAR, patents | Four collectors behind one `Collector` protocol |
| Entity extraction linked to internal ontology | `enrich.py` — taxonomy keywords + Neo4j linkage |
| Scoring against configurable BD criteria | `scoring.py` + `config/scan_config.json` |
| Ranked output to a structured store | S3 `curated/`, served from the in-memory index |
| Report-generation agent | `digest.py` → Markdown → `/briefing` page → `createArtifact()` → `/a/<id>` with MD/HTML/DOCX/PDF export |
| High-scoring signals pushed with a one-paragraph rationale | `notify.py`, off by default, idempotent |
| 8–12 ranked companies, rationale, sources, next action | `digest.py` — all four, with the band honestly under-filled on a quiet week |
| Human-in-the-loop checkpoints | Low-confidence signals are ranked, never suppressed; dismissal is an explicit analyst action |
| Auditability | `runs/` manifests + `score_breakdown` + `signal_sources` — every claim traces to a URL |
| Configurable thresholds, not code | Settings › Scanning, stored in S3, versioned |
