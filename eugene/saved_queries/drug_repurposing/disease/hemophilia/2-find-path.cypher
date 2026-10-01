// match path for hemophilia and similar drug
MATCH p=(dse:disease)-[r1]-(p1:gene_protein)-[r2]-(drg:drug)
WHERE dse.node_index = '32220' and drg.node_index = '15978'
RETURN p

// match path for hemophilia and similar drug
MATCH p=(dse:disease)-[r1]-(p1:gene_protein)-[r2]-(drg:drug)
WHERE (dse.node_index = '32220' and drg.node_index = '15902')
RETURN p

