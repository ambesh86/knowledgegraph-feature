match (doc:pubmed_document)
with apoc.map.merge(properties(doc), {
    nodeId: id(doc),
    anatomies: [(doc)-[:has_extraction]-(x:anatomy) | properties(x)],
    drugs: [(doc)-[:has_extraction]-(x:drug) | properties(x)],
    diseases: [(doc)-[:has_extraction]-(x:disease) | properties(x)],
    gene_proteins: [(doc)-[:has_extraction]-(x:gene_protein) | properties(x)],
    pathways: [(doc)-[:has_extraction]-(x:pathway) | properties(x)]
}) as doc order by doc.title
with collect(doc) as docs,
    [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name] as anatomies,
    [x in apoc.coll.flatten(collect(doc.drugs)) | x.node_name] as drugs,
    [x in apoc.coll.flatten(collect(doc.diseases)) | x.node_name] as diseases,
    [x in apoc.coll.flatten(collect(doc.gene_proteins)) | x.node_name] as gene_proteins,
    [x in apoc.coll.flatten(collect(doc.pathways)) | x.node_name] as pathways,
    [x in apoc.coll.flatten(collect(doc.keywords)) | x] as keywords
with docs,
    apoc.coll.frequenciesAsMap(anatomies) as anatomies,
    apoc.coll.frequenciesAsMap(drugs) as drugs,
    apoc.coll.frequenciesAsMap(diseases) as diseases,
    apoc.coll.frequenciesAsMap(gene_proteins) as gene_proteins,
    apoc.coll.frequenciesAsMap(pathways) as pathways,
    apoc.coll.frequenciesAsMap(keywords) as keywords
return {
    facets: {
        anatomies: anatomies,
        drugs: drugs,
        diseases: diseases,
        gene_proteins: gene_proteins,
        pathways: pathways,
        keywords: keywords
    }
}


// Below queries are attempts to get more counts, but these queries do not work

// match (doc:pubmed_document)
// with apoc.map.merge(properties(doc), {
//     nodeId: id(doc),
//     anatomies: [(doc)-[:has_extraction]-(x:anatomy) | properties(x)],
//     drugs: [(doc)-[:has_extraction]-(x:drug) | properties(x)],
//     diseases: [(doc)-[:has_extraction]-(x:disease) | properties(x)],
//     gene_proteins: [(doc)-[:has_extraction]-(x:gene_protein) | properties(x)],
//     pathways: [(doc)-[:has_extraction]-(x:pathway) | properties(x)],
//     summaryCount: count((doc)-[:has_summary]-(x:pubmed_document_summary)
// }) as doc order by doc.title
// with collect(doc) as docs,
//     [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name] as anatomies,
//     [x in apoc.coll.flatten(collect(doc.drugs)) | x.node_name] as drugs,
//     [x in apoc.coll.flatten(collect(doc.diseases)) | x.node_name] as diseases,
//     [x in apoc.coll.flatten(collect(doc.gene_proteins)) | x.node_name] as gene_proteins,
//     [x in apoc.coll.flatten(collect(doc.pathways)) | x.node_name] as pathways,
//     [x in apoc.coll.flatten(collect(doc.keywords)) | x] as keywords
// with docs,
//     apoc.coll.frequenciesAsMap(anatomies) as anatomies,
//     apoc.coll.frequenciesAsMap(drugs) as drugs,
//     apoc.coll.frequenciesAsMap(diseases) as diseases,
//     apoc.coll.frequenciesAsMap(gene_proteins) as gene_proteins,
//     apoc.coll.frequenciesAsMap(pathways) as pathways,
//     apoc.coll.frequenciesAsMap(keywords) as keywords,
//     apoc.coll.frequenciesAsMap([x IN summaryCount |
//     CASE
//         WHEN x < 2 THEN "Few Summaries"
//         WHEN 2 <= x < 7 THEN "Some Summaries"
//         WHEN 7 <= x THEN "Many Summaries"
//     END
//     ]) as summariesBucket
// return {
//     facets: {
//         anatomies: anatomies,
//         drugs: drugs,
//         diseases: diseases,
//         gene_proteins: gene_proteins,
//         pathways: pathways,
//         keywords: keywords,
//         summariesBucket: summariesBucket
//     }
// }






// match (doc:pubmed_document)
// with apoc.map.merge(properties(doc), {
//     nodeId: id(doc),
//     anatomies: [(doc)-[:has_extraction]-(x:anatomy) | properties(x)],
//     drugs: [(doc)-[:has_extraction]-(x:drug) | properties(x)],
//     diseases: [(doc)-[:has_extraction]-(x:disease) | properties(x)],
//     gene_proteins: [(doc)-[:has_extraction]-(x:gene_protein) | properties(x)],
//     pathways: [(doc)-[:has_extraction]-(x:pathway) | properties(x)],
//     summaryCount: count((doc)-[:has_summary]-(:pubmed_document_summary))
// }) as doc order by doc.title
// with collect(doc) as docs,
//     [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name] as anatomies,
//     [x in apoc.coll.flatten(collect(doc.drugs)) | x.node_name] as drugs,
//     [x in apoc.coll.flatten(collect(doc.diseases)) | x.node_name] as diseases,
//     [x in apoc.coll.flatten(collect(doc.gene_proteins)) | x.node_name] as gene_proteins,
//     [x in apoc.coll.flatten(collect(doc.pathways)) | x.node_name] as pathways,
//     [x in apoc.coll.flatten(collect(doc.keywords)) | x] as keywords
// with docs,
//     apoc.coll.frequenciesAsMap(anatomies) as anatomies,
//     apoc.coll.frequenciesAsMap(drugs) as drugs,
//     apoc.coll.frequenciesAsMap(diseases) as diseases,
//     apoc.coll.frequenciesAsMap(gene_proteins) as gene_proteins,
//     apoc.coll.frequenciesAsMap(pathways) as pathways,
//     apoc.coll.frequenciesAsMap(keywords) as keywords,
//     apoc.coll.frequenciesAsMap([x IN summaryCount |
//     CASE
//         WHEN x < 2 THEN "Few Summaries"
//         WHEN 2 <= x < 7 THEN "Some Summaries"
//         WHEN 7 <= x THEN "Many Summaries"
//     END
//     ]) as summariesBucket
// return {
//     facets: {
//         anatomies: anatomies,
//         drugs: drugs,
//         diseases: diseases,
//         gene_proteins: gene_proteins,
//         pathways: pathways,
//         keywords: keywords,
//         summariesBucket: summariesBucket
//     }
// }



// with apoc.map.merge(properties(doc), {
//     nodeId: id(doc),
//     anatomies: [(doc)-[:has_extraction]-(x:anatomy) | properties(x)],
//     drugs: [(doc)-[:has_extraction]-(x:drug) | properties(x)],
//     diseases: [(doc)-[:has_extraction]-(x:disease) | properties(x)],
//     gene_proteins: [(doc)-[:has_extraction]-(x:gene_protein) | properties(x)],
//     pathways: [(doc)-[:has_extraction]-(x:pathway) | properties(x)]
// }) as doc order by doc.title
// with *, count((doc)-[:has_summary]-(:pubmed_document_summary)) as summaryCount
// with collect(doc) as docs,
//     [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name] as anatomies,
//     [x in apoc.coll.flatten(collect(doc.drugs)) | x.node_name] as drugs,
//     [x in apoc.coll.flatten(collect(doc.diseases)) | x.node_name] as diseases,
//     [x in apoc.coll.flatten(collect(doc.gene_proteins)) | x.node_name] as gene_proteins,
//     [x in apoc.coll.flatten(collect(doc.pathways)) | x.node_name] as pathways,
//     [x in apoc.coll.flatten(collect(doc.keywords)) | x] as keywords,
//     doc.summaryCount as summaryCount
// with *,
//     apoc.coll.frequenciesAsMap(anatomies) as anatomies,
//     apoc.coll.frequenciesAsMap(drugs) as drugs,
//     apoc.coll.frequenciesAsMap(diseases) as diseases,
//     apoc.coll.frequenciesAsMap(gene_proteins) as gene_proteins,
//     apoc.coll.frequenciesAsMap(pathways) as pathways,
//     apoc.coll.frequenciesAsMap(keywords) as keywords,
//     apoc.coll.frequenciesAsMap([x IN summaryCount |
//     CASE
//         WHEN x < 2 THEN "Few Summaries"
//         WHEN 2 <= x < 7 THEN "Some Summaries"
//         WHEN 7 <= x THEN "Many Summaries"
//     END
//     ]) as summariesBucket
// return {
//     facets: {
//         anatomies: anatomies,
//         drugs: drugs,
//         diseases: diseases,
//         gene_proteins: gene_proteins,
//         pathways: pathways,
//         keywords: keywords,
//         summariesBucket: summariesBucket
//     }
// }


// match (doc:pubmed_document)
// with apoc.map.merge(properties(doc), {
//     nodeId: id(doc),
//     anatomies: [(doc)-[:has_extraction]-(x:anatomy) | properties(x)],
//     drugs: [(doc)-[:has_extraction]-(x:drug) | properties(x)],
//     diseases: [(doc)-[:has_extraction]-(x:disease) | properties(x)],
//     gene_proteins: [(doc)-[:has_extraction]-(x:gene_protein) | properties(x)],
//     pathways: [(doc)-[:has_extraction]-(x:pathway) | properties(x)]
//     // summaryCount: count((doc)-[:has_summary]-(:pubmed_document_summary))
// }) as doc order by doc.title
// UNION
//     MATCH p=(doc)-[:has_summary]-(:pubmed_document_summary) 
//     with doc, count (p) as summaryCount
// with *
// with collect(doc) as docs,
//     [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name] as anatomies,
//     [x in apoc.coll.flatten(collect(doc.drugs)) | x.node_name] as drugs,
//     [x in apoc.coll.flatten(collect(doc.diseases)) | x.node_name] as diseases,
//     [x in apoc.coll.flatten(collect(doc.gene_proteins)) | x.node_name] as gene_proteins,
//     [x in apoc.coll.flatten(collect(doc.pathways)) | x.node_name] as pathways,
//     [x in apoc.coll.flatten(collect(doc.keywords)) | x] as keywords,
//     [x in apoc.meta.nodes.count((doc)-[:has_summary]-(:pubmed_document_summary)) | x] as summaryCount
// with *,
//     apoc.coll.frequenciesAsMap(anatomies) as anatomies,
//     apoc.coll.frequenciesAsMap(drugs) as drugs,
//     apoc.coll.frequenciesAsMap(diseases) as diseases,
//     apoc.coll.frequenciesAsMap(gene_proteins) as gene_proteins,
//     apoc.coll.frequenciesAsMap(pathways) as pathways,
//     apoc.coll.frequenciesAsMap(keywords) as keywords,
//     apoc.coll.frequenciesAsMap([x IN summaryCount |
//     CASE
//         WHEN x < 2 THEN "Few Summaries"
//         WHEN 2 <= x < 7 THEN "Some Summaries"
//         WHEN 7 <= x THEN "Many Summaries"
//     END
//     ]) as summariesBucket
// return {
//     facets: {
//         anatomies: anatomies,
//         drugs: drugs,
//         diseases: diseases,
//         gene_proteins: gene_proteins,
//         pathways: pathways,
//         keywords: keywords,
//         summariesBucket: summariesBucket
//     }
// }