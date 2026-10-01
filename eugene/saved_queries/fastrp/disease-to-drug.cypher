
// CALL gds.graph.project(
// 'genes_drugs_diseases',
// ['disease', 'drug', 'gene_protein'],
// {
//     disease_protein: {orientation: 'UNDIRECTED', type:'*'},
//     drug_protein: {orientation: 'UNDIRECTED', type:'*'}
// })
// YIELD
// graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
// RETURN
// graph, nodeProjection, nodes, rels;



// // https://neo4j.com/docs/graph-data-science/current/management-ops/graph-reads/graph-stream-nodes/
// // view properties
// CALL gds.graph.nodeProperty.stream('diseaseToProteinUndirected', 'dmk-embedding-1', ['disease', 'gene_protein'])
// YIELD nodeId, propertyValue
// RETURN gds.util.asNode(nodeId).name AS name, propertyValue AS embedding
// ORDER BY score ASC

// define the link prediction pipeline
CALL gds.beta.pipeline.linkPrediction.create('fastrp-pipeline-1');

// add embedding as a node property, fast rp will use degree topology
CALL gds.beta.pipeline.linkPrediction.addNodeProperty('fastrp-pipeline-1', 'fastRP', {
  mutateProperty: 'dmk-embedding-1',
  embeddingDimension: 256,
  randomSeed: 75
});

// define embedding as a feature, can add other node properties
CALL gds.beta.pipeline.linkPrediction.addFeature('fastrp-pipeline-1', 'hadamard', {
  nodeProperties: ['dmk-embedding-1']
}) YIELD featureSteps;


// define model type, each model will be tried in the autotuning step
CALL gds.beta.pipeline.linkPrediction.addLogisticRegression('fastrp-pipeline-1')
YIELD parameterSpace;

CALL gds.beta.pipeline.linkPrediction.addRandomForest('fastrp-pipeline-1', {numberOfDecisionTrees: 10 })
YIELD parameterSpace;

// cofigure model training autotuning parameters
CALL gds.alpha.pipeline.linkPrediction.configureAutoTuning('fastrp-pipeline-1', {
  maxTrials: 4
}) YIELD autoTuningConfig;



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



CALL gds.beta.pipeline.linkPrediction.predict.stream('genes_drugs_diseases', {
  modelName: 'fastrp-model-1',
  topN: 10,
  topK: 2,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN gds.util.asNode(node1).node_name AS disease, gds.util.asNode(node2).node_name AS drug, probability
 ORDER BY probability DESC, disease, drug;

// "torsades de pointes"│"Flecainide" is an interesting result
//  ╒═════════════════════╤═══════════════════════════════════════════╤══════════════════╕
// │disease              │drug                                       │probability       │
// ╞═════════════════════╪═══════════════════════════════════════════╪══════════════════╡
// │"torsades de pointes"│"Mequitazine"                              │0.5014669565394289│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Dexchlorpheniramine maleate"              │0.50146656577194  │
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Rupatadine"                               │0.5014648567492243│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Mefloquine"                               │0.5014642113307926│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"unipolar depression"│"Dronabinol"                               │0.5014590588603747│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Flecainide"                               │0.501458898170196 │
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Amodiaquine"                              │0.5014588009752263│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"Propofol"           │"postural orthostatic tachycardia syndrome"│0.5014579674520876│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Encorafenib"                              │0.5014578985167062│
// ├─────────────────────┼───────────────────────────────────────────┼──────────────────┤
// │"torsades de pointes"│"Halofantrine"                             │0.5014577916538572│
// └─────────────────────┴───────────────────────────────────────────┴──────────────────┘
// Started streaming 10 records after 6 ms and completed after 40926 ms.