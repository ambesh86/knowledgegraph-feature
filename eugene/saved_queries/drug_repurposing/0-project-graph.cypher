CALL gds.graph.project(
'genes_drugs_diseases',
['disease', 'drug', 'gene_protein'],
{
    disease_protein: {orientation: 'UNDIRECTED', type:'*'},
    drug_protein: {orientation: 'UNDIRECTED', type:'*'}
})
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels;
