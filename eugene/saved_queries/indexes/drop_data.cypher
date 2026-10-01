// drop relationships in batches of 100k
MATCH ()-[r]->() CALL(r) { DELETE r } IN TRANSACTIONS OF 100000 ROWS;
// drop nodes in batches of 100k
MATCH (n) CALL(n) { DETACH DELETE n } IN TRANSACTIONS OF 100000 ROWS;


show constraints
yield name
return name;

drop constraint `drug_id` if exists;
drop constraint `nct_id_ClinicalTrial_uniq` if exists;
drop constraint `org_id_Organization_uniq` if exists;
drop constraint `organization_id_Organization_uniq` if exists;
drop constraint `patent_id_Patent_Application_uniq` if exists;
drop constraint `pmid_Research_uniq` if exists;


show indexes
yield name
return name;

drop index `drug_id` if exists;
drop index `drug_product_node_index_index` if exists;
drop index `drug_synonym_node_index_index` if exists;
drop index `index_343aff4e` if exists;
drop index `index_f7700477` if exists;