// https://go.drugbank.com/drugs/DB00877
//node similarity filtered by sirolimus
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein]  - (dse:disease)
WHERE drg.node_name =~ '(?i).*sirolimus.*'
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


// Started streaming 8 records after 13 ms and completed after 158728 ms.
// ╒══════════════╤═══════════════════════╤══════════╤═════════════╤═══════════════════╕
// │Drug_Name     │Disease_Name           │Drug_Index│Disease_Index│similarity         │
// ╞══════════════╪═══════════════════════╪══════════╪═════════════╪═══════════════════╡
// │"Temsirolimus"│"agranulocytosis"      │"15012"   │"36229"      │0.24307781634110381│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Temsirolimus"│"neutropenia"          │"15012"   │"36104"      │0.24252473754404658│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Temsirolimus"│"hypertensive disorder"│"15012"   │"33577"      │0.24120375163853736│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Temsirolimus"│"hypertension"         │"15012"   │"36035"      │0.23763381936000177│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Sirolimus"   │"agranulocytosis"      │"14975"   │"36229"      │0.23515116887534557│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Sirolimus"   │"neutropenia"          │"14975"   │"36104"      │0.23461612570453777│
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Sirolimus"   │"hypertensive disorder"│"14975"   │"33577"      │0.2118722156958351 │
// ├──────────────┼───────────────────────┼──────────┼─────────────┼───────────────────┤
// │"Sirolimus"   │"hypertension"         │"14975"   │"36035"      │0.20891779293379925│
// └──────────────┴───────────────────────┴──────────┴─────────────┴───────────────────┘
