CALL gds.graph.project(
'genes_drugs_diseases',
['disease', 'drug', 'gene_protein'],
{
    disease_protein: {orientation: 'UNDIRECTED', type:'*'},
    drug_protein: {orientation: 'UNDIRECTED', type:'*'}
})
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels;



//node similarity filtered - lupus
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein] - (dse:disease)
    WHERE dse.node_name =~ '(?i).*lupus.*'
CALL gds.nodeSimilarity.filtered.stream('genes_drugs_diseases', {
    degreeCutoff: 3,
    similarityCutoff: .5,
    topN: 3,
    topK: 5,
    similarityMetric: "COSINE",
    sourceNodeFilter: [dse],
    targetNodeFilter: [drg],
    relationshipTypes: ['drug_protein', 'disease_protein']
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS Disease1_Name,
gds.util.asNode(node2).node_name AS Disease2_Name,
gds.util.asNode(node1).node_index AS Disease1_Index,
gds.util.asNode(node2).node_index AS Disease2_Index
ORDER BY similarity DESCENDING, Disease1_Name, Disease2_Name


╒══════════════════╤═════════════════╤═════════════╤══════════════╤══════════════╕
│similarity        │Disease1_Name    │Disease2_Name│Disease1_Index│Disease2_Index│
╞══════════════════╪═════════════════╪═════════════╪══════════════╪══════════════╡
│0.5163977794943223│"lupus nephritis"│"AE-941"     │"94775"       │"16198"       │
├──────────────────┼─────────────────┼─────────────┼──────────────┼──────────────┤
│0.5163977794943223│"lupus nephritis"│"AE-941"     │"94775"       │"16198"       │
└──────────────────┴─────────────────┴─────────────┴──────────────┴──────────────┘







-----


//node similarity filtered - lupus
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein] - (dse:disease)
    WHERE dse.node_name =~ '(?i).*lupus.*'
CALL gds.nodeSimilarity.filtered.
('genes_drugs_diseases', {
    degreeCutoff: 3,
    similarityCutoff: .5,
    topN: 3,
    topK: 5,
    similarityMetric: "COSINE",
    sourceNodeFilter: [dse],
    targetNodeFilter: [drg],
    relationshipTypes: ['drug_protein', 'disease_protein']
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS Disease1_Name,
gds.util.asNode(node2).node_name AS Disease2_Name,
gds.util.asNode(node1).node_index AS Disease1_Index,
gds.util.asNode(node2).node_index AS Disease2_Index
ORDER BY similarity DESCENDING, Disease1_Name, Disease2_Name


// match nodes
MATCH p=(n1 {node_index: '29182'})-[r]-(n2)
RETURN p

// match nodes
MATCH p=(n1 {node_index: '94775'})-[r]-(n2 {node_index: '16198'})
RETURN p


//node similarity filtered - lupus
MATCH (drg:drug) - [r:drug_protein] - (p1:gene_protein) - [r2:disease_protein] - (dse:disease)
    WHERE dse.node_name =~ '(?i).*lupus.*'
CALL gds.nodeSimilarity.filtered.stream('diseaseToProteinGraph', {
    degreeCutoff: 1,
    similarityCutoff: .4,
    similarityMetric: "COSINE",
    sourceNodeFilter: [dse],
    relationshipTypes: ['disease_protein', 'drug_protein']
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS Disease1_Name,
gds.util.asNode(node2).node_name AS Disease2_Name,
gds.util.asNode(node1).node_index AS Disease1_Index,
gds.util.asNode(node2).node_index AS Disease2_Index
ORDER BY similarity DESCENDING, Disease1_Name, Disease2_Name

