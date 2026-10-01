// https://go.drugbank.com/drugs/DB00563
// https://www.ncbi.nlm.nih.gov/gene/213
// match path for methotrexate
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14194' and dse.node_index = '35764'
RETURN p


// match path for methotrexate
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14194' and dse.node_index = '36229'
RETURN p


MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14194' and 
(dse.node_index = '35764' or dse.node_index = '36229' or dse.node_index = '33623' or dse.node_index = '33632')
RETURN p


