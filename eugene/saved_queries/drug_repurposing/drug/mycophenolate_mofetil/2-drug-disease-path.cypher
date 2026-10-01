// https://go.drugbank.com/drugs/DB00688
// match path for mycophenolate mofetil
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14964' and dse.node_index = '33577'
RETURN p


// match path for mycophenolate mofetil
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14964' and dse.node_index = '36229'
RETURN p



MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14964' and 
(dse.node_index = '33577' or dse.node_index = '36229' or dse.node_index = '36104')
RETURN p

