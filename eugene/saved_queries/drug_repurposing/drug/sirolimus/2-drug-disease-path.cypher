// https://go.drugbank.com/drugs/DB00877
// match path for sirolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '15012' and dse.node_index = '36229'
RETURN p

// https://go.drugbank.com/drugs/DB00877
// match path for sirolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '15012' and dse.node_index = '36104'
RETURN p


// https://go.drugbank.com/drugs/DB00563
// https://www.ncbi.nlm.nih.gov/gene/213
// match path for sirolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '15012' and 
(dse.node_index = '36229' or dse.node_index = '36104' or dse.node_index = '33577')
RETURN p