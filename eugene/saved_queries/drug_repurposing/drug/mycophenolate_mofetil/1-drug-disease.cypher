// – Generic Name: Mycophenolate mofetil
//  Immunosuppressant used in preventing and treating GVHD.
//node similarity filtered by mycophenolate mofetil
// https://go.drugbank.com/drugs/DB00688
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*mycophenolate.*mofetil.*'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 2,
    similarityCutoff: .2,
    topN: 20,
    topK: 20,
    similarityMetric: "COSINE",
    sourceNodeFilter: [drg],
    targetNodeFilter: [dse],
    relationshipTypes: ['drug_protein', 'disease_protein']
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS Disease_Name,
gds.util.asNode(node2).node_name AS Drug_Name,
gds.util.asNode(node1).node_index AS Disease_Index,
gds.util.asNode(node2).node_index AS Drug_Index
ORDER BY similarity DESCENDING, Drug_Name, Disease_Name 


// Started streaming 6 records after 13 ms and completed after 80732 ms.
// ╒═══════════════════╤═══════════════════════╤═══════════════════════╤═════════════╤══════════╕
// │similarity         │Disease_Name           │Drug_Name              │Disease_Index│Drug_Index│
// ╞═══════════════════╪═══════════════════════╪═══════════════════════╪═════════════╪══════════╡
// │0.26512748062438973│"Mycophenolate mofetil"│"hypertensive disorder"│"14964"      │"33577"   │
// ├───────────────────┼───────────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.25980665560027577│"Mycophenolate mofetil"│"hypertension"         │"14964"      │"36035"   │
// ├───────────────────┼───────────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.22901779193873018│"Mycophenolate mofetil"│"agranulocytosis"      │"14964"      │"36229"   │
// ├───────────────────┼───────────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.22901779193873018│"Mycophenolate mofetil"│"agranulocytosis"      │"14964"      │"36229"   │
// ├───────────────────┼───────────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.22849670413739645│"Mycophenolate mofetil"│"neutropenia"          │"14964"      │"36104"   │
// ├───────────────────┼───────────────────────┼───────────────────────┼─────────────┼──────────┤
// │0.22849670413739645│"Mycophenolate mofetil"│"neutropenia"          │"14964"      │"36104"   │
// └───────────────────┴───────────────────────┴───────────────────────┴─────────────┴──────────┘
