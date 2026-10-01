// 
CALL gds.beta.pipeline.linkPrediction.train('pubmed_graph', {
  pipeline: 'pubmed-pipeline-1',
  modelName: 'pubmed-disease-model',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  sourceNodeLabel: 'pubmed_document',
  targetRelationshipType: 'has_extraction',
  targetNodeLabel: 'disease',
  randomSeed: 75
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores;

// 
CALL gds.beta.pipeline.linkPrediction.train('pubmed_graph', {
  pipeline: 'pubmed-pipeline-1',
  modelName: 'pubmed-drug-model',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  sourceNodeLabel: 'pubmed_document',
  targetRelationshipType: 'has_extraction',
  targetNodeLabel: 'drug',
  randomSeed: 75
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores;
