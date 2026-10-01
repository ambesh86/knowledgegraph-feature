// faceted query NODES 2023 talk - https://www.youtube.com/watch?app=desktop&v=8Fzt5SOlisk2VAc
// phase 1

:params
{
    "searchCriteria": {
        "anatomyCount": {
            "low": 0,
            "high": 4
        },
        "biologicalProcessCount": {
            "low": 0,
            "high": 2
        },
        "diseaseCount": {
            "low": 0,
            "high": 8
        },
        "drugCount": {
            "low": 0,
            "high": 4
        },
        "geneProteinCount": {
            "low": 0,
            "high": 8
        },
        "pathwayCount": {
            "low": 0,
            "high": 2
        },
        "pubmedSummaryCount": {
            "low": 3,
            "high": 6
        },
        "selectedAnatomy": [
            {
                "label": "Anatomy",
                "property": "name",
                "values": [
                    "colon"
                ]
            }
        ]
    }
}

with $searchCriteria as searchCriteria,
{
    Article: {
        props: [],
        match (doc:pubmed_document),
        where: {
            anatomyCount: "
                any(x in searchCriteria.anatomyCount where
                    x.low <= toInteger(doc.anatomyCount) < x.high
                )
            "
        }
    }
} as cypherModel;

with cypherModel, {
    selectedAnatomy: coalesce(searchCriteria.selectedAnatomy, [])
    keywords: coalesce(searchCriteria.keywords, [])
};

with cypherModel, searchCriteria,
    apoc.map.fromPairs([x in searchCriteria.selectedAnatomy | [x.label + '_' + x.property, x.values]])
    as searchCriteriaMap;


with cypherModel, searchCriteria, searchCriteriaMap

call apoc.when(size(searchCriteria.keywords) > 0,

)



// phase 2
call apoc.cypher.run(cypher, { searchCriteriaMap: searchCriteriaMap, searchCriteria: searchCriteria })
yield value
with distinct(value.doc) as doc
limit 250

with apoc.map.merge(properties(doc), {
    nodeId: id(doc),
    anatomies: [(doc)-[:has_extracted]-(a:anatomy) | properties(anatomy)]
}) as doc order by doc.title

with collect(doc) as docs,
    collect(doc.anatomyCount) as anatomyCounts,
    [x in apoc.coll.flatten(collect(doc.anatomies)) | x.node_name]
