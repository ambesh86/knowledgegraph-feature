// ============================================================================
// ClinicalTrials.gov → Eugene graph loader
//
// Idempotent: MERGE on node_index / (start,end,type) means re-running updates
// in place instead of duplicating. Safe to run after every refresh download.
//
// Requires ./dumps/ct_import mounted at /var/lib/neo4j/import (docker-compose.yml).
//
// Run:
//   docker exec -i eugene-neo4j cypher-shell -u neo4j -p eugene_local_2024 \
//     -f /var/lib/neo4j/import/load_ctgov.cypher
// ============================================================================

// --- 1. Indexes FIRST -------------------------------------------------------
// Without these the edge pass below does a full scan per row across 130k+ nodes.
CREATE INDEX clinical_trial_idx      IF NOT EXISTS FOR (n:clinical_trial) ON (n.node_index);
CREATE INDEX clinical_trial_node_id  IF NOT EXISTS FOR (n:clinical_trial) ON (n.node_id);
CREATE INDEX clinical_trial_nct      IF NOT EXISTS FOR (n:clinical_trial) ON (n.nct_id);
CREATE INDEX clinical_trial_name     IF NOT EXISTS FOR (n:clinical_trial) ON (n.node_name);
CREATE INDEX clinical_trial_status   IF NOT EXISTS FOR (n:clinical_trial) ON (n.status);
// Edge endpoints resolve by node_index on drug/disease. `drug_idx_unique`
// already exists; disease has no node_index index yet.
CREATE INDEX disease_idx             IF NOT EXISTS FOR (n:disease) ON (n.node_index);

// --- 2. Trial nodes ---------------------------------------------------------
LOAD CSV WITH HEADERS FROM 'file:///ctgov_nodes.csv' AS row
CALL (row) {
  MERGE (n:clinical_trial { node_index: row.`node_index:ID` })
  SET n.node_id          = row.node_id,
      n.node_label       = row.`node_label:LABEL`,
      n.node_name        = row.node_name,
      n.node_source      = row.node_source,
      n.nct_id           = row.nct_id,
      n.title            = row.title,
      n.status           = row.status,
      n.phase            = row.phase,
      n.study_type       = row.study_type,
      n.enrollment       = row.enrollment,
      n.sponsor          = row.sponsor,
      n.start_date       = row.start_date,
      n.completion_date  = row.completion_date,
      n.conditions       = row.conditions,
      n.interventions    = row.interventions,
      n.themes           = row.themes,
      n.url              = row.url,
      n.for_clinical_trial = true
} IN TRANSACTIONS OF 1000 ROWS;

// --- 3. Drug → trial edges --------------------------------------------------
// Split by :TYPE because Cypher cannot MERGE a dynamically-typed relationship;
// dynamic types are only supported on CREATE, which is not idempotent.
LOAD CSV WITH HEADERS FROM 'file:///ctgov_edges.csv' AS row
CALL (row) {
  WITH row WHERE row.`:TYPE` = 'evaluated_in'
  MATCH (d:drug           { node_index: row.`:START_ID` })
  MATCH (t:clinical_trial { node_index: row.`:END_ID`   })
  MERGE (d)-[r:evaluated_in]->(t)
  SET r.display_relation = row.display_relation,
      r.source           = 'ClinicalTrials.gov'
} IN TRANSACTIONS OF 1000 ROWS;

// --- 4. Disease → trial edges (see note above on the split) ------------------
LOAD CSV WITH HEADERS FROM 'file:///ctgov_edges.csv' AS row
CALL (row) {
  WITH row WHERE row.`:TYPE` = 'featured_in'
  MATCH (d:disease        { node_index: row.`:START_ID` })
  MATCH (t:clinical_trial { node_index: row.`:END_ID`   })
  MERGE (d)-[r:featured_in]->(t)
  SET r.display_relation = row.display_relation,
      r.source           = 'ClinicalTrials.gov'
} IN TRANSACTIONS OF 1000 ROWS;

// --- 5. Record the snapshot date --------------------------------------------
// Data with no recorded ingest date cannot be dated honestly in an answer — the
// agent ends up implying snapshot facts are current. /health/data-freshness reads
// this node, and the agent puts the date into its system prompt every turn.
MATCH (t:clinical_trial)
WITH count(t) AS trial_count
MERGE (s:DataSnapshot {source: 'ClinicalTrials.gov'})
SET s.ingested_at  = datetime(),
    s.record_count = trial_count,
    s.window       = 'last 12 months of study start dates',
    s.loader       = 'bin/ctgov/load_ctgov.cypher';
