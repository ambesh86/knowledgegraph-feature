// [3] add degrees
// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/graph-sage/#_train_when_there_are_no_node_properties_present_in_the_graph
// In the case when you have a graph that does not have node properties we recommend to use existing algorithm in mutate mode to create node properties.
CALL gds.degree.mutate(
  'diseaseToProteinNoPropertiesGraph',
  {
    mutateProperty: 'degree'
  }
) YIELD nodePropertiesWritten