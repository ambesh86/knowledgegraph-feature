// 
CALL gds.beta.pipeline.linkPrediction.train('eugene_foundational_graph', {
  pipeline: 'pgpub_pipeline_1',
  modelName: 'tpp_pgpub_model',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  sourceNodeLabel: 'csl_tpp',
  targetRelationshipType: 'has_publication',
  targetNodeLabel: 'uspto_pgpub',
  randomSeed: 75
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores;


// Failed to invoke procedure `gds.beta.pipeline.linkPrediction.train`: Caused by: java.lang.IllegalArgumentException: 
//   The specified `testFraction` is too low for the current graph. The test set would have 0 relationship(s) but it must have at least 1.