// if the project in memory graph does not exist, then project it
// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/graph-sage/#_train_when_there_are_no_node_properties_present_in_the_graph
// https://neo4j.com/docs/graph-data-science/current/management-ops/graph-creation/graph-project/
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

// https://neo4j.com/docs/graph-data-science/current/management-ops/graph-reads/graph-stream-nodes/
// VERIFY no embeddings exist for nodes in the graph
// view any properties, THIS STEP SHOULD FAIL as we are verifing no embeddings exist
CALL gds.graph.nodeProperty.stream('genes_drugs_diseases', 'embedding', ['disease', 'drugs', 'gene_protein'])
YIELD nodeId, propertyValue
RETURN gds.util.asNode(nodeId).node_name AS name, propertyValue AS embedding
ORDER BY name ASC;

// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/#algorithms-embeddings-fastrp-examples-stats
CALL gds.fastRP.stats('genes_drugs_diseases', { embeddingDimension: 256 })
YIELD *;

// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/#algorithms-embeddings-fastrp-examples-mutate
// https://youtu.be/HNE-Ctl52hw?t=220
// parameters suggested by video
// iterationWeights: [0.0, 0.0, 1.0] are from the whitepaper, probabilities during the random walk
// normalizationStrength: remove influence of high degree nodes
// the pipeline will run this, or you can generate embeddings outside the pipeline
CALL gds.fastRP.mutate(
  'genes_drugs_diseases',
  {
    embeddingDimension: 256,
    mutateProperty: 'embedding256',
    iterationWeights: [0.0, 0.0, 1.0],
    normalizationStrength: -0.5,
    randomSeed: 75
  }
)
YIELD nodePropertiesWritten;


// VERIFY embeddings exist after fastrp
CALL gds.graph.nodeProperty.stream('genes_drugs_diseases', 'embedding256', ['disease', 'drugs', 'gene_protein'])
YIELD nodeId, propertyValue
RETURN gds.util.asNode(nodeId).node_name AS name, propertyValue AS embedding
ORDER BY name ASC;