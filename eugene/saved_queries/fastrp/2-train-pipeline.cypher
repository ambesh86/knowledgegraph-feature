// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/training/

// estimate memory to train
CALL gds.beta.pipeline.linkPrediction.train.estimate('genes_drugs_diseases', {
  pipeline: 'fastrp-pipeline-sm',
  modelName: 'fastrp-model-sm',
  targetRelationshipType: 'disease_protein'
})
YIELD requiredMemory;

// train 
CALL gds.beta.pipeline.linkPrediction.train('genes_drugs_diseases', {
  pipeline: 'fastrp-pipeline-sm',
  modelName: 'fastrp-model-sm',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  targetRelationshipType: 'disease_protein',
  randomSeed: 75
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores;

// Started streaming 1 records in less than 1 ms and completed after 3989 ms.
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════╤══════════════════╤══════════════════╤════════════════════╕
// │winningModel                                                          │avgTrainScore     │outerTrainScore   │testScore         │validationScores    │
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════╪══════════════════╪══════════════════╪════════════════════╡
// │{minEpochs: 1, maxEpochs: 100, focusWeight: 0.0, patience: 1, toleranc│0.8120473402099716│0.8120473147165658│0.8115200238840464│[0.8120474762279075]│
// │e: 0.001, learningRate: 0.001, batchSize: 100, penalty: 0.0, methodNam│                  │                  │                  │                    │
// │e: "LogisticRegression", classWeights: []}                            │                  │                  │                  │                    │
// └──────────────────────────────────────────────────────────────────────┴──────────────────┴──────────────────┴──────────────────┴────────────────────┘

// 128 dim size - 13 mins
// Started streaming 1 records after 14 ms and completed after 835591 ms.
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════╤══════════════════╤══════════════════╤══════════════════════════════════════════════════════════════════════╕
// │winningModel                                                          │avgTrainScore     │outerTrainScore   │testScore         │validationScores                                                      │
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════╪══════════════════╪══════════════════╪══════════════════════════════════════════════════════════════════════╡
// │{minEpochs: 1, maxEpochs: 100, focusWeight: 0.0, patience: 1, toleranc│0.8907768656189964│0.8907763336180688│0.8913667794520187│[0.890778452984545, 0.8712252150856198, 0.6912015667163988, 0.69119887│
// │e: 0.001, learningRate: 0.001, batchSize: 100, penalty: 0.0, methodNam│                  │                  │                  │53345734]                                                             │
// │e: "LogisticRegression", classWeights: []}                            │                  │                  │                  │                                                                      │
// └──────────────────────────────────────────────────────────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────────────────────────────────────────────────────────┘

// 64 dim size:  - 6 mins
// Started streaming 1 records in less than 1 ms and completed after 375496 ms.
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════╤══════════════════╤══════════════════╤══════════════════════════════════════════════════════════════════════╕
// │winningModel                                                          │avgTrainScore     │outerTrainScore   │testScore         │validationScores                                                      │
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════╪══════════════════╪══════════════════╪══════════════════════════════════════════════════════════════════════╡
// │{minEpochs: 1, maxEpochs: 100, focusWeight: 0.0, patience: 1, toleranc│0.8655632446013092│0.8655627312456534│0.8670358857976215│[0.8655647960242375, 0.861933794035873, 0.5240335648238993, 0.52402952│
// │e: 0.001, learningRate: 0.001, batchSize: 100, penalty: 0.0, methodNam│                  │                  │                  │07655555]                                                             │
// │e: "LogisticRegression", classWeights: []}                            │                  │                  │                  │                                                                      │
// └──────────────────────────────────────────────────────────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────────────────────────────────────────────────────────┘


// 64 dim size:  - 1 min
// created fastrp embedding outside pipeline, only added LR model type
// Started streaming 1 records after 11 ms and completed after 4565 ms.
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════╤══════════════════╤══════════════════╤════════════════════╕
// │winningModel                                                          │avgTrainScore     │outerTrainScore   │testScore         │validationScores    │
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════╪══════════════════╪══════════════════╪════════════════════╡
// │{minEpochs: 1, maxEpochs: 100, focusWeight: 0.0, patience: 1, toleranc│0.8999910283145578│0.8999880645992501│0.9012302062711852│[0.8999998583143526]│
// │e: 0.001, learningRate: 0.001, batchSize: 100, penalty: 0.0, methodNam│                  │                  │                  │                    │
// │e: "LogisticRegression", classWeights: []}                            │                  │                  │                  │                    │
// └──────────────────────────────────────────────────────────────────────┴──────────────────┴──────────────────┴──────────────────┴────────────────────┘


// 128 dim size:  - 1 min
// created fastrp embedding outside pipeline, only added LR model type
// Started streaming 1 records after 18 ms and completed after 5138 ms.
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════╤══════════════════╤══════════════════╤════════════════════╕
// │winningModel                                                          │avgTrainScore     │outerTrainScore   │testScore         │validationScores    │
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════╪══════════════════╪══════════════════╪════════════════════╡
// │{minEpochs: 1, maxEpochs: 100, focusWeight: 0.0, patience: 1, toleranc│0.9185178797334274│0.9185176044095787│0.9196383339877402│[0.9185187264987026]│
// │e: 0.001, learningRate: 0.001, batchSize: 100, penalty: 0.0, methodNam│                  │                  │                  │                    │
// │e: "LogisticRegression", classWeights: []}                            │                  │                  │                  │                    │


CALL gds.beta.pipeline.linkPrediction.train('genes_drugs_diseases', {
  pipeline: 'fastrp-pipeline-1',
  modelName: 'fastrp-model-1',
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  sourceNodeLabel: 'drug',
  targetRelationshipType: 'disease_protein',
  targetNodeLabel: 'disease',
  randomSeed: 75
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores;