// https://go.drugbank.com/drugs/DB00563
// https://www.ncbi.nlm.nih.gov/gene/213
// match path for tacrolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14251' and dse.node_index = '35764'
RETURN p


// match path for tacrolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14251' and dse.node_index = '33577'
RETURN p




// https://go.drugbank.com/drugs/DB00563
// https://www.ncbi.nlm.nih.gov/gene/213 - ALB
// https://www.ncbi.nlm.nih.gov/gene/1577 - CYP3A5
// match path for tacrolimus
MATCH p=(drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '14251' and 
(dse.node_index = '35764' or dse.node_index = '33577')
RETURN p