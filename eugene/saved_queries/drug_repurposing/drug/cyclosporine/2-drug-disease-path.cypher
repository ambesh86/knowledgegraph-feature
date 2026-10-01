
// match path for cyclophosphamide
// https://go.drugbank.com/drugs/DB00531 - drug for lymphomas, lukemia
// https://www.ncbi.nlm.nih.gov/gene/1577
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14934' and dse.node_index = '33577'
RETURN p


// match path for cyclophosphamide
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14934' and dse.node_index = '36035'
RETURN p


// match path for cyclophosphamide
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14934' and dse.node_index = '35641'
RETURN p


// match path for cyclophosphamide
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14934' and 
(dse.node_index = '35641' or dse.node_index = '33577' or dse.node_index = '36035' or dse.node_index = '36229')
RETURN p