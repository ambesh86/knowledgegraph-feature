// [4] verify - high similarity score low cardinality
MATCH (n:disease)-[r]-(p:gene_protein)
WHERE n.node_id = '14822' or n.node_id = '10970'
RETURN n, r, p
