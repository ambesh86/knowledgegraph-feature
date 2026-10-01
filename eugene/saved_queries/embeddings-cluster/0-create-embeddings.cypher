// populate fastrp embeddings
CALL gds.fastRP.mutate(
  'genes_drugs_diseases',
  {
    embeddingDimension: 64,
    mutateProperty: 'fastrp-embedding-64',
    iterationWeights: [0.0, 0.0, 1.0],
    normalizationStrength: -0.5,
    randomSeed: 75
  }
)
YIELD nodePropertiesWritten;


CALL gds.fastRP.mutate(
  'genes_drugs_diseases',
  {
    embeddingDimension: 128,
    mutateProperty: 'fastrp-embedding-128',
    iterationWeights: [0.0, 0.0, 1.0],
    normalizationStrength: -0.5,
    randomSeed: 75
  }
)
YIELD nodePropertiesWritten;



CALL gds.beta.graphSage.mutate(
  'genes_drugs_diseases',
  {
    mutateProperty: 'graphsage-embedding-256',
    modelName: 'graphsage-model-lg'
  }
) YIELD
  nodeCount,
  nodePropertiesWritten;


// populate graphsage embeddings
CALL gds.beta.graphSage.train(
  'genes_drugs_diseases',
  {
    modelName: 'graphsage-model-sm',
    featureProperties: ['degree'],
    embeddingDimension: 64,
    epochs: 4,
    randomSeed: 85
  }
)
YIELD trainMillis
RETURN trainMillis;

CALL gds.beta.graphSage.mutate(
  'genes_drugs_diseases',
  {
    mutateProperty: 'graphsage-embedding-64',
    modelName: 'graphsage-model-sm'
  }
) YIELD
  nodeCount,
  nodePropertiesWritten;