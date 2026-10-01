// [2] project - disease to protein graph - this can only be run 1x, the projection might delete on db restart
MATCH (source:disease|drug)
OPTIONAL MATCH (source)-[r:disease_protein|disease_phenotype_positive|disease_phenotype_negative|indication|contraindication|`off-label use`|exposure_disease|pathway_protein|pathway_pathway]-(target:gene_protein|effect_phenotype|drug|disease|exposure|pathway|anatomy)
RETURN gds.graph.project(
  'search_graph',
  source,
  target,
  { relationshipProperties: r { strength: 1 } }
)



MATCH (source:disease)
OPTIONAL MATCH (source)-[r:disease_protein|disease_phenotype_positive|disease_phenotype_negative]-(target:gene_protein|effect_phenotype)
RETURN gds.graph.project(
  'search_graph',
  source,
  target,
  { relationshipProperties: r { strength: 1 } }
)


CALL gds.graph.drop('search_graph')