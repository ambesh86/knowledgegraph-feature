// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('pubmed-pipeline-1');

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/#linkprediction-pipeline-examples-train-filtering
// used addNodeProperty when you want to execute a graph algorithm to calculate the new property
// add embedding as a node property, fast rp will use degree topology
// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/#linkprediction-adding-node-properties
// VERIFY embeddings exist AFTER pipeline prediction
// the node property steps that are added to the pipeline will be executed both when training a pipeline and when the trained model is applied for prediction.
// can run this outside the pipeline
// CALL gds.beta.pipeline.linkPrediction.addNodeProperty('pubmed-pipeline-1', 'fastRP', {
//   mutateProperty: 'pubmed-embedding-1',
//   embeddingDimension: 256,
//   randomSeed: 75
// });

// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addFeature('pubmed-pipeline-1', 'hadamard', {
    nodeProperties: [
        'fastrp-embedding',
        'model2vec_embeddings',
        'label_one_hot_encoding',
        'node_idx'
    ]
}) YIELD featureSteps;


// configure test, training, validation data splits 
CALL gds.beta.pipeline.linkPrediction.configureSplit('pubmed-pipeline-1', {
  testFraction: 0.17,
  trainFraction: 0.58,
  validationFolds: 3
})
YIELD splitConfig;

// define model type, each model will be tried in the autotuning step
CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('pubmed-pipeline-1')
YIELD parameterSpace;

CALL gds.beta.pipeline.linkPrediction.addRandomForest('pubmed-pipeline-1', {numberOfDecisionTrees: 8 })
YIELD parameterSpace;

// note the alpha namespace
CALL gds.alpha.pipeline.linkPrediction.addMLP('pubmed-pipeline-1',
{hiddenLayerSizes: [4, 2], penalty: 0.5, patience: 2, classWeights: [0.55, 0.45], focusWeight: {range: [0.0, 0.1]}})
YIELD parameterSpace;
