// [5] verify - mid similarity score
MATCH (n:disease)-[r]-(p:gene_protein)
WHERE n.node_id = '8853' or n.node_id = '9276' or n.node_id = '1197'
RETURN n, r, p
