// small query
match (node:drug)
with apoc.map.merge(properties(node), {
    nodeId: id(node),
    indications: [(node)-[:indication]-(x:disease) | properties(x)],
    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
    offLabels: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
}) as node order by node.title
with collect(node) as nodes,
    [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
    [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
    [x in apoc.coll.flatten(collect(node.offLabels)) | x.node_name] as offLabels,
    [x in apoc.coll.flatten(collect(node.indicationCount)) | x.node_name] as indicationCount,
    [x in apoc.coll.flatten(collect(node.contraindicationCount)) | x.node_name] as contraindicationCount,
    [x in apoc.coll.flatten(collect(node.offLabelCount)) | x] as offLabelCount
with nodes,
    apoc.coll.frequenciesAsMap(indications) as indications,
    apoc.coll.frequenciesAsMap(contraindications) as contraindications,
    apoc.coll.frequenciesAsMap(offLabels) as offLabels
return {
    facets: {
        indications: indications,
        contraindications: contraindications,
        offLabels: offLabels
    }
}
