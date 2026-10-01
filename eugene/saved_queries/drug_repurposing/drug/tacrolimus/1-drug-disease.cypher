//node similarity filtered by tacrolimus
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*tacrolimus.*'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 3,
    similarityCutoff: .2,
    topN: 100,
    topK: 25,
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


// Started streaming 8 records after 14 ms and completed after 59287 ms.
// ╒═══════════════════╤════════════╤═══════════════════════╤═════════════╤══════════╕
// │similarity         │Disease_Name│Drug_Name              │Disease_Index│Drug_Index│
// ╞═══════════════════╪════════════╪═══════════════════════╪═════════════╪══════════╡
// │0.3384834161159624 │"Tacrolimus"│"kidney disease"       │"14251"      │"35764"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.29438432661502206│"Tacrolimus"│"hypertensive disorder"│"14251"      │"33577"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.28953303789678897│"Tacrolimus"│"hypertension"         │"14251"      │"36035"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.28258855356217366│"Tacrolimus"│"liver failure"        │"14251"      │"39531"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.24772065081715094│"Tacrolimus"│"agranulocytosis"      │"14251"      │"36229"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.24715700810543623│"Tacrolimus"│"neutropenia"          │"14251"      │"36104"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.2053599411045542 │"Tacrolimus"│"epilepsy"             │"14251"      │"35641"   │
// ├───────────────────┼────────────┼───────────────────────┼─────────────┼──────────┤
// │0.2053599411045542 │"Tacrolimus"│"epilepsy"             │"14251"      │"35641"   │
// └───────────────────┴────────────┴───────────────────────┴─────────────┴──────────┘