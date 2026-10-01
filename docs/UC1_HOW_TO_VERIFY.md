# UC1 — How to access and verify it

A hands-on checklist. Every item maps to a specific line in the PDF, and every item is
something **you can see yourself** rather than take on trust.

---

## Access

| | |
|---|---|
| **UI** | <http://localhost:18502/nextgen/login> |
| **Login** | `verify@csl.local` / `VerifyUC1-2026` |
| **Scanner API** | <http://localhost:18300/health> · docs at <http://localhost:18300/docs> |
| **S3** | `s3://eugene-scout-087084717211` |

If nothing loads:

```bash
docker compose up -d eugene_scout eugene_agent_ui_next
docker ps --filter name=eugene-scout --filter name=eugene-agent-ui-next
```

---

## Part 1 — Verify in the browser (5 minutes)

### Radar (⌘4) — "surfacing relevant partnership signals"

1. Signals are listed, ranked, newest-and-strongest first.
2. **Click any source badge** (`ClinicalTrials.gov`, `Europe PMC`, `USPTO`, `SEC EDGAR`).
   It opens the real upstream record. *This is the check that matters most: if the data
   were fabricated, these links would not resolve to a matching study.*
3. **Click "Why"** on any row. You get the score broken into six factors with the inputs
   that produced each — `matched: factor ix, hemophilia`, `stage: PHASE1`,
   `4d old, 45d window`. This is the PDF's "BD leaders can interrogate and challenge".
4. Look for the **`AI-WRITTEN` / `COMPUTED`** badge on the rationale. LLM prose and
   deterministic prose are labelled differently on purpose.
5. Look for **`REVIEW`** badges and the "Worth a second look" panel — the PDF's
   "flag low-confidence outputs rather than suppressing uncertainty". Note the signal is
   still listed, not hidden.
6. Look for **"Known to the CSL graph"** on some rows, with the resolved node id, and the
   line saying graph membership does *not* affect the score.
7. **Filter chips** narrow the list; the counts stay visible so you can still see how
   many mediums exist while viewing highs.
8. **Rescan** runs a live scan (~80s) and the list refreshes.

### Watchlist (⌘5) — "ranked partner portfolio"

- Companies ranked by score, with signal counts and areas.
- `Δ 30d` shows **—** where no 30-day baseline exists yet. It does not show a fake `+0`.
- Click a row to pivot to that company's signals.

### Briefing (⌘6) — the PDF's headline deliverable

Quoted: *"a ranked weekly briefing showing 8–12 high-priority biotech companies with
complementary pipeline assets, each accompanied by a plain-English rationale, the key
data sources consulted, and a 'next action' recommendation."*

Check each entry has all four: **rationale**, **sources consulted**, **evidence links**,
**next action**. If fewer than 8 companies clear the bar you will see a notice saying so
— the list is never padded to hit the number.

**"Publish & share"** turns it into a shareable page at `/nextgen/a/<id>` with
Markdown / HTML / Word / PDF export.

### Today (⌘1)

- The counter and "since you last looked" strip are computed from real data.
- Open Today, go away, come back — the "new since" count reflects what actually changed.

### Settings → Partnership scanning

- The cron schedule, and which sources are available.
- **Scoring weights are editable.** Change a threshold, save, reload — it persists.
  This is "configurable thresholds, managed as configuration not code".
- **Recent scans** shows the audit trail, including which source failed and why.

---

## Part 2 — Verify from the command line

```bash
# The scanner is alive, S3 reachable, schedule armed
curl -s localhost:18300/status | python3 -m json.tool | head -30
```

```bash
# Prove the scheduler ran on its own overnight — no human triggered this.
# `trigger: cron` is the proof. Read from S3, not from container logs, because
# logs reset on every rebuild while the run manifests persist.
curl -s "localhost:18300/runs?limit=10" | python3 -c "
import json,sys
for r in json.load(sys.stdin)['runs']:
    print(f\"{r['run_id']:26} {r['trigger']:7} {r['status']:9} signals={r['signals_kept']}\")"
```

You should see a row with `trigger=cron` at a `T0200` timestamp. Expect the odd
`degraded` row in the history too — that is a source having failed on that run, which is
the audit trail doing its job rather than a problem.

```bash
# Every signal has at least one resolvable upstream link
curl -s "localhost:18300/signals?limit=400" | python3 -c "
import json,sys
s=json.load(sys.stdin)['signals']
bad=[x for x in s if not x['sources'] or not x['sources'][0]['url'].startswith('https://')]
print(f'{len(s)} signals, {len(bad)} without a usable source link')"
```

```bash
# Spot-check that a link really resolves (should print 200)
curl -s -o /dev/null -w '%{http_code}\n' \
  "$(curl -s 'localhost:18300/signals?limit=1' | python3 -c 'import json,sys;print(json.load(sys.stdin)["signals"][0]["sources"][0]["url"])')"
```

```bash
# Scoring is reproducible — the same signal scores identically every time
curl -s "localhost:18300/signals?limit=1" | python3 -c "
import json,sys
x=json.load(sys.stdin)['signals'][0]
b=x['score_breakdown']
tw=sum(f['weight'] for f in b['factors'])
recomputed=100*sum(f['contribution'] for f in b['factors'])/tw
print(f\"badge {x['score']}  recomputed from factors {recomputed:.2f}\")"
```

```bash
# Both S3 tiers: raw/ is staging, curated/ is final
aws s3 ls s3://eugene-scout-087084717211/ --recursive | awk '{print $4}' | cut -d/ -f1 | sort | uniq -c
```

```bash
# The weekly briefing as Markdown
curl -s "localhost:18300/digest?area=hemophilia&format=markdown" | head -40
```

---

## Part 3 — Run the tests yourself

```bash
# Python: 328 tests, hermetic (no network, in-process S3), ~55s
cd agents/eugene-scout && .venv/bin/python -m pytest -q

# With coverage
.venv/bin/python -m pytest --cov=scout --cov-report=term

# Browser: 42 specs against the running deployment, ~2 min
cd agents/eugene-agent-ui-next
ATLAS_BASE_URL=http://localhost:18502/nextgen npx playwright test --reporter=line
```

The Playwright suite asserts against **real scan output**, not fixtures — that is
deliberate, because the failure this feature exists to prevent is "the panel shows
something plausible that is not true", which a mocked test cannot catch.

---

## Part 4 — PDF requirement → where to see it

| Use-case requirement | Verify by |
|---|---|
| Scheduled orchestrator agent | `docker logs eugene-scout \| grep cron` — the 02:00 run |
| Sub-agents across ClinicalTrials, PubMed, patents, SEC | Source badges on Radar rows; `/status` → `sources_available` |
| Entity extraction linked to internal ontology | "Known to the CSL graph" on Radar rows |
| Scoring against configurable BD criteria | Settings → weights; the "Why" panel |
| Ranked output in a structured store | `aws s3 ls .../curated/` |
| Report-generation agent | Briefing (⌘6) → Publish & share |
| High-scoring signals pushed with a rationale | Settings → Send test *(off by default — see below)* |
| 8–12 ranked companies + rationale + sources + next action | Briefing entries |
| Human-in-the-loop checkpoints | `REVIEW` badges + "Worth a second look" |
| Auditability | Settings → Recent scans; `runs/` in S3 |
| Configurable thresholds, not code | Settings → weights persist across reload |

---

## What is deliberately NOT working, and why

Stated plainly so a green checklist is not mistaken for total coverage.

| Item | Status |
|---|---|
| **EPO patent source** | Built and unit-tested, **ships disabled**. Needs a free OAuth key from developers.epo.org. Without one the response shape cannot be confirmed against a live call, and every other source here was verified before being trusted. |
| **Notifications** | Off by default, by design — a `docker compose up` must not message the BD team. Webhook delivery *was* verified end-to-end against a live sink; SMTP was not. Turn on with `SCOUT_NOTIFY_ENABLED=true` + `SCOUT_NOTIFY_WEBHOOK_URL`. |
| **AWS deployment** | Not done. Everything runs on Docker Compose; `infrastructure/` is untouched. |
| **Evaluate Pharma / Citeline** | Named in the PDF, not implemented — they require paid subscriptions. |
| **Company entity resolution** | Improved but imperfect. Sibling entities of one parent (`Roche Holding` vs `Roche Products`) stay separate on purpose: a false merge attributes another company's pipeline and is far harder to spot than a duplicate row. |

---

## If something looks wrong

```bash
docker logs eugene-scout --tail 50          # scanner
docker logs eugene-agent-ui-next --tail 50  # UI
curl -s localhost:18300/status | python3 -m json.tool   # last run + per-source state
```

An empty Radar is **not** the same as a broken one. If the scanner is unreachable the UI
shows an explicit "Scanning service unavailable" banner rather than a blank list —
distinguishing "nothing found" from "nothing loaded" is a deliberate design property.
