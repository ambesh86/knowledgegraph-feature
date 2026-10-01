// https://go.drugbank.com/drugs/DB00091
//node similarity filtered by cyclophosphamide
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*cyclosporine.*'
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

// Started streaming 6 records after 16 ms and completed after 86590 ms.
// ╒══════════════╤═══════════════════════╤══════════╤═════════════╤═══════════════════╕
// │Drug_Name     │Disease_Name           │Drug_Index│Disease_Index│similarity         │
// ╞══════════════╪═══════════════════════╪══════════╪═════════════╪═══════════════════╡
// │"Cyclosporine"│"hypertensive disorder"│"14934"   │"33577"      │0.31719009989855745│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Cyclosporine"│"hypertension"         │"14934"   │"36035"      │0.3108244337783695 │
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Cyclosporine"│"agranulocytosis"      │"14934"   │"36229"      │0.2544222400924133 │
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Cyclosporine"│"neutropenia"          │"14934"   │"36104"      │0.2538433491487105 │
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Cyclosporine"│"epilepsy"             │"14934"   │"35641"      │0.22987203539228981│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Cyclosporine"│"epilepsy"             │"14934"   │"35641"      │0.22987203539228981│
// └──────────────┴───────────────────────┴──────────┴─────────────┴───────────────────┘