 // stream degree
 CALL gds.graph.nodeProperty.stream('diseaseToProteinNoPropertiesGraph', 'degree')
YIELD nodeId, propertyValue
RETURN nodeId as id, gds.util.asNode(nodeId).node_name AS name, propertyValue AS degree
ORDER BY degree DESC
