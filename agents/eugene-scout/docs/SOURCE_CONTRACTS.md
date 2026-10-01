# Source contracts — verified live, 2026-08-08

Every field the collectors read is listed here alongside a real response captured on the date
above. Nothing in `scout/collectors/` may reference a field that does not appear in this file.
Re-verify and update this document whenever a collector changes.

Common request posture for all sources:

```
User-Agent: CSL-Atlas-Scout/1.0 (biomedical BD intelligence; contact: semanticraj@gmail.com)
Accept: application/json
timeout: 20s connect+read
retry: 3 attempts, exponential backoff, only on 429/5xx/timeout
```

---

## 1. ClinicalTrials.gov API v2 — VERIFIED ✅

```
GET https://clinicaltrials.gov/api/v2/studies
  ?query.term=<free text>
  &pageSize=<int>
  &sort=LastUpdatePostDate:desc
```

Observed `HTTP 200`. Response root: `{"studies": [...], "nextPageToken": "..."}`.

Fields consumed, all confirmed present in the live sample:

| Path | Sample value |
|---|---|
| `protocolSection.identificationModule.nctId` | `NCT06003387` |
| `protocolSection.identificationModule.briefTitle` | `Efficacy and Safety of CSL222 (Etranacogene Dezaparvovec) Gene Therapy…` |
| `protocolSection.identificationModule.organization.fullName` | `CSL Behring` |
| `protocolSection.statusModule.overallStatus` | `RECRUITING` |
| `protocolSection.statusModule.startDateStruct.date` | `2024-01-30` |
| `protocolSection.statusModule.lastUpdatePostDateStruct.date` | `2026-08-07` |
| `protocolSection.statusModule.studyFirstPostDateStruct.date` | `2023-08-22` |
| `protocolSection.sponsorCollaboratorsModule.leadSponsor.name` | `CSL Behring` |
| `protocolSection.sponsorCollaboratorsModule.leadSponsor.class` | `INDUSTRY` |
| `protocolSection.designModule.phases[]` | `["PHASE3"]` |
| `protocolSection.designModule.studyType` | `INTERVENTIONAL` |
| `protocolSection.designModule.enrollmentInfo.count` | `35` |
| `protocolSection.conditionsModule.conditions[]` | `["Hemophilia B"]` |
| `protocolSection.armsInterventionsModule.interventions[].name` | `CSL222 (AAV5-hFIXco-Padua)` |
| `protocolSection.descriptionModule.briefSummary` | `The purpose of this study is to assess…` |

Phase enum observed: `PHASE1`, `PHASE2`, `PHASE3`, `PHASE4`, `NA`, `EARLY_PHASE1`.
Record URL: `https://clinicaltrials.gov/study/{nctId}`.

Date used for recency: `lastUpdatePostDateStruct.date`. **This sort IS honoured** (verified: first
result had `2026-08-07`, the most recent available), but the collector still date-filters because
sort correctness is not a contract we control.

---

## 2. Europe PMC — literature (`SRC:MED`) — VERIFIED ✅

```
GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
  ?query=(<terms>) AND SRC:MED
  &format=json&pageSize=<int>&resultType=lite&sort=P_PDATE_D desc
```

Observed `HTTP 200`. Root: `{"version":"6.9","hitCount":57734,"resultList":{"result":[…]}}`.

| Path | Sample value |
|---|---|
| `resultList.result[].id` | `42308604` |
| `resultList.result[].source` | `MED` |
| `resultList.result[].pmid` | `42308604` |
| `resultList.result[].pmcid` | `PMC13271316` (absent on many records) |
| `resultList.result[].doi` | `10.1016/j.biomaterials.2026.124381` |
| `resultList.result[].title` | `Precision glycoengineered AAV capsids enhance hepatocyte targeting…` |
| `resultList.result[].authorString` | `Luo J, Shi Y, Ji D, …` |
| `resultList.result[].journalTitle` | `Biomaterials` |
| `resultList.result[].pubYear` | `2026` |
| `resultList.result[].firstPublicationDate` | `2026-06-11` |
| `resultList.result[].firstIndexDate` | `2026-06-18` |
| `resultList.result[].isOpenAccess` | `N` |
| `resultList.result[].citedByCount` | `0` |

URL: `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` when `pmid` present, else
`https://europepmc.org/article/{source}/{id}`.

### ⚠️ The sort is NOT honoured — date filtering is mandatory

Verified 2026-08-08 with `sort=P_PDATE_D desc`: the **first** result had
`firstPublicationDate=2026-06-11`, two months stale, while `hitCount` was 57,734. This reproduces
exactly what `agents/eugene-agent-ui-next/lib/atlas/intel.ts` (lines 50–75) and
`src/foundation/router/digest_router.py` already document. **Never trust ordering from this API.**
Collectors over-fetch (`pageSize = limit × 5`), then filter by an absolute date window, then sort
locally.

---

## 3. Europe PMC — patents (`SRC:PAT`) — VERIFIED ✅

Same endpoint and response shape as §2 with `SRC:PAT`. `hitCount: 1632` for `(factor VIII)`.

| Path | Sample value |
|---|---|
| `resultList.result[].id` | `US2012045819` / `WO2012038315` |
| `resultList.result[].source` | `PAT` |
| `resultList.result[].title` | `BINDING MOLECULES FOR HUMAN FACTOR VIII AND FACTOR VIII-LIKE PROTEINS` |
| `resultList.result[].authorString` | `YU JINAN, POTTER M DANIEL, …` (assignees/inventors, not authors) |
| `resultList.result[].pubYear` | `2012` |
| `resultList.result[].firstPublicationDate` | `2011-09-23` |

URL: `https://europepmc.org/article/PAT/{id}`. The `id` prefix is the jurisdiction (`US`, `WO`, `EP`).

**Confirmed stale-by-default:** with no explicit sort the first two results were from 2011. This is
the precise bug that put 2002-era grants under an "overnight" heading. Patents get a much wider
window (540 days) than literature because grant lag is measured in years — but the window is still
enforced.

---

## 4. SEC EDGAR full-text search — VERIFIED ✅

```
GET https://efts.sec.gov/LATEST/search-index
  ?q=<quoted phrase>
  &forms=8-K,S-1,424B4
  &startdt=YYYY-MM-DD&enddt=YYYY-MM-DD
```

Observed `HTTP 200`. Elasticsearch-shaped response.

| Path | Sample value |
|---|---|
| `hits.total.value` | `1784` |
| `hits.hits[]._id` | `0001628280-24-032815:exhibit-991072424.htm` |
| `hits.hits[]._source.display_names[]` | `SANGAMO THERAPEUTICS, INC  (SGMO)  (CIK 0001001233)` |
| `hits.hits[]._source.ciks[]` | `0001001233` |
| `hits.hits[]._source.file_date` | `2024-07-24` |
| `hits.hits[]._source.form` | `8-K` |
| `hits.hits[]._source.root_forms[]` | `["8-K"]` |
| `hits.hits[]._source.adsh` | `0001628280-24-032815` |
| `hits.hits[]._source.sics[]` | `2836` (2836 = Biological Products) |
| `hits.hits[]._source.biz_states[]` | `CA` |

`display_names` is parsed with the regex `^(?P<name>.+?)\s+\((?P<ticker>[A-Z.]+)\)\s+\(CIK (?P<cik>\d+)\)$`
— ticker is absent for private/foreign filers, so the pattern degrades to name-only.

Document URL: `https://www.sec.gov/Archives/edgar/data/{cik_int}/{adsh_no_dashes}/{filename}`
where `filename` is the part of `_id` after the colon. Filing index URL (always valid, used as the
fallback): `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}`.

Date range **is** honoured: `startdt=2026-06-01&enddt=2026-08-08` returned 27 hits, top result
uniQure N.V. dated `2026-06-19`. Rate limit: SEC asks for ≤10 req/s and a contact-bearing
User-Agent; the collector serialises its requests with a 150 ms floor between calls.

---

## Object storage — VERIFIED ✅

Bucket `s3://eugene-scout-087084717211` (account 087084717211, us-east-1), created 2026-08-08:

- Public access fully blocked, SSE-S3 (AES256) with bucket keys, versioning **enabled**.
- Lifecycle: `raw/` objects expire at 90 days (staging is reproducible, not precious);
  non-current versions of `curated/` and `runs/` expire at 90 days; incomplete multipart
  uploads aborted after 7 days.
- Round-trip `put`/`list` confirmed against `_probe/healthcheck.txt`.
