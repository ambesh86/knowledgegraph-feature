
// node name text indexes
DROP INDEX anatomy_node_name_index IF EXISTS;
DROP INDEX biological_process_node_name_index IF EXISTS;
DROP INDEX cellular_component_node_name_index IF EXISTS;
DROP INDEX disease_node_name_index IF EXISTS;
DROP INDEX drug_node_name_index IF EXISTS;
DROP INDEX effect_phenotype_node_name_index IF EXISTS;
DROP INDEX exposure_node_name_index IF EXISTS;
DROP INDEX gene_protein_node_name_index IF EXISTS;
DROP INDEX molecular_function_node_name_index IF EXISTS;
DROP INDEX pathway_node_name_index IF EXISTS;

// node source text indexes
DROP INDEX anatomy_node_source_index IF EXISTS;
DROP INDEX biological_process_node_source_index IF EXISTS;
DROP INDEX cellular_component_node_source_index IF EXISTS;
DROP INDEX disease_node_source_index IF EXISTS;
DROP INDEX drug_node_source_index IF EXISTS;
DROP INDEX effect_phenotype_node_source_index IF EXISTS;
DROP INDEX exposure_node_source_index IF EXISTS;
DROP INDEX gene_protein_node_source_index IF EXISTS;
DROP INDEX molecular_function_node_source_index IF EXISTS;
DROP INDEX pathway_node_source_index IF EXISTS;

// node index range indexes
DROP INDEX anatomy_node_index_index IF EXISTS;
DROP INDEX biological_process_node_index_index IF EXISTS;
DROP INDEX cellular_component_node_index_index IF EXISTS;
DROP INDEX disease_node_index_index IF EXISTS;
DROP INDEX drug_node_index_index IF EXISTS;
DROP INDEX effect_phenotype_node_index_index IF EXISTS;
DROP INDEX exposure_node_index_index IF EXISTS;
DROP INDEX gene_protein_node_index_index IF EXISTS;
DROP INDEX molecular_function_node_index_index IF EXISTS;
DROP INDEX pathway_node_index_index IF EXISTS;

// node id range indexes
DROP INDEX anatomy_node_id_index IF EXISTS;
DROP INDEX biological_process_node_id_index IF EXISTS;
DROP INDEX cellular_component_node_id_index IF EXISTS;
DROP INDEX disease_node_id_index IF EXISTS;
DROP INDEX drug_node_id_index IF EXISTS;
DROP INDEX effect_phenotype_node_id_index IF EXISTS;
DROP INDEX exposure_node_id_index IF EXISTS;
DROP INDEX gene_protein_node_id_index IF EXISTS;
DROP INDEX molecular_function_node_id_index IF EXISTS;
DROP INDEX pathway_node_id_index IF EXISTS;

// node idx range indexes
DROP INDEX anatomy_node_idx_index IF EXISTS;
DROP INDEX biological_process_node_idx_index IF EXISTS;
DROP INDEX cellular_component_node_idx_index IF EXISTS;
DROP INDEX disease_node_idx_index IF EXISTS;
DROP INDEX drug_node_idx_index IF EXISTS;
DROP INDEX effect_phenotype_node_idx_index IF EXISTS;
DROP INDEX exposure_node_idx_index IF EXISTS;
DROP INDEX gene_protein_node_idx_index IF EXISTS;
DROP INDEX molecular_function_node_idx_index IF EXISTS;
DROP INDEX pathway_node_idx_index IF EXISTS;

// pubmed indexes
DROP INDEX pubmed_document_node_idx_index IF EXISTS;
DROP INDEX pubmed_document_pmcid_index IF EXISTS;
DROP INDEX pubmed_document_pmid_index IF EXISTS;
DROP INDEX pubmed_document_is_pubmed_index IF EXISTS;
DROP INDEX pubmed_document_refresh_date_index IF EXISTS;
DROP INDEX pubmed_document_title_index IF EXISTS;

// clinical trail indexes, check for indexes created by the constraints
DROP INDEX clinical_trial_nct_number_index IF EXISTS;

// drop clinical trail indexes
DROP INDEX clinical_trial_nct_number_index IF EXISTS;
DROP INDEX pubmed_document_model2vec_embeddings_index IF EXISTS;
DROP INDEX drug_model2vec_embeddings_index IF EXISTS;
DROP INDEX disease_model2vec_embeddings_index IF EXISTS;
DROP INDEX gene_protein_model2vec_embeddings_index IF EXISTS;
DROP INDEX anatomy_model2vec_embeddings_index IF EXISTS;


DROP INDEX pgpub_prediction_embeddings_index IF EXISTS;
DROP INDEX pgpub_embeddings_index IF EXISTS;
DROP INDEX pgpub_prediction_embeddings_index IF EXISTS;
DROP INDEX uspto_application_application_number_text_index IF EXISTS;
DROP INDEX uspto_application_file_create_dtg_index IF EXISTS;
DROP INDEX uspto_application_is_uspto_index IF EXISTS;
DROP INDEX uspto_application_patent_number_index IF EXISTS;
DROP INDEX uspto_pgpub_application_number_text_index IF EXISTS;
DROP INDEX uspto_pgpub_filing_date_index IF EXISTS;
DROP INDEX uspto_pgpub_first_applicant_name_index IF EXISTS;
DROP INDEX uspto_pgpub_is_uspto_index IF EXISTS;

DROP INDEX csl_tpp_embeddings_index IF EXISTS;
DROP INDEX csl_tpp_is_csl_index IF EXISTS;
DROP INDEX csl_tpp_node_id_index IF EXISTS;
DROP INDEX csl_tpp_theraputic_area_index IF EXISTS;
DROP INDEX csl_tpp_node_index_index IF EXISTS;
DROP INDEX csl_tpp_prediction_embeddings_index IF EXISTS;
DROP INDEX csl_tpp_question_embeddings_index IF EXISTS;
DROP INDEX csl_tpp_question_is_csl_index IF EXISTS;
DROP INDEX csl_tpp_question_node_id_index IF EXISTS;
DROP INDEX csl_tpp_question_node_index_index IF EXISTS;


