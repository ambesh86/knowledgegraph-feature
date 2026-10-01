// [2] estimate - disease to protein graph
CALL gds.nodeSimilarity.write.estimate('diseaseToProteinGraph', {
  writeRelationshipType: 'SIMILAR',
  writeProperty: 'score'
})
YIELD nodeCount, relationshipCount, bytesMin, bytesMax, requiredMemory
