// [6] estimate - THIS FAILS
CALL gds.beta.pipeline.linkPrediction.predict.stream.estimate('diseaseToProteinNoPropertiesGraph', 
    {
        modelName: 'nodeDegreeOnlyGraphSageModel',
        topN: 5,
        threshold: 0.5
})
YIELD requiredMemory

// Failed to invoke procedure `gds.beta.pipeline.linkPrediction.predict.stream.estimate`: 
// Caused by: java.lang.IllegalArgumentException: 
// The model `nodeDegreeOnlyGraphSageModel` has data with different types than expected. 
// Expected data type: `org.neo4j.gds.embeddings.graphsage.ImmutableModelData`, 
// invoked with model data type: `org.neo4j.gds.ml.models.Classifier$ClassifierData`.