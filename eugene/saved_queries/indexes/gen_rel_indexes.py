rels = [
    "anatomy_anatomy",
    "anatomy_protein_absent",
    "anatomy_protein_present",
    "bioprocess_bioprocess",
    "bioprocess_protein",
    "cellcomp_cellcomp",
    "cellcomp_protein",
    "contraindication",
    "disease_disease",
    "disease_phenotype_negative",
    "disease_phenotype_positive",
    "disease_protein",
    "drug_drug",
    "drug_effect",
    "drug_protein",
    "exposure_bioprocess",
    "exposure_cellcomp",
    "exposure_disease",
    "exposure_exposure",
    "exposure_molfunc",
    "exposure_protein",
    "indication",
    "molfunc_molfunc",
    "molfunc_protein",
    "pathway_pathway",
    "pathway_protein",
    "phenotype_phenotype",
    "phenotype_protein",
    "protein_protein",
]

# relationship display_relation indexes
rel_tmpl = "CREATE INDEX rel_{}_index IF NOT EXISTS FOR ()-[r:{}]-() ON (r.display_relation);"


for rel in rels:
    rel_cmd = rel_tmpl.format(rel, rel)
    print(rel_cmd)
