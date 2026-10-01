// [4] node similarity filtered - VWD disease to protein graph
MATCH (d1:disease)
    WHERE d1.node_name = 'von Willebrand disease' OR
    d1.node_name = 'pseudo-von Willebrand disease' OR
    d1.node_name = 'Von Willebrand disease, X-linked form' OR
    d1.node_name = 'hereditary von Willebrand disease' OR
    d1.node_name = 'von Willebrand disease (hereditary or acquired)'
CALL gds.nodeSimilarity.filtered.stream('search_graph', {
    degreeCutoff: 1,
    similarityCutoff: .45,
    similarityMetric: "COSINE",
    sourceNodeFilter: [d1]
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS name1,
gds.util.asNode(node2).node_name AS name2,
gds.util.asNode(node1).node_id AS id1,
gds.util.asNode(node2).node_id AS id2
ORDER BY similarity DESCENDING, name1, name2

// [4] node similarity filtered - lupus disease to protein graph
MATCH (d1:disease)
    WHERE d1.node_name =~ '(?i).*lupus.*'
CALL gds.nodeSimilarity.filtered.stream('search_graph', {
    degreeCutoff: 1,
    similarityCutoff: .45,
    similarityMetric: "COSINE",
    sourceNodeFilter: [d1]
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS name1,
gds.util.asNode(node2).node_name AS name2,
gds.util.asNode(node1).node_id AS id1,
gds.util.asNode(node2).node_id AS id2
ORDER BY similarity DESCENDING, name1, name2

// [4] node similarity filtered - VWD disease to protein graph
// CALL gds.nodeSimilarity.filtered.stream('diseaseToProteinGraph', {
//     degreeCutoff: 1,
//     similarityCutoff: .1,
//     similarityMetric: "COSINE",
//     sourceNodeFilter: [60156, 54134, 73933, 48329, 8332] // node ids for target diseases
// })
// YIELD node1, node2, similarity
// RETURN similarity,
// gds.util.asNode(node1).node_name AS name1,
// gds.util.asNode(node2).node_name AS name2,
// gds.util.asNode(node1).node_id AS id1,
// gds.util.asNode(node2).node_id AS id2
// ORDER BY similarity DESCENDING, name1, name2


MATCH (d1:disease)
    WHERE d1.node_name =~ '(?i).*von willebrand disease.*'
CALL gds.nodeSimilarity.filtered.stream('search_graph', {
    degreeCutoff: 1,
    similarityCutoff: .45,
    similarityMetric: "COSINE",
    sourceNodeFilter: [d1]
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS name1,
gds.util.asNode(node2).node_name AS name2,
gds.util.asNode(node1).node_id AS id1,
gds.util.asNode(node2).node_id AS id2
ORDER BY similarity DESCENDING, name1, name2


MATCH (d1:drug)
    WHERE d1.node_name =~ '(?i).*flurandrenolide.*'
CALL gds.nodeSimilarity.filtered.stream('search_graph', {
    degreeCutoff: 1,
    similarityCutoff: .45,
    similarityMetric: "COSINE",
    sourceNodeFilter: [d1]
})
YIELD node1, node2, similarity
RETURN similarity,
gds.util.asNode(node1).node_name AS name1,
gds.util.asNode(node2).node_name AS name2,
gds.util.asNode(node1).node_id AS id1,
gds.util.asNode(node2).node_id AS id2
ORDER BY similarity DESCENDING, name1, name2


// counts
match (node:drug)
WHERE node.node_name =~ '(?i).*Flurandrenolide.*'
    or node.node_name =~ '(?i).*Fluocinolone acetonide.*' 
    or node.node_name =~ '(?i).*Prednicarbate.*' 
    or node.node_name =~ '(?i).*Desoximetasone.*' 
    or node.node_name =~ '(?i).*Amcinonide.*'
    or node.node_name =~ '(?i).*Benzoyl peroxide.*'
with apoc.map.merge(properties(node), {
    nodeId: id(node),
    indications: [(node)-[:indication]-(x:disease) | properties(x)],
    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
}) as node order by node.title
with collect(node) as nodes,
    [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
    [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
    [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses,
    [x in apoc.coll.flatten(collect(node.indicationCount)) | x.node_name] as indicationCount,
    [x in apoc.coll.flatten(collect(node.contraindicationCount)) | x.node_name] as contraindicationCount,
    [x in apoc.coll.flatten(collect(node.offLabelCount)) | x] as offLabelCount
with nodes,
    apoc.coll.frequenciesAsMap(indications) as indications,
    apoc.coll.frequenciesAsMap(contraindications) as contraindications,
    apoc.coll.frequenciesAsMap(offLabelUses) as offLabelUses
return {
    facets: {
        indications: indications,
        contraindications: contraindications,
        offLabelUses: offLabelUses
    }
}




