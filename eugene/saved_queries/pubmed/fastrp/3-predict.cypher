

call gds.beta.pipeline.linkPrediction.predict.stream('pubmed_graph', {
  modelName: 'pubmed-disease-model',
  topN: 1000,
  threshold: 0.5
})
 yield node1, node2, probability
 return probability, gds.util.asNode(node1).node_name as disease, gds.util.asNode(node2).title as article, gds.util.asNode(node2).pmcid as pmcid
 order by probability desc, disease, article;

// potentially related result
// "C1q nephropathy"	"Decision experiences in joint replacement surgery for patients with haemophilic arthritis: A qualitative study"
// ╒══════════════════════════════════════════════════════════════════════╤══════════════════════════════════════════════════════════════════════╤═══════════╕
// │disease                                                               │article                                                               │probability│
// ╞══════════════════════════════════════════════════════════════════════╪══════════════════════════════════════════════════════════════════════╪═══════════╡
// │"46,XY gonadal dysgenesis-motor and sensory neuropathy syndrome"      │"A Case Report of Neuromyelitis Optica Spectrum Disorder (NMOSD) Treat│1.0        │
// │                                                                      │ment in Resource‐Limited Setup: An Ethiopian Experience"              │           │
// ├──────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────┤
// │"Al-Gazali syndrome"                                                  │"Glutamine missense suppressor transfer RNAs inhibit polyglutamine agg│1.0        │
// │                                                                      │regation"                                                             │           │
// ├──────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────┤
// │"C1q nephropathy"                                                     │"Decision experiences in joint replacement surgery for patients with h│1.0        │
// │                                                                      │aemophilic arthritis: A qualitative study"                            │           │
// ├──────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────┤
// │"Canavan disease"                                                     │"Mitochondria-Targeted Biomaterials-Regulating Macrophage Polarization│1.0        │
// │                                                                      │ Opens New Perspectives for Disease Treatment"                        │           │
// ├──────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────┤


CALL gds.beta.pipeline.linkPrediction.predict.stream('pubmed_graph', {
  modelName: 'pubmed-drug-model',
  topN: 200,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN probability, gds.util.asNode(node1).node_name AS drug, gds.util.asNode(node2).title AS article, gds.util.asNode(node2).pmcid as pmcid 
 ORDER BY probability DESC, drug, article;
