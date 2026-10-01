// some anatomy nodes do not have node_index, thus no embeddings
// 'anatomy',
// anatomy_protein_present: {orientation: 'UNDIRECTED', type:'*'},
// anatomy_protein_absent: {orientation: 'UNDIRECTED', type:'*'}
// 'node_idx', 'label_one_hot_encoding'
// has_MoA: {orientation: 'UNDIRECTED', type:'*'}

CYPHER runtime=parallel
call gds.graph.project(
    'pubmed_graph',
    [
        'disease',
        'drug',
        'gene_protein',
        'pubmed_document'
    ],
    {
        has_extraction: {orientation: 'UNDIRECTED', type:'*'},
        disease_disease: {orientation: 'UNDIRECTED', type:'*'},
        disease_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_drug: {orientation: 'UNDIRECTED', type:'*'},
        drug_effect: {orientation: 'UNDIRECTED', type:'*'},
        protein_protein: {orientation: 'UNDIRECTED', type:'*'},
        indication: {orientation: 'UNDIRECTED', type:'*'},
        contraindication: {orientation: 'UNDIRECTED', type:'*'}
    },
    {
      nodeProperties: ['model2vec_embeddings', 'label_one_hot_encoding']
    }
)
yield graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
return graph, nodeProjection, nodes, rels;

call gds.graph.project(
    'pubmed_graph',
    {
        disease: {},
        drug: {},
        gene_protein: {}
    },
    {
        has_extraction: {orientation: 'UNDIRECTED', type:'*'},
        disease_disease: {orientation: 'UNDIRECTED', type:'*'},
        disease_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_protein: {orientation: 'UNDIRECTED', type:'*'},
        drug_drug: {orientation: 'UNDIRECTED', type:'*'},
        drug_effect: {orientation: 'UNDIRECTED', type:'*'},
        protein_protein: {orientation: 'UNDIRECTED', type:'*'},
        indication: {orientation: 'UNDIRECTED', type:'*'},
        contraindication: {orientation: 'UNDIRECTED', type:'*'}
    },
    {
      nodeProperties: ['node_index', 'node_name']
    }
)
yield graphName AS graph, nodeProjection, nodeCount AS nodes, relationshipCount AS rels
return graph, nodeProjection, nodes, rels;


        pubmed_document: {
          label: 'pubmed_document',
          properties: {
            title: {
              defaultValue: ""
            },
            pmcid: {
              defaultValue: ""
            }
          }
        }



// params taken from that youtube video and original fastrp paper 
// https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/#algorithms-embeddings-fastrp-examples-mutate
// https://youtu.be/HNE-Ctl52hw?t=220
// parameters suggested by video
// iterationWeights: [0.0, 0.0, 1.0] are from the whitepaper, probabilities during the random walk
// normalizationStrength: remove influence of high degree nodes
// the pipeline will run this, or you can generate embeddings outside the pipeline
// call gds.fastRP.mutate(
//   'pubmed_graph',
//   {
//     embeddingDimension: 512,
//     mutateProperty: 'fastrp-embedding',
//     iterationWeights: [.6, .9, 1.0],
//     normalizationStrength: -0.5,
//     randomSeed: 75
//   }
// )
// yield nodePropertiesWritten;


// create node embeddings
call gds.fastRP.mutate(
  'pubmed_graph',
  {
    embeddingDimension: 512,
    mutateProperty: 'fastrp-embedding',
    iterationWeights: [1.0, .8, .15],
    normalizationStrength: -0.5,
    randomSeed: 75,
    featureProperties: ['model2vec_embeddings', 'label_one_hot_encoding'],
    propertyRatio: .25
  }
)
yield nodePropertiesWritten;


// VERIFY embeddings exist after fastrp
call gds.graph.nodeProperty.stream(
  'pubmed_graph', 
  'fastrp-embedding', 
  ['*'],  
  { listNodeLabels: true })
yield nodeId, propertyValue, nodeLabels
return
  gds.util.asNode(nodeId).node_name AS name,
  nodeLabels,
  propertyValue
order by name asc;

