//node similarity filtered by gvhd
MATCH (dse:disease) - [r2:disease_protein] - (p1:gene_protein) - [r:drug_protein] - (drg:drug)
WHERE dse.node_name =~ '(?i).*aGVHD.*' OR
    dse.node_name =~ '(?i).*cGVHD.*' OR
    dse.node_name =~ '(?i).*Graft.*Host Disease.*'
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


// Started streaming 3 records after 14 ms and completed after 8082 ms.
// ╒═══════════════════╤═══════════════════════════╤══════════╤═════════════╤══════════╕
// │similarity         │Disease_Name               │Drug_Name │Disease_Index│Drug_Index│
// ╞═══════════════════╪═══════════════════════════╪══════════╪═════════════╪══════════╡
// │0.20412414523193154│"graft versus host disease"│"LLL-3348"│"32520"      │"19383"   │
// ├───────────────────┼───────────────────────────┼──────────┼─────────────┼──────────┤
// │0.20412414523193154│"graft versus host disease"│"VIR201"  │"32520"      │"18158"   │
// ├───────────────────┼───────────────────────────┼──────────┼─────────────┼──────────┤
// │0.14433756729740646│"graft versus host disease"│"CRx-139" │"32520"      │"17592"   │
// └───────────────────┴───────────────────────────┴──────────┴─────────────┴──────────┘
