// [1] project - disease to protein graph
MATCH (source:disease)
OPTIONAL MATCH (source)-[r:disease_protein]-(target:gene_protein)
RETURN gds.graph.project(
  'diseaseToProteinGraph',
  source,
  target,
  { relationshipProperties: r { strength: 1 } }
)
