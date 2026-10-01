# Foundation Graph API Swagger Testing Guide

This guide covers the ten Foundation routes exposed by the core FastAPI application.
The local Swagger UI is normally:

```text
http://localhost:18000/docs
```

The API is registered by `src/eugene_ws.py` through these routers:

- `src/foundation/router/n_hop_router.py`
- `src/foundation/router/search_path_router.py`
- `src/foundation/router/facts_router.py`
- `src/foundation/router/node_id_lookup_router.py`
- `src/foundation/router/node_details_router.py`
- `src/foundation/router/label_router.py`
- `src/foundation/router/count_router.py`
- `src/foundation/router/facet_router.py`
- `src/foundation/router/similarity_router.py`

## Prerequisites

Start Neo4j and the core API, or use the equivalent deployed API URL. The local Compose defaults are:

```text
Core API:       http://localhost:18000
Neo4j Browser:  http://localhost:17474
Neo4j Bolt:     bolt://localhost:17687
Neo4j username: neo4j
Neo4j password: eugene_local_2024
```

The core API obtains its driver through `GraphDbConnectionFactory.remote_neo4j_instance_from_env()` in `src/graph/infra/db/graph_db_connection_factory.py`. Configure the values expected by that factory, typically:

```text
NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
NEO4J_DATABASE   # if supported by the selected factory implementation
```

The local stack also requires `docker.env` for the broader application and authentication settings. The routes are included by `src/eugene_ws.py`; authentication middleware/router configuration is in `src/router/auth/`. In a protected deployment, authorize in Swagger before executing requests. A direct local deployment may still require the Entra-related variables because the application imports authentication modules at startup.

Relevant dependencies include `fastapi`, `pydantic`, `neo4j`, `pandas`, `numpy`, and the Neo4j APOC/GDS plugins for facet and similarity queries. The local Neo4j Compose service enables both `apoc` and `graph-data-science`.

## Get usable values first

Run these read-only queries in Neo4j Browser. Use the returned values exactly; do not use Neo4j's internal `id(n)` for these APIs unless a response explicitly returns it. The graph APIs use the application property `node_id`.

### Labels and counts

```cypher
CALL db.labels() YIELD label
RETURN label
ORDER BY label;
```

The API's accepted route labels are the values in `src/foundation/router/model/label.py`:

```text
anatomy
biological_process
disease
drug
effect_phenotype
exposure
gene_protein
molecular_function
pathway
```

```cypher
UNWIND [
  'anatomy', 'biological_process', 'disease', 'drug',
  'effect_phenotype', 'exposure', 'gene_protein',
  'molecular_function', 'pathway'
] AS label
CALL {
  WITH label
  MATCH (n)
  WHERE label IN labels(n)
  RETURN count(n) AS count
}
RETURN label, count
ORDER BY count DESC;
```

### Valid node IDs, names, and indexes

```cypher
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND n.node_name IS NOT NULL
  AND (n.is_hidden IS NULL OR NOT n.is_hidden)
RETURN labels(n) AS labels,
       n.node_id AS node_id,
       n.node_name AS node_name,
       n.node_index AS node_index
ORDER BY labels[0], n.node_name
LIMIT 50;
```

### A connected pair for path/reachability

This produces values suitable for `/graph/relationship`, `/graph/path`, `/graph/reachability`, and `/graph/facts`.

```cypher
MATCH (a)-[r]-(b)
WHERE a.node_id IS NOT NULL
  AND b.node_id IS NOT NULL
  AND a.node_id <> b.node_id
RETURN a.node_id AS start_id,
       a.node_name AS start_name,
       labels(a) AS start_labels,
       b.node_id AS end_id,
       b.node_name AS end_name,
       labels(b) AS end_labels,
       type(r) AS relationship
LIMIT 25;
```

For a start node with a stable name for `/node/find/{node_value}`:

```cypher
MATCH (n:drug)
WHERE n.node_name IS NOT NULL
  AND n.node_id IS NOT NULL
RETURN n.node_id AS node_id, n.node_name AS node_value, n.node_index AS node_index
ORDER BY n.node_name
LIMIT 25;
```

For details requests, use the `node_id` column from either query:

```cypher
MATCH (n)
WHERE n.node_id IS NOT NULL
RETURN collect(n.node_id)[0..10] AS node_ids;
```

## API contracts and execution flows

### 1. `GET /graph/relationship/start/{start_id}`

Router: `src/foundation/router/n_hop_router.py`, `find_n_hop()`.

Flow:

```text
router → FoundationalNHopProvider.find_subgraph_by_start_id_and_end_id
       → Neo4jFoundationalNHopAdapter.collect_by_start_id_and_end_id
       → GraphMapper.map
       → Graph response
```

Provider wiring is in `src/foundation/conf/conf.py`.

Parameters:

- Path `start_id`: string; `validate_id`; rejects `%`, `$`, `;`, `:`, `^`, `*`.
- Query `end_id`: optional string; same ID validation.
- Query `n_hop`: optional integer, default `1`, range `1..2`.

Underlying query shape:

```cypher
MATCH (startNode { node_id: $start_id })-[r]-{0,2}(endNode)
UNWIND(r) AS rel
RETURN DISTINCT startNode(rel).node_name AS startName,
  toStringOrNull(startNode(rel).node_id) AS startId,
  labels(startNode(rel)) AS startLabels,
  endNode(rel).node_name AS endName,
  toStringOrNull(endNode(rel).node_id) AS endId,
  labels(endNode(rel)) AS endLabels,
  type(rel) AS relType
ORDER BY startName
SKIP $offset LIMIT $limit
```

When `end_id` is supplied, the end pattern is `endNode { node_id: $end_id }`. The adapter actually supports pagination internally, but this route does not expose `page` or `page_size`, so provider defaults are used.

Swagger request:

```text
GET /graph/relationship/start/DB00846?n_hop=1
GET /graph/relationship/start/DB00846?end_id=DB00538&n_hop=2
```

Typical response shape:

```json
{
  "node_count": 2,
  "nodes": [
    {"id": "DB00846", "name": "Example drug", "labels": ["drug"]},
    {"id": "D000001", "name": "Example disease", "labels": ["disease"]}
  ],
  "relationships": {
    "indication": [
      {"start_id": "DB00846", "end_id": "D000001", "type": "indication"}
    ]
  }
}
```

The precise node/relationship fields are defined by `src/foundation/model/graph/` and `GraphMapper`; an empty or absent match can produce an empty/null graph depending on mapper behavior.

### 2. `GET /graph/path/start/{start_id}/end/{end_id}`

Router: `src/foundation/router/search_path_router.py`, `find_search_paths_by_start_id_and_end_id()`.

Flow:

```text
router → FoundationalPathProvider.find_shortest_path_by_start_id_and_end_id
       → Neo4jFoundationalPathAdapter.find_shortest_path_by_start_id_and_end_id
       → ShortestPaths response model
```

Parameters:

- Path `start_id`: string, `validate_id`.
- Path `end_id`: string, `validate_id`.
- Query `n_hop`: required integer, `1..4`.

Adapter query:

```cypher
MATCH path = SHORTEST 10
(startNode { node_id: $start_id })-[link]-{0,$n_hop}(endNode { node_id: $end_id })
RETURN [n IN nodes(path) | n.node_id] AS paths
```

Swagger request:

```text
GET /graph/path/start/DB00846/end/DB00538?n_hop=2
```

Response:

```json
{
  "start_id": "DB00846",
  "end_id": "DB00538",
  "max_hop": 2,
  "count": 1,
  "paths": [["DB00846", "D000001", "DB00538"]]
}
```

No path is represented by `count: 0` and `paths: []`.

### 3. `GET /graph/reachability/start/{start_id}/end/{end_id}`

Router: `src/foundation/router/search_path_router.py`, `find_is_reachable_by_start_id_and_end_id()`.

Flow:

```text
router → FoundationalPathProvider.find_is_reachable_by_start_id_and_end_id
       → Neo4jFoundationalPathAdapter.find_is_reachable_by_start_id_and_end_id
       → Reachability response model
```

Parameters are the same as `/graph/path`; `n_hop` is required and ranges `1..4`.

Adapter query:

```cypher
MATCH path = ANY
(startNode { node_id: $start_id })-[link]-{0,$n_hop}(endNode { node_id: $end_id })
RETURN toBoolean(count(path)) AS is_reachable
```

Swagger request:

```text
GET /graph/reachability/start/DB00846/end/DB00538?n_hop=2
```

Response:

```json
{
  "start_id": "DB00846",
  "end_id": "DB00538",
  "max_hop": 2,
  "is_reachable": true
}
```

### 4. `GET /graph/facts/start/{start_id}`

Router: `src/foundation/router/facts_router.py`, `find_n_hop()`.

Flow:

```text
router → FoundationalFactsOrchestrator.find_facts_by_start_id
       → FoundationalNHopProvider.find_subgraph_by_start_id_and_end_id
       → Neo4jFoundationalNHopAdapter.collect_by_start_id_and_end_id
       → FactsMapper.map
       → ListResponse
```

Parameters:

- Path `start_id`: string, `validate_id`.
- Query `page`: required integer, `> 0`.
- Query `page_size`: required integer, `1..50`.

The route hard-codes `n_hop=1`; there is no active `n_hop` query parameter.

Adapter query shape:

```cypher
MATCH (startNode { node_id: $start_id })-[r]-{0,1}(endNode)
UNWIND(r) AS rel
RETURN DISTINCT startNode(rel).node_name AS startName,
  toStringOrNull(startNode(rel).node_id) AS startId,
  labels(startNode(rel)) AS startLabels,
  endNode(rel).node_name AS endName,
  toStringOrNull(endNode(rel).node_id) AS endId,
  labels(endNode(rel)) AS endLabels,
  type(rel) AS relType
ORDER BY startName
SKIP $offset LIMIT $limit
```

`FactsMapper` converts graph edges into natural-language strings.

Swagger request:

```text
GET /graph/facts/start/DB00846?page=1&page_size=10
```

Response:

```json
{
  "count": 2,
  "results": [
    "Example drug has indication relationship with Example disease",
    "Example drug targets Example protein"
  ]
}
```

The exact wording comes from `src/foundation/mapper/facts_mapper.py`.

### 5. `GET /node/find/{node_value}`

Router: `src/foundation/router/node_id_lookup_router.py`, `lookup_node_id_by_value()`.

Flow:

```text
router → FoundationalNodeIdProvider.find_node_id_by_node_name
       → Neo4jFoundationalNodeAdapter.find_node_id_by_node_name
       → NodeIdLookupMapper.map
       → NodeIdLookup response
```

Parameters:

- Path `node_value`: string, maximum 2048 characters; `validate_value` rejects `%`, `_`, `$`, `;`, `:`, `^`, `*`.
- Query `fuzzy_match`: optional boolean, default `false`.

Exact lookup query:

```cypher
CALL db.index.fulltext.queryNodes('entity_names', $phrase_query)
YIELD node AS n, score
WHERE (n.is_hidden IS NULL OR NOT n.is_hidden)
  AND toLower(n.node_name) = toLower($node_name)
RETURN n.node_id, n.node_name
ORDER BY score DESC
```

Fuzzy lookup query:

```cypher
CALL db.index.fulltext.queryNodes('entity_names', $fuzzy_query)
YIELD node AS n, score
WHERE n.is_hidden IS NULL OR NOT n.is_hidden
RETURN n.node_id, n.node_name
ORDER BY score DESC
LIMIT 25
```

The `entity_names` full-text index must exist.

Swagger requests:

```text
GET /node/find/Example%20drug?fuzzy_match=false
GET /node/find/rituximab?fuzzy_match=true
```

Typical response shape:

```json
{
  "query": "Example drug",
  "count": 1,
  "fuzzy_match": false,
  "results": [
    {"id": "DB00846", "name": "Example drug"}
  ]
}
```

### 6. `POST /node/details`

Router: `src/foundation/router/node_details_router.py`, `lookup_node_details_by_id()`.

Flow:

```text
router → FoundationalNodeDetailsProvider.find_node_details_by_node_ids
       → Neo4jFoundationalNodeDetailsAdapter.find_node_details_by_node_ids
       → NodeDetailsMapper.map
       → GenericNodeDetails list
```

Request model: `src/foundation/router/model/node_details_request.py`.

Body:

```json
{"ids": ["DB00846", "D000001"]}
```

Rules:

- `ids` is a list of strings.
- Maximum 50 IDs, enforced by both request validation and adapter limit.
- Each ID is checked by `validate_id`.
- Empty IDs return no details rather than a useful result.

Adapter query:

```cypher
MATCH (n)
WHERE (n.is_hidden IS NULL OR NOT n.is_hidden)
  AND n.node_id IN $node_ids
RETURN labels(n) AS labels,
       n.node_id AS id,
       n.node_name AS value,
       n.node_source AS source,
       n.description AS description
```

Swagger request:

```text
POST /node/details
Content-Type: application/json
```

```json
{"ids": ["DB00846", "D000001"]}
```

Response:

```json
[
  {
    "labels": ["drug"],
    "id": "DB00846",
    "value": "Example drug",
    "source": "DrugBank",
    "description": "..."
  }
]
```

### 7. `GET /labels/{label}`

Router: `src/foundation/router/label_router.py`, `list_by_label()`.

Flow:

```text
router → Neo4jFoundationalNodeAdapter.find_by_label
       → _build_find_by_label / Neo4j query
       → to_id_list_response
       → NameAndIdListResponse
```

Parameters:

- Path `label`: one of the nine `Label` enum values.
- Query `page`: required integer, `> 0`.
- Query `page_size`: required integer, `1..50`.

Query:

```cypher
MATCH (n:`{label}`)
RETURN n.node_id AS node_id, n.node_name AS node_name
ORDER BY n.node_name
SKIP {offset}
LIMIT {limit}
```

Swagger request:

```text
GET /labels/drug?page=1&page_size=25
```

Response:

```json
{
  "count": 25,
  "results": [
    {"name": "Aspirin", "id": "DB00945"},
    {"name": "Example drug", "id": "DB00846"}
  ]
}
```

### 8. `GET /count/{label}`

Router: `src/foundation/router/count_router.py`, `count_by_label()`.

Flow:

```text
router → Neo4jFoundationalNodeCountAdapter.count_all_by_label
       → MATCH (n:`{label}`) RETURN count(n)
       → {count, label}
```

Parameters:

- Path `label`: same nine accepted labels.
- No query parameters.

Query:

```cypher
MATCH (n:`{label}`)
RETURN count(n) AS count
```

Swagger request:

```text
GET /count/drug
```

Response:

```json
{"count": 12345, "label": "drug"}
```

### 9. `POST /facet/{label}`

Router: `src/foundation/router/facet_router.py`, `collect_facets_by_label_and_values()`.

Flow:

```text
router → Neo4jFoundationalFacetAdapter.collect_facet_by_label
       → APOC facet Cypher
       → JSON blob returned by Neo4j
```

Path parameter:

- `label` is accepted by the general validator but the adapter supports only `drug` and `disease`.

Body model: `FacetSearchValues`.

```json
{"values": ["Lupus", "Aspirin"]}
```

`values` can be an empty list to aggregate all nodes of the selected supported label, but this can be expensive. Validation rejects values containing `%`, `_`, `$`, `;`, `:`, `^`, or `*` when the model validator is applied.

Drug query shape:

```cypher
MATCH (node:drug)
WHERE node.node_name =~ '(?i).*Lupus.*'
   OR node.node_name =~ '(?i).*Aspirin.*'
WITH apoc.map.merge(properties(node), {
  nodeId: id(node),
  indications: [(node)-[:indication]-(x:disease) | properties(x)],
  contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
  offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
}) AS node
...
RETURN {facets: {
  indications: indications,
  contraindications: contraindications,
  offLabelUses: offLabelUses
}} AS json
```

Disease query returns `drugs` and `geneProteins` frequency maps instead.

Swagger request:

```text
POST /facet/drug
Content-Type: application/json
```

```json
{"values": ["Aspirin"]}
```

Typical response:

```json
{
  "facets": {
    "indications": {"Pain": 1},
    "contraindications": {"Bleeding disorder": 1},
    "offLabelUses": {}
  }
}
```

Facet queries require APOC. The adapter currently interpolates search values into regex Cypher; this is a known implementation/security risk despite route validation.

### 10. `POST /similarity/{label}`

Router: `src/foundation/router/similarity_router.py`, `calculate_similarity_by_label_and_values()`.

Flow:

```text
router → Neo4jFoundationalSimilarityAdapter.calculate_similar_by_label_and_values
       → GDS nodeSimilarity.filtered.stream
       → to_similarity_response
       → SimilarityResponse
```

Path parameter:

- General label validation runs, but the adapter supports only `drug` and `disease`.

Body model: `SimilaritySearchValues`.

```json
{"values": ["Lupus"]}
```

Query shape:

```cypher
MATCH (d1:`drug`)
WHERE d1.node_name =~ '(?i).*Lupus.*'
CALL gds.nodeSimilarity.filtered.stream('similarity_graph', {
  degreeCutoff: 1,
  similarityCutoff: .45,
  similarityMetric: "COSINE",
  sourceNodeFilter: [d1]
})
YIELD node1, node2, similarity
RETURN similarity,
  gds.util.asNode(node1).node_name AS name1,
  gds.util.asNode(node2).node_name AS name2,
  toStringOrNull(gds.util.asNode(node1).node_id) AS id1,
  toStringOrNull(gds.util.asNode(node2).node_id) AS id2
ORDER BY similarity DESCENDING, name1, name2
```

The projection name is `SIMILARITY_GRAPH_PROJECTION_NAME` from `src/foundation/conf/const.py`; verify its value before testing. The projection must already exist in GDS.

Swagger request:

```text
POST /similarity/drug
Content-Type: application/json
```

```json
{"values": ["Lupus"]}
```

Response:

```json
{
  "count": 1,
  "results": [
    {
      "score": 0.73,
      "id1": "DB00846",
      "name1": "Example drug",
      "id2": "DB00538",
      "name2": "Related drug"
    }
  ]
}
```

Similarity requires the Neo4j GDS plugin and a populated named projection. Like facet, the adapter interpolates values into regex Cypher; route validation reduces but does not eliminate this risk.

## Supported labels and properties

The routes `/labels/{label}` and `/count/{label}` accept exactly:

```text
anatomy, biological_process, disease, drug, effect_phenotype,
exposure, gene_protein, molecular_function, pathway
```

`FoundationalNodeEnum` contains additional graph labels such as clinical trials, patents, research documents, and summaries, but they are not accepted by the public `Label` route enum.

Expected properties vary by dataset, but these APIs depend on:

- `node_id`: primary application identifier used by graph/path/facts/details.
- `node_name`: display value used by labels, lookup, graph mapping, and facet/similarity.
- `node_index`: used by many broader graph/entity-linking workflows, but not required by every query in this guide.
- Neo4j labels: required for label/count and supported facet/similarity types.
- `is_hidden`: optional; hidden nodes are excluded by lookup/details queries.
- `description`, `node_source`: returned by node details when present.

## Common failures

- `422 Unprocessable Entity`: missing required query parameters, invalid `n_hop`, page outside its range, malformed body, or invalid path characters.
- `400/422 invalid label`: label is not one of the nine public `Label` values.
- Facet/similarity `ValueError`: label is valid generally but not `drug` or `disease`.
- Empty graph/path/results: the `node_id` does not exist, is hidden, has no relationship, or the pair is not connected within the requested hop limit.
- Neo4j connection failure: `NEO4J_URI`, credentials, network route, or database availability is wrong.
- Missing `entity_names` index: `/node/find` fails or returns no results. Inspect with `SHOW FULLTEXT INDEXES`.
- Missing APOC: facet queries fail because of `apoc.map.merge`, `apoc.coll.flatten`, or `apoc.coll.frequenciesAsMap`.
- Missing GDS projection/plugin: similarity fails at `gds.nodeSimilarity.filtered.stream`.
- Large result/timeout: n-hop traversals expand quickly; keep relationship queries at one hop and use small page sizes.
- No details for a valid-looking identifier: the API uses `node_id`, not `node_index` and not Neo4j internal `id(n)`.

## Quick Swagger test sequence

1. Run the connected-pair discovery query and copy `start_id` and `end_id`.
2. Run `/graph/relationship` with `n_hop=1`.
3. Run `/graph/path` and `/graph/reachability` with the same pair and `n_hop=2`.
4. Run `/graph/facts` with the copied `start_id`, `page=1`, `page_size=10`.
5. Run the node-name discovery query and call `/node/find/{node_value}`.
6. Copy one or more returned `node_id` values into `/node/details`.
7. Call `/labels/drug?page=1&page_size=10` and `/count/drug`.
8. Call `/facet/drug` with a returned drug name.
9. Call `/similarity/drug` with the same name after verifying the GDS projection.

## Postman equivalents

Set a collection variable:

```text
baseUrl = http://localhost:18000
startId = <value from connected-pair query>
endId = <value from connected-pair query>
nodeValue = <value from node-name query>
```

Requests:

```text
GET {{baseUrl}}/graph/relationship/start/{{startId}}?n_hop=1
GET {{baseUrl}}/graph/path/start/{{startId}}/end/{{endId}}?n_hop=2
GET {{baseUrl}}/graph/reachability/start/{{startId}}/end/{{endId}}?n_hop=2
GET {{baseUrl}}/graph/facts/start/{{startId}}?page=1&page_size=10
GET {{baseUrl}}/node/find/{{nodeValue}}?fuzzy_match=false
POST {{baseUrl}}/node/details       body: {"ids":["{{startId}}","{{endId}}"]}
GET {{baseUrl}}/labels/drug?page=1&page_size=10
GET {{baseUrl}}/count/drug
POST {{baseUrl}}/facet/drug          body: {"values":["Aspirin"]}
POST {{baseUrl}}/similarity/drug     body: {"values":["Aspirin"]}
```

For any returned API error, first rerun the discovery Cypher and confirm that the copied value is the property the endpoint expects: `node_id` for graph traversal/details, `node_name` for lookup/facet/similarity, and a public enum label for label/count/facet/similarity.
