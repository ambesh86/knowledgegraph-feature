CALL gds.graph.list()
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount
ORDER BY graphName ASC


CALL gds.graph.list('personsNative')
YIELD graphName, degreeDistribution;
