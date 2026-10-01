// [5] verify - blood platelet related diseases
// these node ids are retuned in the filter node similarity step
// this is a reduced set
MATCH (n:disease)-[r]-(p:gene_protein)
WHERE n.node_id = '24574' or
n.node_id = '7930' or
n.node_id = '8332' or
n.node_id = '9276' or 
n.node_id = '1197'
RETURN n, r, p