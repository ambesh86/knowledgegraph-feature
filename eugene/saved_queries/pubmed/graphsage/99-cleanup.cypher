// delete article knn links
match (d1:pubmed_document)-[r:similar_article]-(d2:pubmed_document)
delete r;

// drop model
call gds.model.drop('pubmed_graphsage_model');

// drop graphs
call gds.graph.drop('pubmed_graph');
call gds.graph.drop('pubmed_sampled_graph');

// verify
// count article knn links
match ()-[r:similar_article]-()
return count(r);
// visualize paths
match p=()-[r:similar_article]-()
return p;

call gds.graph.list
call gds.pipeline.list
call gds.model.list


// delete all articles and relationship, this is expensive to rebuild atm
match (n:pubmed_summary)-[r:has_finding]-(n2:pubmed_summary_finding)
delete r, n2;

match (n:pubmed_document)-[r:has_summary]-(n2:pubmed_summary)
delete r, n2;

match (n:pubmed_document)-[r:has_extraction]-()
delete n, r;
