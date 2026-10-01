
// ingest clincial trial nodes
LOAD CSV WITH HEADERS FROM 'file:///clinicaltrial_nodes_v1_fixed.csv' AS row
CALL (row) {
                                       MERGE (n:$(row.`node_label:LABEL`) {
                                           node_index: row.`node_index:ID`
                                        })
                                        set n.node_id = row.node_id,
                                            n.node_label = row.`node_label:LABEL`,
                                            n.node_name = row.node_name,
                                            n.node_source = row.node_source,
                                            n.MONDO_ID = row.MONDO_ID,
                                            n.MONDO_NAME = row.MONDO_NAME,
					                        n.for_clinical_trial = row.for_clinical_trial
} IN TRANSACTIONS OF 2000 ROWS;

LOAD CSV WITH HEADERS FROM 'file:///clinicaltrial_edges_v1.csv' AS row
                 MATCH (start_node {`node_index`: row.`:START_ID`}), (end_node {`node_index`: row.`:END_ID`})
                 CREATE (start_node)-[r:$(row.`:TYPE`)]->(end_node)
                 SET r.display_relation = row.display_relation;