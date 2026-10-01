// delete article knn links
MATCH ()-[r:similar_article]-()
DELETE r;

// drop model
call gds.model.drop('tpp_pgpub_model')
    yield modelName, modelType, modelInfo, loaded, stored, published;

// drop pipeline
call gds.pipeline.drop('pgpub_pipeline_1');

// drop graph
call gds.graph.drop('eugene_foundational_graph');

drop index 'pgpub_prediction_embeddings_index' if exists;

drop index 'csl_tpp_prediction_embeddings_index' if exists;




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


MATCH (n)
where ID(n) = 132065
return n



// clean up TPP nodes
MATCH (n:csl_tpp)-[r]-(n2:csl_tpp_question)
DELETE r, n2;

MATCH ()-[r:has_publication]-(n:csl_tpp)
DELETE r;

MATCH p=(n:csl_tpp)-[summaryrel:has_summary]-(summary)-[findingrel:has_finding]-(finding)
DELETE summaryrel, summary, findingrel, finding;

MATCH (n:csl_tpp)
DELETE n;

// reingest tpps
// time python src/analyze_tpps.py --resources-directory resources/data/tpp --linking 


// clean up pgpub nodes
MATCH p=(n:uspto_pgpub)-[r:has_associated_document]-(n2:uspto_application)
DELETE r, n2

MATCH (n:uspto_pgpub)-[r]-()
DELETE r

MATCH (n:uspto_pgpub)
DELETE n

// reingest pgpub
// time python src/download_and_link_patent_applications.py --max-applications 20 --linking 