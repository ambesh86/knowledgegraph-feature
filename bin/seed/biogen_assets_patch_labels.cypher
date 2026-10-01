// =============================================================================
// Biogen seed — label-convention patch.
// Existing graph nodes carry `(:drug:DRUG)`, `(:disease:DISEASE)`,
// `(:gene_protein:GENE_PROTEIN)`.  Our seed used CamelCase singletons.
// Add the legacy labels so the existing /organizations/assets API picks
// them up.  Idempotent.
// =============================================================================

MATCH (d:Drug) WHERE d.node_id STARTS WITH "biogen_drug_"
SET d:drug:DRUG;

MATCH (d:Disease) WHERE d.node_id STARTS WITH "biogen_dz_"
SET d:disease:DISEASE;

MATCH (g:GeneProtein) WHERE g.node_id STARTS WITH "biogen_gp_"
SET g:gene_protein:GENE_PROTEIN;

// Trials already use the canonical "ClinicalTrial" CamelCase label, so no
// change needed for those.
