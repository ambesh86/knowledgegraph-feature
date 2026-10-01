//node similarity filtered by vwd
MATCH (dse:disease) - [r2:disease_protein] - (p1:gene_protein) - [r:drug_protein] - (drg:drug)
    WHERE dse.node_name = 'von Willebrand disease' OR
            dse.node_name = 'pseudo-von Willebrand disease' OR
            dse.node_name = 'Von Willebrand disease, X-linked form' OR
            dse.node_name = 'hereditary von Willebrand disease' OR
            dse.node_name = 'von Willebrand disease (hereditary or acquired)'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 1,
    similarityCutoff: .1,
    topN: 10,
    topK: 10,
    similarityMetric: "COSINE",
    sourceNodeFilter: [dse],
    targetNodeFilter: [drg],
    relationshipTypes: ['drug_protein', 'disease_protein']
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS Disease_Name,
gds.util.asNode(node2).node_name AS Drug_Name,
gds.util.asNode(node1).node_index AS Disease_Index,
gds.util.asNode(node2).node_index AS Drug_Index
ORDER BY similarity DESCENDING, Disease_Name, Drug_Name

// Started streaming 4 records after 15 ms and completed after 5906 ms.
// ╒═══════════════════╤═════════════════════════════════════════════════╤════════════════════════════╤═════════════╤══════════╕
// │similarity         │Disease_Name                                     │Drug_Name                   │Disease_Index│Drug_Index│
// ╞═══════════════════╪═════════════════════════════════════════════════╪════════════════════════════╪═════════════╪══════════╡
// │0.35355339059327373│"pseudo-von Willebrand disease"                  │"liposomal prostaglandin E1"│"29845"      │"18381"   │
// ├───────────────────┼─────────────────────────────────────────────────┼────────────────────────────┼─────────────┼──────────┤
// │0.125              │"von Willebrand disease (hereditary or acquired)"│"liposomal prostaglandin E1"│"39535"      │"18381"   │
// ├───────────────────┼─────────────────────────────────────────────────┼────────────────────────────┼─────────────┼──────────┤
// │0.10540925533894598│"von Willebrand disease"                         │"Efmoroctocog alfa"         │"27581"      │"18413"   │
// ├───────────────────┼─────────────────────────────────────────────────┼────────────────────────────┼─────────────┼──────────┤
// │0.10540925533894598│"von Willebrand disease"                         │"Simoctocog alfa"           │"27581"      │"18411"   │
// └───────────────────┴─────────────────────────────────────────────────┴────────────────────────────┴─────────────┴──────────┘