// [4] train nodeDegreeOnlyGraphSageModel
// train nodeDegreeOnlyGraphSageModel
CALL gds.beta.graphSage.train(
    'diseaseToProteinNoPropertiesGraph',
    {
        modelName: 'nodeDegreeOnlyGraphSageModel',
        featureProperties: ['degree'],
        nodeLabels: ['disease', 'gene_protein'],
        relationshipTypes: ['disease_protein']
    }
)
YIELD trainMillis
RETURN trainMillis