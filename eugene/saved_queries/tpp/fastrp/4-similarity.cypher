// node_id: 2b991311ba1be0062e29509a1e140329
// node_id: f6fb4e9335f4fb989cad45fefad267d7
match (tpp:csl_tpp)
  where tpp.node_id = 'f6fb4e9335f4fb989cad45fefad267d7' 
with tpp as source_tpp
match (pgpub:`uspto_pgpub`)
with source_tpp, pgpub as target_pgpub
call gds.knn.filtered.write(
  'eugene_foundational_graph',
  {
    nodeProperties: ['prediction_embedding'],
    sourceNodeFilter: source_tpp,
    targetNodeFilter: target_pgpub,
    // nodeLabels: ['uspto_pgpub', 'csl_tpp'],
    topK: 4,
    sampleRate: 1.0,
    deltaThreshold: 0.001,
    similarityCutoff: .85,
    randomSeed: 75,
    concurrency: 1,
    writeProperty: 'similarity_score',
    writeRelationshipType: 'similar_article'
  }
)
yield similarityDistribution
return similarityDistribution.mean as meanSimilarity;


// count aritlce knn links
MATCH (csl_tpp)-[r:similar_article]-(uspto_pgpub)
RETURN count(r);

MATCH (csl_tpp)-[r:similar_article]-(uspto_pgpub)
RETURN csl_tpp;

// visualize paths
MATCH p=()-[r:similar_article]-()
where r.similarity_score > .7
RETURN p;

// clean up 
match ()-[r:similar_article]-()
delete r;