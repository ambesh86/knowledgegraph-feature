
call gds.knn.write(
  'pubmed_graph',
  {
    nodeProperties: ['fastrp-embedding'],
    nodeLabels: ['pubmed_document'],
    topK: 8,
    sampleRate: 1.0,
    deltaThreshold: 0.001,
    similarityCutoff: .85,
    randomSeed: 75,
    concurrency: 1,
    writeProperty: 'fastrp_score',
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
where r.fastrp_score > .7
RETURN p;

// gvhd docs
match p=(n:pubmed_document)-[r:has_extraction]-(n2:disease)
where n.pmcid in ['11759061', '11781120', '11759780', '11759061']
return p

// visualize paths
MATCH p=(n1:pubmed_document)-[r:has_extraction]-(n2:anatomy)
RETURN p;

// visualize paths
MATCH p=(n1:pubmed_document)-[r:has_extraction]-(n2:disease)
RETURN p;