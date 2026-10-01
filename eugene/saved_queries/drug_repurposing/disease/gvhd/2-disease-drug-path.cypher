// match path for gvh and similar drug
MATCH p=(dse:disease)-[r1]-(p1:gene_protein)-[r2]-(drg:drug)
WHERE (dse.node_index = '32520' or drg.node_index = '19383')
RETURN p


// match path for gvh and similar drug
MATCH p=(dse:disease)-[r1]-(p1:gene_protein)-[r2]-(drg:drug)
WHERE (dse.node_index = '32520' or drg.node_index = '18158')
RETURN p


