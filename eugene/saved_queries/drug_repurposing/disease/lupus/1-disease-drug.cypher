//node similarity filtered - lupus
MATCH (dse:disease) - [r2:disease_protein] - (p1:gene_protein) - [r:drug_protein] - (drg:drug)
    WHERE dse.node_name =~ '(?i).*lupus.*'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 2,
    similarityCutoff: .3,
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

// Started streaming 2 records after 14 ms and completed after 199557 m
// ╒══════════════════╤═════════════════╤═════════╤═════════════╤══════════╕
// │similarity        │Disease_Name     │Drug_Name│Disease_Index│Drug_Index│
// ╞══════════════════╪═════════════════╪═════════╪═════════════╪══════════╡
// │0.5163977794943223│"lupus nephritis"│"AE-941" │"94775"      │"16198"   │
// ├──────────────────┼─────────────────┼─────────┼─────────────┼──────────┤
// │0.5163977794943223│"lupus nephritis"│"AE-941" │"94775"      │"16198"   │
// └──────────────────┴─────────────────┴─────────┴─────────────┴──────────┘