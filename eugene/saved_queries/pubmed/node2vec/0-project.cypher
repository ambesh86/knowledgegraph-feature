        // sourceNodeLabels: ['pubmed_document'],
        // targetNodeLabels: ['anatomy', 'drug', 'disease', 'gene_protein']
        // sourceNodeLabels: labels(source),
        // targetNodeLabels: labels(target)
match (source:pubmed_document)-[r:has_extraction]-(target:drug|disease|anatomy|gene_protein)
return gds.graph.project(
    'pubmed_node2vec_graph',
    source,
    target,
    {
        sourceNodeLabels: ['pubmed_document'],
        targetNodeLabels: ['anatomy', 'drug', 'disease', 'gene_protein']
    }
);

call gds.node2vec.mutate('pubmed_node2vec_graph', 
    {
        mutateProperty: 'pubmed-node2vec-embedding',
        embeddingDimension: 256
    }
)
yield nodeCount
return nodeCount;


call gds.graph.nodeProperty.stream('pubmed_node2vec_graph', 'pubmed-node2vec-embedding', 
    [
        'anatomy',
        'disease', 
        'drug',
        'pubmed_document',
        'gene_protein'
    ]
)
yield nodeId, propertyValue
return gds.util.asNode(nodeId).node_name AS name, propertyValue AS embedding
order by name ASC;


call gds.knn.write(
  'pubmed_node2vec_graph',
  {
    nodeProperties: ['pubmed-node2vec-embedding'],
    nodeLabels: ['pubmed_document'],
    topK: 25,
    sampleRate: 1.0,
    deltaThreshold: 0.001,
    similarityCutoff: .3,
    concurrency: 2,
    writeProperty: 'node2vec_score',
    writeRelationshipType: 'similar_article'
  }
)
yield similarityDistribution
return similarityDistribution.mean as meanSimilarity;


// count aritlce knn links
MATCH ()-[r:similar_article]-()
RETURN count(r);
// visualize paths
MATCH p=()-[r:similar_article]-()
where r.node2vec_score > .5
RETURN p;

// gvhd docs
match p=(n:pubmed_document)-[r:has_extraction]-(n2:disease)
where n.pmcid in ['11759061', '11781120', '11759780', '11759061']
return p