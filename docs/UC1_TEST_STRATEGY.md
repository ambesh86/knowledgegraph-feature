# UC1 — Test Strategy

**327 Python tests · 86% line coverage · 25 Playwright specs against a live deployment.**

The organising question for this suite is not "what percentage of lines execute" but
**"what could this system get wrong that nobody would notice?"** A BD intelligence tool
fails quietly: a wrong ranking still renders, a stale patent still looks like news, a
fabricated statistic still reads as confident prose. Every layer below is aimed at a
specific class of silent wrongness.

---

## 1. Layers

| Layer | Count | Runtime | What it protects | Network |
|---|---|---|---|---|
| Unit — pure logic | ~150 | <1s | Scoring determinism, text normalisation, dedup, company aggregation | none |
| Contract — collectors | 38 | <1s | That parsers match what the APIs *actually send* | none (recorded fixtures) |
| Integration — storage & pipeline | 89 | ~10s | S3 key layout, gzip round trip, publish ordering, run identity | in-process S3 (moto) |
| API — HTTP surface | 40 | ~5s | Status codes, auth gating, cold-start shapes, filter semantics | in-process |
| Stress — scale & hostile input | 34 | ~25s | Query latency at 50k signals, O(n²) regressions, unicode/oversized/malformed input | none |
| E2E — browser | 25 | ~90s | Real data end to end, working links, degraded states | **live stack** |

```bash
pytest                       # everything, hermetic, ~53s
pytest -m "not stress"       # fast inner loop
pytest --cov=scout           # coverage report
npx playwright test          # against a running deployment
```

---

## 2. The rules that make the suite trustworthy

**Hermetic by default.** No test in the Python suite touches the network or real S3.
`moto` provides an in-process S3, so the storage layer is exercised *for real* — the key
layout, the gzip round trip and the JSONL encoding are the parts most likely to break
silently, and mocking `Storage` would test none of them.

**Frozen clock.** `FROZEN_TODAY` is fixed. Recency is a scoring input, so a suite using
the real date would score differently every day and its assertions would rot.

**Fixtures are captured, not invented.** Collector fixtures are trimmed copies of real
responses recorded in `SOURCE_CONTRACTS.md`. A hand-written fixture only proves the
parser matches the fixture — a tautology. These prove it matches what the API sends.

**Every bug found in production became a test.** Eleven regression tests carry an
incident in their docstring. They are listed in §4 because that list is the honest
record of what this system got wrong.

---

## 3. What each layer is actually defending

### Determinism (`test_scoring.py`)
The product promise is a ranking an analyst can challenge. So: the same signal scored
100 times must produce one value; the breakdown must arithmetically reconstruct the
badge number; `today` is an argument so historical replay is meaningful; and a factor
that does not apply is *excluded* rather than scored zero — the alternative
systematically punishes literature for having no development phase.

### The anti-hallucination fence (`test_rationale.py`)
The highest-cost failure this system could produce is a fabricated statistic inside a
confident briefing. `_verify` rejects any output containing a digit absent from its
input, and these tests parameterise the characteristic fabrications — invented
enrolment counts, funding figures, percentages, fold-changes. One test asserts
deliberate over-strictness: prose with more decimal precision than the input is
rejected, because the cost of that is a correct template and the cost of relaxing it is
a number nobody catches.

### Assembly (`test_orchestrator.py`)
Unit tests proved the parts; this proves they hold together. Staging happens *before*
scoring, so a pipeline bug cannot corrupt the archive that exists to recover from
pipeline bugs. A dead source degrades one column, not the run. A dismissal survives the
next scan. A re-seen signal is not "new" — otherwise "since you last looked" reports
the entire corpus every night.

### Scale (`test_stress.py`)
The whole architecture rests on the claim that the corpus is small enough to filter in
memory. That claim deserves a test: query latency is asserted at 1k / 10k / 50k
signals. This layer earns its keep — it caught a real O(n²) in cross-source dedup
(14.6s → <1s for 3,000 records) that no functional test would have noticed.

### Design intent (`test_graph_review.py`)
Two decisions are pinned as tests because a reasonable future change could reverse
either:
- **Graph membership must not affect the score.** A drug absent from CSL's graph is
  more likely the novel opportunity. The test asserts `score()` has no such parameter,
  so adding one is a visible act.
- **Low-confidence signals are flagged, never suppressed.** A shorter Radar looks
  better; an analyst who discovers something was quietly dropped stops trusting
  everything that remains.

### Social failure modes (`test_notify.py`)
This module messages real people, so its failures are social. Two are pinned hard:
nothing sends unless explicitly enabled (a `docker compose up` must not alert the BD
team), and dispatch is idempotent per signal (re-running a failed job must not
re-announce the morning's alerts). A failed delivery must *not* mark signals as sent,
or an outage silently swallows the alert forever.

### Truth on screen (`e2e/radar.spec.ts`)
E2E runs against **real data from a real scan** — deliberately not fixtures, because
the defect class here is "the panel shows something plausible that is not true", which
a mocked test cannot see. Assertions are on *contracts*, never on counts: every source
link resolves to one of the four known upstream hosts; ordering is monotonic; the
briefing carries rationale + sources + next action on every entry. Nothing asserts
"there are exactly N signals", so a quiet news day is not a test failure.

---

## 4. Regression tests with an incident behind them

| Test | What went wrong in production |
|---|---|
| `test_british_spelling_matches_american_keyword` | "Haemophilia" matched zero keywords — every European journal silently sank to the bottom |
| `test_undated_item_is_dropped` | Undated records let 2002 patents appear under an "overnight" heading |
| `test_zero_results_404_is_not_a_failure` | USPTO returns 404 for empty results; whole areas were marked degraded on quiet nights |
| `test_keyword_clause_is_parenthesised` | Lucene binds AND tighter than OR — the date filter applied to only the last keyword |
| `test_zero_keyword_match_is_rejected` | An oncology trial entered the hemophilia area on the word "inhibitor" |
| `test_generic_only_match_is_rejected` | Hearing-loss and phenylketonuria patents entered on "gene therapy" alone |
| `test_company_variants_normalise_together` | Bioverativ appeared as two rows, splitting one company's evidence |
| `test_weak_extra_signals_do_not_lower_the_score` | Top-k mean made a better-documented company rank *lower* |
| `test_module_imports_from_a_shallow_path` | `parents[4]` crash-looped the container while every local test passed |
| `test_ids_are_unique_within_the_same_second` | Second-precision run ids collided; the second run overwrote the first's manifest |
| `test_cross_source_grouping_stays_tractable` | O(n²) dedup: 14.6s for 3,000 records |

---

## 5. Coverage, and where it is deliberately thin

86% overall. Where it is lower, the reason is explicit:

| Module | Cov | Why |
|---|---|---|
| `graph.py` | 100% | |
| `models.py`, `config.py` | 98% | |
| `orchestrator.py` | 90% | |
| `storage.py` | 88% | Uncovered: botocore error branches that need injected AWS faults |
| `epo.py` | 80% | Ships **disabled** — written against EPO's published contract, unverifiable without an OAuth key |
| `rationale.py` | 80% | Uncovered: the Anthropic/OpenAI SDK call bodies; the Bedrock path and the fence are covered |
| `api.py` | 76% | Uncovered: FastAPI error handlers reachable only via malformed ASGI |
| `notify.py` | 64% | Uncovered: SMTP transport, which needs a real mail server. **Webhook delivery was verified end-to-end against a live sink during deployment**, including idempotency |

Coverage is reported, not enforced as a gate. A percentage target encourages tests
written to touch lines rather than to catch defects, and this suite's value is
concentrated in the eleven regression tests above — none of which a coverage target
would have prompted anyone to write.

---

## 6. Known limitations this suite does not cover

Stated so nobody mistakes a green run for a guarantee:

- **EPO OPS** is unverified against a live response and ships disabled.
- **SMTP delivery** is untested in code; only the webhook path was proven live.
- **Company entity resolution** is improved but imperfect. Sibling entities of one
  parent (`Roche Holding` vs `Roche Products`) deliberately stay separate — a false
  merge attributes another company's pipeline and is far harder to notice than a
  duplicate row.
- **AWS deployment** is untested; everything runs on Docker Compose today.
- **Commercial sources** named in the PDF (Evaluate Pharma, Citeline) are not
  implemented — they require paid subscriptions.
