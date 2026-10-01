//  https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/

// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('fastrp-pipeline-sm');

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/#linkprediction-pipeline-examples-train-filtering
// used addNodeProperty when you want to execute a graph algorithm to calculate the new property
// add embedding as a node property, fast rp will use degree topology
// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/#linkprediction-adding-node-properties
// VERIFY embeddings exist AFTER pipeline prediction
// the node property steps that are added to the pipeline will be executed both when training a pipeline and when the trained model is applied for prediction.
// can run this outside the pipeline
// CALL gds.beta.pipeline.linkPrediction.addNodeProperty('fastrp-pipeline-sm', 'fastRP', {
//   mutateProperty: 'embedding',
//   embeddingDimension: 64,
//   randomSeed: 75
// });

// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addFeature('fastrp-pipeline-sm', 'hadamard', {
  nodeProperties: ['embedding256']
}) YIELD featureSteps;


// configure test, training, validation data splits 
CALL gds.beta.pipeline.linkPrediction.configureSplit('fastrp-pipeline-sm', {
  testFraction: 0.25,
  trainFraction: 0.6,
  validationFolds: 3
})
YIELD splitConfig;


// define model type, each model will be tried in the autotuning step
CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('fastrp-pipeline-sm')
YIELD parameterSpace;

// note the alpha namespace
CALL gds.alpha.pipeline.linkPrediction.addMLP('fastrp-pipeline-sm',
{hiddenLayerSizes: [4, 2], penalty: 0.5, patience: 2, classWeights: [0.55, 0.45], focusWeight: {range: [0.0, 0.1]}})
YIELD parameterSpace;

CALL gds.beta.pipeline.linkPrediction.addRandomForest('fastrp-pipeline-sm', {numberOfDecisionTrees: 10 })
YIELD parameterSpace;




// configure model training autotuning parameters
CALL gds.alpha.pipeline.linkPrediction.configureAutoTuning('fastrp-pipeline-sm', {
  maxTrials: 2
}) YIELD autoTuningConfig;




// MATCH (source) OPTIONAL MATCH (source:disease)-[r:disease_protein]-(target:gene_protein)
// CALL gds.graph.project(
//     'diseaseToProteinUndirected',
//     source,
//     target,
//     {
//         undirectedRelationshipTypes: ['*']
//     }
// )

// CALL gds.graph.project('proj',
//     ['Person','Movie'],
//     {
//         ACTED_IN:{orientation:'UNDIRECTED'},
//         DIRECTED:{orientation:'UNDIRECTED'}
//     }
// );

// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/graph-sage/#_train_when_there_are_no_node_properties_present_in_the_graph
// https://neo4j.com/docs/graph-data-science/current/management-ops/graph-creation/graph-project/
CALL gds.graph.project(
'diseaseToProteinUndirected',
['disease', 'gene_protein'],
{
    disease_protein: {orientation: 'UNDIRECTED', type:'*'}
})
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels


// https://neo4j.com/docs/graph-data-science/current/management-ops/graph-reads/graph-stream-nodes/
// view properties
CALL gds.graph.nodeProperty.stream('diseaseToProteinUndirected', 'embedding', ['disease', 'gene_protein'])
YIELD nodeId, propertyValue
RETURN gds.util.asNode(nodeId).name AS name, propertyValue AS embedding
ORDER BY score ASC

// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('fastrp-pipeline-1');

// add embedding as a node property, fast rp will use degree topology
CALL gds.beta.pipeline.linkPrediction.addNodeProperty('fastrp-pipeline-1', 'fastRP', {
  mutateProperty: 'dmk-embedding-1',
  embeddingDimension: 256,
  randomSeed: 75
});

// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addFeature('fastrp-pipeline-1', 'hadamard', {
  nodeProperties: ['dmk-embedding-1']
}) YIELD featureSteps;


// configure test, training, validation data splits 
CALL gds.beta.pipeline.linkPrediction.configureSplit('fastrp-pipeline-lg', {
  testFraction: 0.25,
  trainFraction: 0.6,
  validationFolds: 3
})
YIELD splitConfig;


// define model type, each model will be tried in the autotuning step
CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('fastrp-pipeline-1')
YIELD parameterSpace;

CALL gds.beta.pipeline.linkPrediction.addRandomForest('fastrp-pipeline-1', {numberOfDecisionTrees: 10 })
YIELD parameterSpace;

// note the alpha namespace
CALL gds.alpha.pipeline.linkPrediction.addMLP('fastrp-pipeline-1',
{hiddenLayerSizes: [4, 2], penalty: 0.5, patience: 2, classWeights: [0.55, 0.45], focusWeight: {range: [0.0, 0.1]}})
YIELD parameterSpace;


// cofigure model training autotuning parameters
CALL gds.alpha.pipeline.linkPrediction.configureAutoTuning('fastrp-pipeline-1', {
  maxTrials: 4
}) YIELD autoTuningConfig;