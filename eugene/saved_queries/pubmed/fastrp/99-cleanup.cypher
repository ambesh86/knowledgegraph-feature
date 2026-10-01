// delete article knn links
MATCH ()-[r:similar_article]-()
DELETE r;

// drop model
call gds.model.drop('pubmed-disease-model')
    yield modelName, modelType, modelInfo, loaded, stored, published;

call gds.model.drop('pubmed-drug-model')
    yield modelName, modelType, modelInfo, loaded, stored, published;

// drop pipeline
call gds.pipeline.drop('pubmed-pipeline-1');

// drop graph
call gds.graph.drop('pubmed_graph');



// verify
// count article knn links
MATCH ()-[r:similar_article]-()
RETURN count(r)
// visualize paths
MATCH p=()-[r:similar_article]-()
RETURN p

call gds.graph.list
call gds.pipeline.list
call gds.model.list


