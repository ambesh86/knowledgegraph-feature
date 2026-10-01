// delete article knn links
MATCH ()-[r:similar_article]-()
DELETE r;

// drop graph
call gds.graph.drop('pubmed_node2vec_graph');



// verify
// count aritlce knn links
MATCH ()-[r:similar_article]-()
RETURN count(r)
// visualize paths
MATCH p=()-[r:similar_article]-()
RETURN p

call gds.graph.list


