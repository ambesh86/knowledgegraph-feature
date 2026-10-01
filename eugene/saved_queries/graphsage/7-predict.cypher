// [7] predict
CALL gds.beta.pipeline.linkPrediction.predict.stream('diseaseToProteinNoPropertiesGraph', {
modelName: 'nodeDegreeOnlyGraphSageModel',
topN: 5,
threshold: 0.5
})
YIELD node1, node2, probability
RETURN gds.util.asNode(node1).node_name AS node1, gds.util.asNode(node2).node_name AS node2, probability
ORDER BY probability DESC, node1, node2

// The above FAILS with a model error
// Failed to invoke procedure `gds.beta.pipeline.linkPrediction.predict.stream`: 
// Caused by: java.lang.IllegalArgumentException: 
// The model `nodeDegreeOnlyGraphSageModel` has data with different types than expected. 
// Expected data type: `org.neo4j.gds.embeddings.graphsage.ImmutableModelData`, 
// invoked with model data type: `org.neo4j.gds.ml.models.Classifier$ClassifierData`.


CALL gds.beta.pipeline.nodeClassification.predict.stream('diseaseToProteinNoPropertiesGraph', {
  modelName: 'nodeDegreeOnlyGraphSageModel',
  includePredictedProbabilities: true,
  targetNodeLabels: ['embedding']
})
 YIELD nodeId, predictedClass, predictedProbabilities
WITH gds.util.asNode(nodeId) AS diseaseNode, predictedClass, predictedProbabilities
RETURN
  diseaseNode.node_name AS name,
  predictedClass,
  floor(predictedProbabilities[predictedClass] * 100) AS confidence
  ORDER BY name
//   Failed to invoke procedure `gds.beta.pipeline.nodeClassification.predict.stream`: 
//   Caused by: java.lang.IllegalArgumentException: 
//   The model `nodeDegreeOnlyGraphSageModel` has data with different types than expected. 
//   Expected data type: `org.neo4j.gds.embeddings.graphsage.ImmutableModelData`, 
//   invoked with model data type: `org.neo4j.gds.ml.models.BaseModelData`