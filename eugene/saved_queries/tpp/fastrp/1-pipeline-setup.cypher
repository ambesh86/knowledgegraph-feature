// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('pgpub_pipeline_1');

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/#linkprediction-pipeline-examples-train-filtering
// used addNodeProperty when you want to execute a graph algorithm to calculate the new property
// add embedding as a node property, fast rp will use degree topology
// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/#linkprediction-adding-node-properties
// VERIFY embeddings exist AFTER pipeline prediction
// the node property steps that are added to the pipeline will be executed both when training a pipeline and when the trained model is applied for prediction.
// can run this outside the pipeline

// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addFeature('pgpub_pipeline_1', 'hadamard', {
    nodeProperties: [
        'prediction_embeddings',
        'embeddings',
        'label_one_hot_encoding'
        // 'node_idx'
    ]
}) YIELD featureSteps;


// configure test, training, validation data splits 
CALL gds.beta.pipeline.linkPrediction.configureSplit('pgpub_pipeline_1', {
  testFraction: 0.17,
  trainFraction: 0.58,
  validationFolds: 3
})
YIELD splitConfig;

// define model type, each model will be tried in the autotuning step
CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('pgpub_pipeline_1')
YIELD parameterSpace;

CALL gds.beta.pipeline.linkPrediction.addRandomForest('pgpub_pipeline_1', {numberOfDecisionTrees: 8 })
YIELD parameterSpace;

// note the alpha namespace
CALL gds.alpha.pipeline.linkPrediction.addMLP('pgpub_pipeline_1',
{hiddenLayerSizes: [4, 2], penalty: 0.5, patience: 2, classWeights: [0.55, 0.45], focusWeight: {range: [0.0, 0.1]}})
YIELD parameterSpace;
