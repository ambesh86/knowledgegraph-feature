# ClinicalTrials.gov → Eugene graph

Three steps. All are idempotent and safe to re-run for a refresh.

```bash
# 1. Download 1 year of studies across Eugene's four research themes (~3k studies)
python3 bin/ctgov/download_ctgov.py --months 12 --out dumps/ct_import/ctgov_raw.json

# 2. Transform to CSV, linking trials to drug/disease nodes already in the graph
python3 bin/ctgov/build_ctgov_csv.py --raw dumps/ct_import/ctgov_raw.json --outdir dumps/ct_import

# 3. Load (dumps/ct_import is mounted at /var/lib/neo4j/import by docker-compose.yml)
cp bin/ctgov/load_ctgov.cypher dumps/ct_import/
docker exec -i eugene-neo4j cypher-shell -u neo4j -p eugene_local_2024 \
  -f /var/lib/neo4j/import/load_ctgov.cypher

# 4. Re-embed the vector corpus so fused search sees the new trials, then RESTART.
#    milvus-lite is embedded/single-process: the running API will not see a
#    collection built by this out-of-process CLI until it reconnects.
docker exec -w /app/src eugene-ws \
  python -m foundation.vector.corpus_ingest_service --labels clinical_trial,drug,disease
docker compose restart eugene_ws
curl -s localhost:18000/vector/fusion/health   # expect {"ready":true,...}
```

## What lands in the graph

`(:clinical_trial)` nodes keyed on `node_index` (offset 900,000+ so they cannot
collide with the PrimeKG id space), carrying `nct_id`, `title`, `status`, `phase`,
`study_type`, `enrollment`, `sponsor`, `start_date`, `completion_date`,
`conditions`, `interventions`, `themes`, `url`.

Linked to existing nodes by normalized name match:

```
(:drug)   -[:evaluated_in]-> (:clinical_trial)
(:disease)-[:featured_in]->  (:clinical_trial)
```

Those are the two relationship types the agent's system prompt already looks for.

## Verify

```bash
docker exec -i eugene-neo4j cypher-shell -u neo4j -p eugene_local_2024 \
  "MATCH (d:drug)-[:evaluated_in]->(t:clinical_trial)
   RETURN d.node_name AS drug, count(t) AS trials ORDER BY trials DESC LIMIT 10;"
```

## Known limits

- **Linkage is partial (~51%).** CT.gov intervention strings ("BIVV001",
  "rFVIIIFc-VWF-XTEN") frequently don't match graph `drug` names verbatim.
  Unmatched trials still load as nodes — searchable by name and NCT id, just not
  traversable from a drug/disease. Raising this would mean matching through the
  drug alias/synonym nodes (`fetch_drug_aliases`), which is the obvious next step.
- **Themes are hard-coded** in `download_ctgov.py` to mirror
  `agents/eugene-agent-ui-next/lib/atlas/areas.ts`. Changing focus areas means
  editing both.
- The older `src/clinicaltrail/` module is **not** on this path. It still backs
  `Neo4jClinicalTrialAdapter`, but its recursive pagination and `pageSize=25`
  make it unfit for bulk pulls.
