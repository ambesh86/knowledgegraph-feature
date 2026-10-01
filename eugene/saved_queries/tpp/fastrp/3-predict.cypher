

// TODO: we need more data in the training step, then we can run this step
call gds.beta.pipeline.linkPrediction.predict.stream('eugene_foundational_graph', {
  modelName: 'tpp_pgpub_model',
  topN: 1000,
  threshold: 0.5
})
 yield node1, node2, probability
 return probability, gds.util.asNode(node1).node_name as disease, gds.util.asNode(node2).title as article, gds.util.asNode(node2).pmcid as pmcid
 order by probability desc, disease, article;
