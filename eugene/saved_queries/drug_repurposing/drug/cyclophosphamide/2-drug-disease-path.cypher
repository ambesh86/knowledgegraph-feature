// match path for cyclophosphamide
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14954' and dse.node_index = '33577'
RETURN p
