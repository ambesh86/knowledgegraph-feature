// [3] node similarity - disease to protein graph
CALL gds.nodeSimilarity.stream('genes_drugs_diseases')
YIELD node1, node2, similarity
RETURN gds.util.asNode(node1).node_name AS Disease1, gds.util.asNode(node2).node_name AS Disease2, similarity
ORDER BY similarity DESCENDING, Disease1, Disease2
