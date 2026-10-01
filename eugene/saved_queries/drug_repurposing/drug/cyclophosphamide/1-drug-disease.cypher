//node similarity filtered by cyclophosphamide
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*cyclophosphamide.*'
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
YIELD node1, node2, similarity
RETURN
    gds.util.asNode(node1).node_name AS Drug_Name,
    gds.util.asNode(node2).node_name AS Disease_Name,
    gds.util.asNode(node1).node_index AS Drug_Index,
    gds.util.asNode(node2).node_index AS Disease_Index,
    similarity
ORDER BY similarity DESCENDING

// Started streaming 2 records after 14 ms and completed after 53807 ms.
// ╒═══════════════════╤══════════════════╤═══════════════════════╤═════════════╤══════════╕
// │similarity         │Disease_Name      │Drug_Name              │Disease_Index│Drug_Index│
// ╞═══════════════════╪══════════════════╪═══════════════════════╪═════════════╪══════════╡
// │0.23193486710055858│"Cyclophosphamide"│"hypertensive disorder"│"14954"      │"33577"   │
// ├───────────────────┼──────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.2272801823356037 │"Cyclophosphamide"│"hypertension"         │"14954"      │"36035"   │
// └───────────────────┴──────────────────┴───────────────────────┴─────────────┴──────────┘
