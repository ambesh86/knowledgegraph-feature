SHOW INDEXES;

// node label and relationship already exist, to recreate use
CREATE LOOKUP INDEX node_label_lookup IF NOT EXISTS FOR (n) ON EACH labels(n);
CREATE LOOKUP INDEX rel_type_lookup_index FOR ()-[r]-() ON EACH type(r);

// does not work, have to define all the node labels
// CREATE TEXT INDEX node_name_index IF NOT EXISTS FOR (n) ON EACH (n.node_name)

// node name text indexes
CREATE TEXT INDEX anatomy_node_name_index IF NOT EXISTS FOR (n:anatomy) ON (n.node_name);
CREATE TEXT INDEX biological_process_node_name_index IF NOT EXISTS FOR (n:biological_process) ON (n.node_name);
CREATE TEXT INDEX cellular_component_node_name_index IF NOT EXISTS FOR (n:cellular_component) ON (n.node_name);
CREATE TEXT INDEX disease_node_name_index IF NOT EXISTS FOR (n:disease) ON (n.node_name);   
CREATE TEXT INDEX drug_node_name_index IF NOT EXISTS FOR (n:drug) ON (n.node_name);
CREATE TEXT INDEX effect_phenotype_node_name_index IF NOT EXISTS FOR (n:effect_phenotype) ON (n.node_name);
CREATE TEXT INDEX exposure_node_name_index IF NOT EXISTS FOR (n:exposure) ON (n.node_name);
CREATE TEXT INDEX gene_protein_node_name_index IF NOT EXISTS FOR (n:gene_protein) ON (n.node_name);
CREATE TEXT INDEX molecular_function_node_name_index IF NOT EXISTS FOR (n:molecular_function) ON (n.node_name);
CREATE TEXT INDEX pathway_node_name_index IF NOT EXISTS FOR (n:pathway) ON (n.node_name);

// node source text indexes
CREATE TEXT INDEX anatomy_node_source_index IF NOT EXISTS FOR (n:anatomy) ON (n.node_source);
CREATE TEXT INDEX biological_process_node_source_index IF NOT EXISTS FOR (n:biological_process) ON (n.node_source);
CREATE TEXT INDEX cellular_component_node_source_index IF NOT EXISTS FOR (n:cellular_component) ON (n.node_source);
CREATE TEXT INDEX disease_node_source_index IF NOT EXISTS FOR (n:disease) ON (n.node_source);   
CREATE TEXT INDEX drug_node_source_index IF NOT EXISTS FOR (n:drug) ON (n.node_source);
CREATE TEXT INDEX effect_phenotype_node_source_index IF NOT EXISTS FOR (n:effect_phenotype) ON (n.node_source);
CREATE TEXT INDEX exposure_node_source_index IF NOT EXISTS FOR (n:exposure) ON (n.node_source);
CREATE TEXT INDEX gene_protein_node_source_index IF NOT EXISTS FOR (n:gene_protein) ON (n.node_source);
CREATE TEXT INDEX molecular_function_node_source_index IF NOT EXISTS FOR (n:molecular_function) ON (n.node_source);
CREATE TEXT INDEX pathway_node_source_index IF NOT EXISTS FOR (n:pathway) ON (n.node_source);

// node index range indexes
CREATE RANGE INDEX anatomy_node_index_index IF NOT EXISTS FOR (n:anatomy) ON (n.node_index);
CREATE RANGE INDEX biological_process_node_index_index IF NOT EXISTS FOR (n:biological_process) ON (n.node_index);
CREATE RANGE INDEX cellular_component_node_index_index IF NOT EXISTS FOR (n:cellular_component) ON (n.node_index);
CREATE RANGE INDEX disease_node_index_index IF NOT EXISTS FOR (n:disease) ON (n.node_index);   
CREATE RANGE INDEX drug_node_index_index IF NOT EXISTS FOR (n:drug) ON (n.node_index);
CREATE RANGE INDEX effect_phenotype_node_index_index IF NOT EXISTS FOR (n:effect_phenotype) ON (n.node_index);
CREATE RANGE INDEX exposure_node_index_index IF NOT EXISTS FOR (n:exposure) ON (n.node_index);
CREATE RANGE INDEX gene_protein_node_index_index IF NOT EXISTS FOR (n:gene_protein) ON (n.node_index);
CREATE RANGE INDEX molecular_function_node_index_index IF NOT EXISTS FOR (n:molecular_function) ON (n.node_index);
CREATE RANGE INDEX pathway_node_index_index IF NOT EXISTS FOR (n:pathway) ON (n.node_index);

// node id range indexes
CREATE RANGE INDEX anatomy_node_id_index IF NOT EXISTS FOR (n:anatomy) ON (n.node_id);
CREATE RANGE INDEX biological_process_node_id_index IF NOT EXISTS FOR (n:biological_process) ON (n.node_id);
CREATE RANGE INDEX cellular_component_node_id_index IF NOT EXISTS FOR (n:cellular_component) ON (n.node_id);
CREATE RANGE INDEX disease_node_id_index IF NOT EXISTS FOR (n:disease) ON (n.node_id);   
CREATE RANGE INDEX drug_node_id_index IF NOT EXISTS FOR (n:drug) ON (n.node_id);
CREATE RANGE INDEX effect_phenotype_node_id_index IF NOT EXISTS FOR (n:effect_phenotype) ON (n.node_id);
CREATE RANGE INDEX exposure_node_id_index IF NOT EXISTS FOR (n:exposure) ON (n.node_id);
CREATE RANGE INDEX gene_protein_node_id_index IF NOT EXISTS FOR (n:gene_protein) ON (n.node_id);
CREATE RANGE INDEX molecular_function_node_id_index IF NOT EXISTS FOR (n:molecular_function) ON (n.node_id);
CREATE RANGE INDEX pathway_node_id_index IF NOT EXISTS FOR (n:pathway) ON (n.node_id);

// node idx range indexes
CREATE RANGE INDEX anatomy_node_idx_index IF NOT EXISTS FOR (n:anatomy) ON (n.node_idx);
CREATE RANGE INDEX biological_process_node_idx_index IF NOT EXISTS FOR (n:biological_process) ON (n.node_idx);
CREATE RANGE INDEX cellular_component_node_idx_index IF NOT EXISTS FOR (n:cellular_component) ON (n.node_idx);
CREATE RANGE INDEX disease_node_idx_index IF NOT EXISTS FOR (n:disease) ON (n.node_idx);   
CREATE RANGE INDEX drug_node_idx_index IF NOT EXISTS FOR (n:drug) ON (n.node_idx);
CREATE RANGE INDEX effect_phenotype_node_idx_index IF NOT EXISTS FOR (n:effect_phenotype) ON (n.node_idx);
CREATE RANGE INDEX exposure_node_idx_index IF NOT EXISTS FOR (n:exposure) ON (n.node_idx);
CREATE RANGE INDEX gene_protein_node_idx_index IF NOT EXISTS FOR (n:gene_protein) ON (n.node_idx);
CREATE RANGE INDEX molecular_function_node_idx_index IF NOT EXISTS FOR (n:molecular_function) ON (n.node_idx);
CREATE RANGE INDEX pathway_node_idx_index IF NOT EXISTS FOR (n:pathway) ON (n.node_idx);

// pubmed indexes
CREATE RANGE INDEX pubmed_document_node_idx_index IF NOT EXISTS FOR (n:pubmed_document) ON (n.node_idx);
CREATE RANGE INDEX pubmed_document_pmcid_index IF NOT EXISTS FOR (n:pubmed_document) ON (n.pmcid);
CREATE RANGE INDEX pubmed_document_pmid_index IF NOT EXISTS FOR (n:pubmed_document) ON (n.pmid);
CREATE RANGE INDEX pubmed_document_is_pubmed_index IF NOT EXISTS FOR (n:pubmed_document) ON (n.is_pubmed);
CREATE RANGE INDEX pubmed_document_refresh_date_index IF NOT EXISTS FOR (n:pubmed_document) ON (n.refresh_date);
CREATE TEXT INDEX pubmed_document_title_index IF NOT EXISTS FOR (n:anatomy) ON (n.title);

// clinical trail indexes, check for indexes created by the constraints
CREATE RANGE INDEX clinical_trial_nct_number_index IF NOT EXISTS FOR (n:Clinical_Trial) ON (n.nct_number);

// embeddings indexes
CREATE VECTOR INDEX pubmed_document_model2vec_embeddings_index IF NOT EXISTS
    FOR (n:pubmed_document)
    ON n.model2vec_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};

CREATE VECTOR INDEX drug_model2vec_embeddings_index IF NOT EXISTS
    FOR (n:drug)
    ON n.model2vec_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};

CREATE VECTOR INDEX disease_model2vec_embeddings_index IF NOT EXISTS
    FOR (n:disease)
    ON n.model2vec_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};

CREATE VECTOR INDEX gene_protein_model2vec_embeddings_index IF NOT EXISTS
    FOR (n:gene_protein)
    ON n.model2vec_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};

CREATE VECTOR INDEX anatomy_model2vec_embeddings_index IF NOT EXISTS
    FOR (n:anatomy)
    ON n.model2vec_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};



// uspto indexes
CREATE RANGE INDEX uspto_application_application_number_text_index IF NOT EXISTS FOR (n:uspto_application) ON (n.application_number_text);
CREATE RANGE INDEX uspto_application_patent_number_index IF NOT EXISTS FOR (n:uspto_application) ON (n.patent_number);
CREATE RANGE INDEX uspto_application_file_create_dtg_index IF NOT EXISTS FOR (n:uspto_application) ON (n.file_create_dtg);
CREATE RANGE INDEX uspto_application_is_uspto_index IF NOT EXISTS FOR (n:uspto_application) ON (n.is_uspto);

CREATE RANGE INDEX uspto_pgpub_application_number_text_index IF NOT EXISTS FOR (n:uspto_pgpub) ON (n.application_number_text);
CREATE RANGE INDEX uspto_pgpub_is_uspto_index IF NOT EXISTS FOR (n:uspto_pgpub) ON (n.is_uspto);
CREATE TEXT INDEX uspto_pgpub_first_applicant_name_index IF NOT EXISTS FOR (n:uspto_pgpub) ON (n.first_applicant_name);
CREATE RANGE INDEX uspto_pgpub_filing_date_index IF NOT EXISTS FOR (n:uspto_pgpub) ON (n.filing_date);
CREATE VECTOR INDEX pgpub_embeddings_index IF NOT EXISTS
    FOR (n:uspto_pgpub)
    ON n.embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};


// csl tpp indexes
CREATE RANGE INDEX csl_tpp_node_id_index IF NOT EXISTS FOR (n:csl_tpp) ON (n.node_id);
CREATE RANGE INDEX csl_tpp_node_index_index IF NOT EXISTS FOR (n:csl_tpp) ON (n.node_index);
CREATE RANGE INDEX csl_tpp_is_csl_index IF NOT EXISTS FOR (n:csl_tpp) ON (n.is_csl);
CREATE RANGE INDEX csl_tpp_theraputic_area_index IF NOT EXISTS FOR (n:csl_tpp) ON (n.theraputic_area);

CREATE VECTOR INDEX csl_tpp_embeddings_index IF NOT EXISTS
    FOR (n:csl_tpp)
    ON n.embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};


CREATE RANGE INDEX csl_tpp_question_node_id_index IF NOT EXISTS FOR (n:csl_tpp_question) ON (n.node_id);
CREATE RANGE INDEX csl_tpp_question_node_index_index IF NOT EXISTS FOR (n:csl_tpp_question) ON (n.node_index);
CREATE RANGE INDEX csl_tpp_question_is_csl_index IF NOT EXISTS FOR (n:csl_tpp_question) ON (n.is_csl);

CREATE VECTOR INDEX csl_tpp_question_embeddings_index IF NOT EXISTS
    FOR (n:csl_tpp_question)
    ON n.embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 256,
        `vector.similarity_function`: 'cosine'
    }
};

// look for online status and not populating
SHOW VECTOR INDEXES;

// drug aliases indexes
CREATE RANGE INDEX drug_synonym_node_index_index IF NOT EXISTS FOR (n:drug_synonym) ON (n.node_index);
CREATE RANGE INDEX drug_product_node_index_index IF NOT EXISTS FOR (n:drug_product) ON (n.node_index);

SHOW INDEXES;