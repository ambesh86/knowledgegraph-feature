// drop model
call gds.model.drop('fastrp-model-sm')
    YIELD modelName, modelType, modelInfo, loaded, stored, published;

// drop pipeline
call gds.pipeline.drop('fastrp-pipeline-sm');

// drop graph
call gds.graph.drop('geneToDisease');

call gds.graph.list
call gds.pipeline.list
call gds.model.list

