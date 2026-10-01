call gds.graph.project(
    'eugene_foundational_graph',
    [
      'anatomy',
      'biological_process',
      'cellular_component',
      'csl_tpp',
      'disease',
      'drug',
      'gene_protein',
      'molecular_function',
      'pathway',
      'uspto_pgpub'
    ],
    {
        has_publication: {orientation: 'UNDIRECTED', type:'*'},
        anatomy_protein_present: {orientation: 'UNDIRECTED', type:'*'},
        anatomy_protein_absent: {orientation: 'UNDIRECTED', type:'*'},
        bioprocess_bioprocess: {orientation: 'UNDIRECTED', type:'*'},
        contraindication: {orientation: 'UNDIRECTED', type:'*'},
        cellcomp_cellcomp: {orientation: 'UNDIRECTED', type:'*'},
        disease_disease: {orientation: 'UNDIRECTED', type:'*'},
        disease_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_drug: {orientation: 'UNDIRECTED', type:'*'},
        drug_effect: {orientation: 'UNDIRECTED', type:'*'},
        protein_protein: {orientation: 'UNDIRECTED', type:'*'},
        pathway_protein: {orientation: 'UNDIRECTED', type:'*'},
        pathway_pathway: {orientation: 'UNDIRECTED', type:'*'},
        indication: {orientation: 'UNDIRECTED', type:'*'},
        molfunc_molfunc: {orientation: 'UNDIRECTED', type:'*'}
    },
    {
      nodeProperties: ['embeddings', 'label_one_hot_encoding']
    }
)
yield graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
return graph, nodeProjection, nodes, rels;

// params taken from that youtube video and original fastrp paper 
// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/#algorithms-embeddings-fastrp-examples-mutate
// https://youtu.be/HNE-Ctl52hw?t=220
// parameters suggested by video
// iterationWeights: [0.0, 0.0, 1.0] are from the whitepaper, probabilities during the random walk
// normalizationStrength: remove influence of high degree nodes
// the pipeline will run this, or you can generate embeddings outside the pipeline


// create node embeddings
call gds.fastRP.write(
  'eugene_foundational_graph',
  {
    embeddingDimension: 512,
    writeProperty: 'prediction_embeddings',
    iterationWeights: [0, .6, .8],
    normalizationStrength: -0.5,
    randomSeed: 75,
    featureProperties: ['embeddings', 'label_one_hot_encoding'],
    propertyRatio: .50
  }
)
yield nodePropertiesWritten;


// VERIFY embeddings exist after fastrp
call gds.graph.nodeProperty.stream(
  'eugene_foundational_graph', 
  'prediction_embedding', 
  ['*'],  
  { listNodeLabels: true })
yield nodeId, propertyValue, nodeLabels
return
  gds.util.asNode(nodeId).node_name AS name,
  nodeLabels,
  propertyValue
order by name asc;

