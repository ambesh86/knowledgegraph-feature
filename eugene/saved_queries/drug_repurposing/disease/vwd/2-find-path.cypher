// match path for vwd and similar drug
MATCH p=(n1:disease)-[r1]-(p1:gene_protein)-[r2]-(n2 {node_index: '18381'})
WHERE n1.node_index = '29845' or  n1.node_index = '39535'
RETURN p