MATCH (n:pubmed_document)
SET n.node_idx = n.pmcid
RETURN n.pmcid;

MATCH (n:pubmed_document)
SET n.node_idx = toInteger(n.node_idx)
RETURN n.node_idx;


// missing anatomy node idx
MATCH (n)
WHERE ID(n) = 116782
return n


// one hot encoding
MATCH (n1:gene_protein)
WITH n1, gds.alpha.ml.oneHotEncoding(
[
  'gene_protein', 
  'anatomy',
  'disease',
  'effect_phenotype',
  'drug',
  'biological_process',
  'molecular_function',
  'cellular_component',
  'exposure',
  'pathway',
  'pubmed_document',
  'pubmed_summary',
  'pubmed_summary_finding',
  'clinical_trial',
  'condition',
  'collaborator',
  'funder_type',
  'intervention',
  'phase',
  'primary_outcome_measure',
  'secondary_outcome_measure',
  'sponsor'
], ['gene_protein']) AS encoding
CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
YIELD node
RETURN node;


MATCH (n1:anatomy)
WITH n1, gds.alpha.ml.oneHotEncoding(
[
  'gene_protein', 
  'anatomy',
  'disease',
  'effect_phenotype',
  'drug',
  'biological_process',
  'molecular_function',
  'cellular_component',
  'exposure',
  'pathway',
  'pubmed_document',
  'pubmed_summary',
  'pubmed_summary_finding',
  'clinical_trial',
  'condition',
  'collaborator',
  'funder_type',
  'intervention',
  'phase',
  'primary_outcome_measure',
  'secondary_outcome_measure',
  'sponsor'
], ['anatomy']) AS encoding
CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
YIELD node
RETURN node;

MATCH (n1:disease)
WITH n1, gds.alpha.ml.oneHotEncoding(
[
  'gene_protein', 
  'anatomy',
  'disease',
  'effect_phenotype',
  'drug',
  'biological_process',
  'molecular_function',
  'cellular_component',
  'exposure',
  'pathway',
  'pubmed_document',
  'pubmed_summary',
  'pubmed_summary_finding',
  'clinical_trial',
  'condition',
  'collaborator',
  'funder_type',
  'intervention',
  'phase',
  'primary_outcome_measure',
  'secondary_outcome_measure',
  'sponsor'
], ['disease']) AS encoding
CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
YIELD node
RETURN node;

MATCH (n1:drug)
WITH n1, gds.alpha.ml.oneHotEncoding(
[
  'gene_protein', 
  'anatomy',
  'disease',
  'effect_phenotype',
  'drug',
  'biological_process',
  'molecular_function',
  'cellular_component',
  'exposure',
  'pathway',
  'pubmed_document',
  'pubmed_summary',
  'pubmed_summary_finding',
  'clinical_trial',
  'condition',
  'collaborator',
  'funder_type',
  'intervention',
  'phase',
  'primary_outcome_measure',
  'secondary_outcome_measure',
  'sponsor'
], ['drug']) AS encoding
CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
YIELD node
RETURN node;

MATCH (n1:pubmed_document)
WITH n1, gds.alpha.ml.oneHotEncoding(
[
  'gene_protein', 
  'anatomy',
  'disease',
  'effect_phenotype',
  'drug',
  'biological_process',
  'molecular_function',
  'cellular_component',
  'exposure',
  'pathway',
  'pubmed_document',
  'pubmed_summary',
  'pubmed_summary_finding',
  'clinical_trial',
  'condition',
  'collaborator',
  'funder_type',
  'intervention',
  'phase',
  'primary_outcome_measure',
  'secondary_outcome_measure',
  'sponsor'
], ['pubmed_document']) AS encoding
CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
YIELD node
RETURN node;