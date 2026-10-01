CALL gds.beta.pipeline.linkPrediction.predict.stream('genes_drugs_diseases', {
  modelName: 'fastrp-model-sm',
  topN: 10,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN gds.util.asNode(node1).node_name AS node1, gds.util.asNode(node2).node_name AS node2, probability
 ORDER BY probability DESC, node1, node2;

// predict
CALL gds.beta.pipeline.linkPrediction.predict.stream('genes_drugs_diseases', {
  modelName: 'fastrp-model-sm',
  topN: 10,
  threshold: 0.5
})
 YIELD node1, node2, probability
 RETURN gds.util.asNode(node1).node_name AS node1, gds.util.asNode(node2).node_name AS node2, probability
 ORDER BY probability DESC, node1, node2;
// Started streaming 25 records after 19 ms and completed after 124958 ms.
// ╒══════════╤══════════╤══════════════════╕
// │gene1     │gene2     │probability       │
// ╞══════════╪══════════╪══════════════════╡
// │"RPL10L"  │"RPS27L"  │0.5035031590300069│
// ├──────────┼──────────┼──────────────────┤
// │"TTC30A"  │"TTC30B"  │0.5034966949271202│
// ├──────────┼──────────┼──────────────────┤
// │"MRPL2"   │"MRPL41"  │0.5034901770917712│
// ├──────────┼──────────┼──────────────────┤
// │"HSPB11"  │"TTC30A"  │0.5034848360567117│

// embedding size: 64 - ~2 mins
// algo: linear regression
// Started streaming 10 records after 9 ms and completed after 89753 ms.
// ╒════════╤════════╤══════════════════╕
// │gene1   │gene2   │probability       │
// ╞════════╪════════╪══════════════════╡
// │"RPL10L"│"RPS27L"│0.5016735754625922│
// ├────────┼────────┼──────────────────┤
// │"RPS26" │"RPS27L"│0.5016585231137747│
// ├────────┼────────┼──────────────────┤
// │"RPS15A"│"RPS27L"│0.5016575083481802│
// ├────────┼────────┼──────────────────┤
// │"RPS5"  │"RPS27L"│0.5016552748233392│

// embedding sim: 64 - ~17mins
// algo: multi layer perceptron
// Started streaming 10 records after 11 ms and completed after 1024219 ms.
// the gene2 is actually a gene or disease
// ╒════════════════╤══════════════════════════════════════════╤══════════════════╕
// │gene1           │gene2                                     │probability       │
// ╞════════════════╪══════════════════════════════════════════╪══════════════════╡
// │"PLAT"          │"IgG4-related sclerosing cholangitis"     │0.5429224493564782│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"ASB6"          │"IgG4-related submandibular gland disease"│0.5428917074765895│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"ASB6"          │"eosinophilic angiocentric fibrosis"      │0.5428917074765895│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"LIPA"          │"glaucoma 3, primary congenital"          │0.5427788284864583│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"LIPA"          │"hydrophthalmos"                          │0.5427574350887934│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"UGT1A4"        │"PSMC3IP"                                 │0.5427449887791281│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"LIPA"          │"primary congenital glaucoma (disease)"   │0.5427168262796709│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"PSMC3IP"       │"UGT1A7"                                  │0.5426824082392586│
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"RPL17-C18orf32"│"fallopian tube carcinosarcoma"           │0.542676909047231 │
// ├────────────────┼──────────────────────────────────────────┼──────────────────┤
// │"RPS14"         │"hereditary fallopian tube carcinoma"     │0.5426667519115477│
// └────────────────┴──────────────────────────────────────────┴──────────────────┘

// embedding dim size; 256 - ~4mins
// algo: lr
// Started streaming 10 records after 7 ms and completed after 260120 ms.
// ╒════════╤═══════════╤══════════════════╕
// │node1   │node2      │probability       │
// ╞════════╪═══════════╪══════════════════╡
// │"RNF145"│"C5orf15"  │0.5002330558836426│
// ├────────┼───────────┼──────────────────┤
// │"RNF145"│"DPH5"     │0.5002330558836426│
// ├────────┼───────────┼──────────────────┤
// │"RNF145"│"EEF1A1P5" │0.5002330558836426│
// ├────────┼───────────┼──────────────────┤
// │"RNF145"│"EIF5AL1"  │0.5002330558836426│
// ├────────┼───────────┼──────────────────┤
// │"RNF145"│"HNRNPCL3" │0.5002330558836426│


// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/#linkprediction-adding-node-properties
// VERIFY embeddings exist AFTER pipeline prediction, with node labels
CALL gds.graph.nodeProperty.stream(
  'geneToDisease', 
  'embedding256', 
  ['*'],  
  { listNodeLabels: true })
YIELD nodeId, propertyValue, nodeLabels
RETURN
  gds.util.asNode(nodeId).node_name AS name,
  nodeLabels,
  propertyValue
ORDER BY name ASC

// https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/#linkprediction-adding-node-properties
// VERIFY embeddings exist AFTER pipeline prediction
// CALL gds.graph.nodeProperty.stream('diseaseToProtein', 'embedding', ['disease', 'gene_protein'])
// YIELD nodeId, propertyValue
// RETURN gds.util.asNode(nodeId).node_name AS name, propertyValue AS embedding
// ORDER BY name ASC


// Verify matches
// Match base node
MATCH p=(n1:gene_protein { node_name: 'RPL10L' })-[r]->(n2:gene_protein)
RETURN p LIMIT 100

MATCH p=(n1:gene_protein { node_name: 'RPS27L' })-[r]->(n2:gene_protein)
RETURN p LIMIT 100

// Match suggested relationship, this will come back empty as this is a new prediction of an unseen link
MATCH p=(n1:gene_protein { node_name: 'RPL10L' })-[r]->(n2:gene_protein { node_name: 'RPS27L' })
RETURN p





CALL gds.beta.pipeline.linkPrediction.predict.stream('genes_drugs_diseases', {
  modelName: 'fastrp-model-1',
  topN: 10,
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