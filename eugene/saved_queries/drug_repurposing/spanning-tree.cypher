// https://neo4j.com/labs/apoc/4.4/overview/apoc.path/apoc.path.spanningTree
// https://neo4j.com/labs/apoc/4.4/overview/apoc.path/apoc.path.spanningTree
MATCH (drg:drug)-[r1]-(p1:gene_protein)-[r2]-(dse:disease)
WHERE drg.node_index = '15012' and dse.node_index = '36104'
CALL apoc.path.spanningTree(drg,{ 
    bfs: true, 
    maxLevel: 100,
    limit: 100,
    relationshipFilter: 'disease_protein|drug_protein',
    labelFilter: 'drug|gene_protein|/disease',
    terminatorNodes: [dse]
}) YIELD path  
RETURN path