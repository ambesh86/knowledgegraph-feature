//node similarity filtered by cyclophosphamide
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*methotrexate.*'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 3,
    similarityCutoff: .2,
    topN: 20,
    topK: 20,
    similarityMetric: "COSINE",
    sourceNodeFilter: [drg],
    targetNodeFilter: [dse],
    relationshipTypes: ['drug_protein', 'disease_protein']
})
YIELD node1, node2, similarity
RETURN
    gds.util.asNode(node1).node_name AS Drug_Name,
    gds.util.asNode(node2).node_name AS Disease_Name,
    gds.util.asNode(node1).node_index AS Drug_Index,
    gds.util.asNode(node2).node_index AS Disease_Index,
    similarity
ORDER BY similarity DESCENDING


// Started streaming 13 records after 14 ms and completed after 269664 ms.
// ╒═══════════════════╤══════════════╤═════════════════════════════╤═════════════╤══════════╕
// │similarity         │Disease_Name  │Drug_Name                    │Disease_Index│Drug_Index│
// ╞═══════════════════╪══════════════╪═════════════════════════════╪═════════════╪══════════╡
// │0.33802947993760246│"Methotrexate"│"kidney disease"             │"14194"      │"35764"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.22992841299312072│"Methotrexate"│"agranulocytosis"            │"14194"      │"36229"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.22992841299312072│"Methotrexate"│"agranulocytosis"            │"14194"      │"36229"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.22781216120491274│"Methotrexate"│"neutropenia"                │"14194"      │"36104"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.22781216120491274│"Methotrexate"│"neutropenia"                │"14194"      │"36104"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21951115062660018│"Methotrexate"│"macrocytic anemia (disease)"│"14194"      │"33623"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21951115062660018│"Methotrexate"│"macrocytic anemia (disease)"│"14194"      │"33623"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21951115062660018│"Methotrexate"│"macrocytic anemia (disease)"│"14194"      │"33623"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21951115062660018│"Methotrexate"│"macrocytic anemia (disease)"│"14194"      │"33623"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21112974938039378│"Methotrexate"│"anemia (disease)"           │"14194"      │"33632"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21112974938039378│"Methotrexate"│"anemia (disease)"           │"14194"      │"33632"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21112974938039378│"Methotrexate"│"anemia (disease)"           │"14194"      │"33632"   │
// ├───────────────────┼──────────────┼─────────────────────────────┼─────────────┼──────────┤
// │0.21112974938039378│"Methotrexate"│"anemia (disease)"           │"14194"      │"33632"   │
// └───────────────────┴──────────────┴─────────────────────────────┴─────────────┴──────────┘
