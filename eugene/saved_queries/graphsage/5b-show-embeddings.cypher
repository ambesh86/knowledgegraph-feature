// 5b show embeddings
CALL gds.beta.graphSage.stream(
    'diseaseToProteinNoPropertiesGraph',
    {
        modelName: 'nodeDegreeOnlyGraphSageModel'
    }
)
YIELD nodeId, embedding
RETURN gds.util.asNode(nodeId).node_name AS disease, embedding
ORDER BY disease, embedding


CALL gds.beta.graphSage.mutate(
  'diseaseToProteinNoPropertiesGraph',
  {
    modelName: 'nodeDegreeOnlyGraphSageModel',
    mutateProperty: 'inMemoryEmbedding'
  }
) 
YIELD nodeCount, nodePropertiesWritten