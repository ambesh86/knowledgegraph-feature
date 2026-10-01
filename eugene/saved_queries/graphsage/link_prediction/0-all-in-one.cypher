// NOTE the prediction using graphsage in the link prediction pipeline fails
// traing and embedding creation w/ graphsage appears to work, prediction does not

// OPTIONAL - CLEAN UP PREVIOUS RUNS
// drop model
call gds.model.drop('graphsage-model-xlg')
    YIELD modelName, modelType, modelInfo, loaded, stored, published;

// drop pipeline
call gds.pipeline.drop('graphsage-pipeline-xlg');

// drop graph
call gds.graph.drop('genes_drugs_diseases');



// PROJECT GRAPH
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




// TRAIN
// graph sage
CALL gds.degree.mutate(
  'genes_drugs_diseases',
  {
    mutateProperty: 'degree'
  }
) YIELD nodePropertiesWritten;


CALL gds.beta.graphSage.train(
  'genes_drugs_diseases',
  {
    modelName: 'graphsage-model-xlg',
    featureProperties: ['degree'],
    embeddingDimension: 256,
    epochs: 4,
    randomSeed: 85
  }
)
YIELD trainMillis
RETURN trainMillis;


CALL gds.beta.graphSage.mutate(
  'genes_drugs_diseases',
  {
    mutateProperty: 'graphsage-embedding',
    modelName: 'graphsage-model-xlg'
  }
) YIELD
  nodeCount,
  nodePropertiesWritten;

// VERIFY embeddings exist for nodes in the graph
CALL gds.beta.graphSage.stream(
  'genes_drugs_diseases',
  {
    modelName: 'graphsage-model-xlg'
  }
)
YIELD nodeId, embedding
RETURN gds.util.asNode(nodeId).node_name AS name, embedding
ORDER BY name, embedding


CALL gds.graph.nodeProperty.stream('genes_drugs_diseases', 'graphsage-embedding', ['drug', 'disease', 'gene_protein'])
YIELD nodeId, propertyValue
RETURN gds.util.asNode(nodeId).node_name AS name, propertyValue AS embedding
ORDER BY name ASC;


// CREATE PIPELINE AND TRAIN
//  https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/
// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('graphsage-pipeline-xlg');



// define embedding as a feature, can add other node properties
// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addNodeProperty('graphsage-pipeline-xlg', 'beta.graphSage', {
  modelName: 'graphsage-model-xlg',
  mutateProperty: 'graphsage-embedding'
})


CALL gds.beta.pipeline.linkPrediction.addFeature('graphsage-pipeline-xlg', 'hadamard', {
  nodeProperties: ['graphsage-embedding']
}) YIELD featureSteps;


// configure test, training, validation data splits 
// CALL gds.beta.pipeline.linkPrediction.configureSplit('graphsage-pipeline-xlg', {
//   testFraction: 0.25,
//   trainFraction: 0.6,
//   validationFolds: 3
// })
// YIELD splitConfig;


// define model type, each model will be tried in the autotuning step
// CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('graphsage-pipeline-xlg')
// YIELD parameterSpace;

// CALL gds.alpha.pipeline.linkPrediction.addMLP('graphsage-pipeline-xlg',
// {hiddenLayerSizes: [4, 2], penalty: 0.5, patience: 2, classWeights: [0.55, 0.45], focusWeight: {range: [0.0, 0.1]}})
// YIELD parameterSpace;

// PREDICT - fails
// predict
// Failed to invoke procedure `gds.beta.pipeline.linkPrediction.predict.stream`: Caused by: java.lang.IllegalArgumentException: The model `graphsage-model-xlg` has data with different types than expected.
//  Expected data type: `org.neo4j.gds.embeddings.graphsage.ImmutableModelData`, invoked with model data type: `org.neo4j.gds.ml.models.Classifier$ClassifierData
CALL gds.beta.pipeline.linkPrediction.predict.stream('genes_drugs_diseases', {
  modelName: 'graphsage-model-xlg',
  topN: 10,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN gds.util.asNode(node1).node_name AS node1, gds.util.asNode(node2).node_name AS node2, probability
 ORDER BY probability DESC, node1, node2;

  