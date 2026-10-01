// match path for lupus and ae-941
MATCH p=(n1 {node_index: '94775'})-[r1]-(p1:gene_protein)-[r2]-(n2 {node_index: '16198'})
RETURN p