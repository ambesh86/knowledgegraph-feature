// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/graph-sage/
// [1] project diseaseToProteinNoPropertiesGraph
CALL gds.graph.project(
'diseaseToProteinNoPropertiesGraph',
['disease', 'gene_protein'],
['disease_protein'],
{}
)
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection.Book AS bookProjection, nodes, rels
