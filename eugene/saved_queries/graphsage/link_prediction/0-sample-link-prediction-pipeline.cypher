CALL gds.beta.pipeline.linkPrediction.create('pipe1')


CALL gds.beta.pipeline.linkPrediction.addNodeProperty('pipe1', 'fastRP', {
  mutateProperty: 'embedding',
  embeddingDimension: 256,
  randomSeed: 42
})


CALL gds.beta.pipeline.linkPrediction.addFeature('pipe1', 'hadamard', {
  nodeProperties: ['embedding']
}) YIELD featureSteps

CALL gds.beta.pipeline.linkPrediction.configureSplit('pipe1', {
  testFraction: 0.25,
  trainFraction: 0.6,
  validationFolds: 3
})
YIELD splitConfig


CALL gds.beta.pipeline.linkPrediction.addRandomForest('pipe1', {
    numberOfDecisionTrees: 10
})
YIELD parameterSpace

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/
// THIS SHOULD WORK but did not, 
// errors with? undirectedRelationshipTypes 
// MATCH (source:Person)-[r:KNOWS]->(target:Person)
// RETURN gds.graph.project(
//   'myGraph',
//   source,
//   target,
//   {
//     sourceNodeProperties: source { .age },
//     targetNodeProperties: target { .age },
//     relationshipType: 'KNOWS'
//   },
//   { undirectedRelationshipTypes: ['KNOWS'] }
// )

// project undirected graph
CALL gds.graph.project(
'graph1',
['disease', 'gene_protein'],
{
    disease_protein: {orientation: 'UNDIRECTED', type:'*'}
})
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels

CALL gds.beta.pipeline.linkPrediction.train.estimate('graph1', {
  pipeline: 'pipe1',
  modelName: 'lp-pipeline-model',
  targetRelationshipType: 'disease_protein'
})
YIELD requiredMemory

call gds.graph.drop('graph1')

CALL gds.beta.pipeline.linkPrediction.train('graph1', {
  pipeline: 'pipe1',
  modelName: 'lp-pipeline-model',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  targetRelationshipType: 'disease_protein',
  randomSeed: 18
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores


CALL gds.beta.pipeline.linkPrediction.predict.stream.estimate('graph1', {
  modelName: 'lp-pipeline-model',
  topN: 5,
  threshold: 0.5
})
YIELD requiredMemory


CALL gds.beta.pipeline.linkPrediction.predict.stream('graph1', {
  modelName: 'lp-pipeline-model',
  topN: 5,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN gds.util.asNode(node1).node_name AS disease1, gds.util.asNode(node2).node_name AS disease2, probability
 ORDER BY probability DESC, disease1, disease2

 completed in 3815921 ms.

╒════════╤═════════╤═══════════╕
│disease1│disease2 │probability│
╞════════╪═════════╪═══════════╡
│"RYR1"  │"DOCK6"  │1.0        │
├────────┼─────────┼───────────┤
│"RYR1"  │"PACSIN2"│1.0        │
├────────┼─────────┼───────────┤
│"RYR1"  │"SESN3"  │1.0        │
├────────┼─────────┼───────────┤
│"RYR1"  │"TRPA1"  │1.0        │
├────────┼─────────┼───────────┤
│"RYR1"  │"UFSP2"  │1.0        │
└────────┴─────────┴───────────┘

MATCH (d1:disease|gene_protein)
WHERE d1.node_name =~ '(?i).*RYR1.*' 
    or d1.node_name =~ '(?i).*DOCK6.*' 
    or d1.node_name =~ '(?i).*PACSIN2.*'
RETURN d1











--- DID NOT WORK --- 


// CALL gds.beta.graphSage.train(
//     'graph1',
//     {
//         modelName: 'pipe1-model',
//         featureProperties: ['embedding'],
//         nodeLabels: ['disease', 'gene_protein'],
//         relationshipTypes: ['disease_protein']
//     }
// )
// YIELD trainMillis
// RETURN trainMillis

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/
// MATCH (source:Person)-[r:KNOWS]->(target:Person)
// RETURN gds.graph.project(
//   'myGraph',
//   source,
//   target,
//   {
//     sourceNodeProperties: source { .age },
//     targetNodeProperties: target { .age },
//     relationshipType: 'KNOWS'
//   },
//   { undirectedRelationshipTypes: ['KNOWS'] }
// )

    // { 
    //     relationshipProperties: r { .embedding },
    //     undirectedRelationshipTypes: ['*']
    // }
MATCH (source) OPTIONAL MATCH (source:disease)-[r:disease_protein]-(target:gene_protein)
CALL gds.graph.project(
    'diseaseToProteinNoPropertiesGraph',
    source,
    target,
    {},
    {undirectedRelationshipTypes: ['*']}
)
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels