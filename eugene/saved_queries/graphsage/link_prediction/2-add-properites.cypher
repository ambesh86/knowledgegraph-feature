CALL gds.beta.pipeline.linkPrediction.addNodeProperty('graphsage-pipeline', 'gds.beta.graphSage', 
  {
    mutateProperty: 'embedding',
    embeddingDimension: 64,
    randomSeed: 42
  }
)


CALL gds.beta.pipeline.linkPrediction.addNodeProperty('pipe', 'fastRP', 
  {
    mutateProperty: 'embedding',
    embeddingDimension: 256,
    randomSeed: 42
  }
)
