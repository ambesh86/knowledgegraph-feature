// [5] verify - VWF a related disease
MATCH (n:disease)-[r]-(p:gene_protein)
WHERE n.node_id = '8668_13304_10191_15628_15629_15630_15631' or n.node_id = '2907_2692'
RETURN n, r, p