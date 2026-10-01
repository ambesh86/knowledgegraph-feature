CALL gds.graph.project(
  'pubmed_to_community',
  [
    'pubmed_document',
    'anatomy',
    'disease',
    'drug',
    'gene_protein'
  ],
  {
      has_extraction: {orientation: 'UNDIRECTED', type:'*'}
  }
)
YIELD
graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
RETURN
graph, nodeProjection, nodes, rels;

MATCH (source:`pubmed_document`)-[r:`has_extraction`]->(target:drug|disease)
RETURN gds.graph.project(
  'pubmed_to_community',
  source,
  target,
  {
    sourceNodeProperties: source {
      pmcid: coalesce(toString(source.pmcid), -100), 
      title: coalesce(source.title, "")
    },
    targetNodeProperties: target {
      node_index: coalesce(target.node_index, -1),
      node_name: coalesce(target.node_name, "")
    }
  }
);

  {
    sourceNodeProperties: source {
      pmcid: coalesce(toString(source.pmcid), "-100"), 
      title: coalesce(source.title, ""),
      keywords: coalesce(toStringList(source.keywords), "")
    },
    targetNodeProperties: target {
      node_index: coalesce(target.node_index, "-1"),
      node_name: coalesce(target.node_name, "")
    }
  }

CALL gds.labelPropagation.mutate('pubmed_to_community', { mutateProperty: 'lpa_community', seedProperty: 'node_index' })
YIELD communityCount, ranIterations, didConverge;

// if using mutation, then stream results
CALL gds.graph.nodeProperty.stream('pubmed_to_community', 'lpa_community')
YIELD nodeId, propertyValue
RETURN propertyValue AS community, gds.util.asNode(nodeId).node_name AS name, gds.util.asNode(nodeId).title AS title,
 gds.util.asNode(nodeId).keywords AS keywords
ORDER BY name ASC;

// if using mutation, then stream results for a single community
CALL gds.graph.nodeProperty.stream('pubmed_to_community', 'lpa_community')
YIELD nodeId, propertyValue
WHERE propertyValue = 26829
RETURN propertyValue AS community, gds.util.asNode(nodeId).node_name AS name, gds.util.asNode(nodeId).title AS title,
 gds.util.asNode(nodeId).keywords AS keywords
ORDER BY name ASC;

// if using mutation, then stream results
CALL gds.graph.nodeProperty.stream('pubmed_to_community', 'lpa_community')
YIELD nodeId, propertyValue
WHERE propertyValue = 26765
RETURN propertyValue AS community, gds.util.asNode(nodeId).node_name AS name, gds.util.asNode(nodeId).title AS title,
 gds.util.asNode(nodeId).keywords AS keywords
ORDER BY name ASC;


// cleanup
CALL gds.graph.drop('pubmed_to_community');
