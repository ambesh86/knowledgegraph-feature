# https://neo4j.com/docs/graph-data-science/current/model-catalog/list/
CALL gds.model.list()
YIELD modelName, modelType, modelInfo, loaded, stored, published
