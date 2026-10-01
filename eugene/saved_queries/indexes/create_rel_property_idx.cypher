CREATE INDEX rel_anatomy_anatomy_index IF NOT EXISTS FOR ()-[r:anatomy_anatomy]-() ON (r.display_relation);
CREATE INDEX rel_anatomy_protein_absent_index IF NOT EXISTS FOR ()-[r:anatomy_protein_absent]-() ON (r.display_relation);
CREATE INDEX rel_anatomy_protein_present_index IF NOT EXISTS FOR ()-[r:anatomy_protein_present]-() ON (r.display_relation);
CREATE INDEX rel_bioprocess_bioprocess_index IF NOT EXISTS FOR ()-[r:bioprocess_bioprocess]-() ON (r.display_relation);
CREATE INDEX rel_bioprocess_protein_index IF NOT EXISTS FOR ()-[r:bioprocess_protein]-() ON (r.display_relation);
CREATE INDEX rel_cellcomp_cellcomp_index IF NOT EXISTS FOR ()-[r:cellcomp_cellcomp]-() ON (r.display_relation);
CREATE INDEX rel_cellcomp_protein_index IF NOT EXISTS FOR ()-[r:cellcomp_protein]-() ON (r.display_relation);
CREATE INDEX rel_contraindication_index IF NOT EXISTS FOR ()-[r:contraindication]-() ON (r.display_relation);
CREATE INDEX rel_disease_disease_index IF NOT EXISTS FOR ()-[r:disease_disease]-() ON (r.display_relation);
CREATE INDEX rel_disease_phenotype_negative_index IF NOT EXISTS FOR ()-[r:disease_phenotype_negative]-() ON (r.display_relation);
CREATE INDEX rel_disease_phenotype_positive_index IF NOT EXISTS FOR ()-[r:disease_phenotype_positive]-() ON (r.display_relation);
CREATE INDEX rel_disease_protein_index IF NOT EXISTS FOR ()-[r:disease_protein]-() ON (r.display_relation);
CREATE INDEX rel_drug_drug_index IF NOT EXISTS FOR ()-[r:drug_drug]-() ON (r.display_relation);
CREATE INDEX rel_drug_effect_index IF NOT EXISTS FOR ()-[r:drug_effect]-() ON (r.display_relation);
CREATE INDEX rel_drug_protein_index IF NOT EXISTS FOR ()-[r:drug_protein]-() ON (r.display_relation);
CREATE INDEX rel_exposure_bioprocess_index IF NOT EXISTS FOR ()-[r:exposure_bioprocess]-() ON (r.display_relation);
CREATE INDEX rel_exposure_cellcomp_index IF NOT EXISTS FOR ()-[r:exposure_cellcomp]-() ON (r.display_relation);
CREATE INDEX rel_exposure_disease_index IF NOT EXISTS FOR ()-[r:exposure_disease]-() ON (r.display_relation);
CREATE INDEX rel_exposure_exposure_index IF NOT EXISTS FOR ()-[r:exposure_exposure]-() ON (r.display_relation);
CREATE INDEX rel_exposure_molfunc_index IF NOT EXISTS FOR ()-[r:exposure_molfunc]-() ON (r.display_relation);
CREATE INDEX rel_exposure_protein_index IF NOT EXISTS FOR ()-[r:exposure_protein]-() ON (r.display_relation);
CREATE INDEX rel_indication_index IF NOT EXISTS FOR ()-[r:indication]-() ON (r.display_relation);
CREATE INDEX rel_molfunc_molfunc_index IF NOT EXISTS FOR ()-[r:molfunc_molfunc]-() ON (r.display_relation);
CREATE INDEX rel_molfunc_protein_index IF NOT EXISTS FOR ()-[r:molfunc_protein]-() ON (r.display_relation);
CREATE INDEX rel_off-label use_index IF NOT EXISTS FOR ()-[r:off-label use]-() ON (r.display_relation);
CREATE INDEX rel_pathway_pathway_index IF NOT EXISTS FOR ()-[r:pathway_pathway]-() ON (r.display_relation);
CREATE INDEX rel_pathway_protein_index IF NOT EXISTS FOR ()-[r:pathway_protein]-() ON (r.display_relation);
CREATE INDEX rel_phenotype_phenotype_index IF NOT EXISTS FOR ()-[r:phenotype_phenotype]-() ON (r.display_relation);
CREATE INDEX rel_phenotype_protein_index IF NOT EXISTS FOR ()-[r:phenotype_protein]-() ON (r.display_relation);
CREATE INDEX rel_protein_protein_index IF NOT EXISTS FOR ()-[r:protein_protein]-() ON (r.display_relation);

// clinical trials

CREATE INDEX rel_studies_index IF NOT EXISTS FOR ()-[r:studies]-() ON (r.display_relation);