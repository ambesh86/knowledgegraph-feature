# Eugene — Neo4j Cypher Query Catalog

This document gathers every Cypher query embedded in the Eugene codebase into one
place, grouped by domain/adapter. For each query you get: the Python method that
runs it, the source file, a plain-English description of what it does, and the
exact Cypher (with interpolation placeholders shown as they appear in the code).

> **How Cypher runs in Eugene:** queries live inside Neo4j adapter classes under
> `src/**/infra/db/`. They are executed by the **Core API** service (`eugene_ws`,
> host port 18000) against the **neo4j** container over Bolt (`bolt://neo4j:7687`).
> Other services (MCP, agent) reach these queries indirectly via the Core API's
> REST endpoints — they do not run Cypher themselves.

> **Note on dynamic queries:** many adapters build Cypher by interpolating node
> labels, relationship types, or filter values via Python `%`/f-string formatting
> and `itertools.chain` fragment joining. Such queries are reproduced as templates
> with their `%s` / `{...}` / `$param` placeholders intact.

---

## Foundation domain — core graph traversal, nodes, facets, similarity, patents & pubmed

### `_upsert_drug_aliases` — src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py
**What it does:** Builds the search/anchor portion of the drug-alias upsert by optionally matching a drug node by its DrugBank id, then concatenates per-alias MERGE upserts and a final RETURN. The label is interpolated from the normalized DRUG node label.

**Cypher:**
```cypher
OPTIONAL MATCH (drug:%s { node_id: $drug_bank_id })
```
The `%s` is interpolated with `normalize_node_label(FoundationalNodeEnum.DRUG.value[1])`. This snippet is joined with the generated alias upserts and a trailing `RETURN drug.node_id`.

### `_generate_product_name_upserts` — src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py
**What it does:** Generates one MERGE upsert per product-name alias, creating/refreshing a drug-product node and linking it to the drug via a HAS_DRUG_ALIAS relationship. Node label, parameter placeholders, and relationship type are interpolated.

**Cypher:**
```cypher
WITH drug
            MERGE (product:`%s` { node_id: %s })
            ON MATCH
                SET product.refresh_date = datetime()
            ON CREATE
                SET product.refresh_date = datetime(),
                    product.node_id = %s,
                    product.drug_bank_id = %s,
                    product.node_name = %s
            MERGE (drug)-[r1:`%s`]-(product)
```
Interpolations in order: `normalize_node_label(FoundationalNodeEnum.DRUG_PRODUCT.value[1])`, `$drug_bank_id`, `$product{count}_node_id`, `$product{count}_drug_bank_id`, `$product{count}_node_name`, `FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1]`.

### `_generate_synonyms_upserts` — src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py
**What it does:** Generates one MERGE upsert per synonym alias, creating/refreshing a drug-synonym node and linking it to the drug via a HAS_DRUG_ALIAS relationship. Node label, parameter placeholders, and relationship type are interpolated.

**Cypher:**
```cypher
WITH drug
            MERGE (synonym:`%s` { node_id: %s })
            ON MATCH
                SET synonym.refresh_date = datetime()
            ON CREATE
                SET synonym.refresh_date = datetime(),
                    synonym.node_id = %s,
                    synonym.drug_bank_id = %s,
                    synonym.node_name = %s
            MERGE (drug)-[r1:`%s`]-(synonym)
```
Interpolations in order: `normalize_node_label(FoundationalNodeEnum.DRUG_SYNONYM.value[1])`, `$drug_bank_id`, `$synonym{count}_node_id`, `$synonym{count}_drug_bank_id`, `$synonym{count}_node_name`, `FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1]`.

### `_generate_drug_alias_search` — src/foundation/infra/db/adapter/neo4j_drug_aliases_adapter.py
**What it does:** Builds the drug-alias lookup query: matches a starting node by a caller-supplied WHERE clause, traverses the HAS_DRUG_ALIAS subgraph via APOC, and returns distinct alias names, node ids, drug bank ids, and whether each is the canonical drug. The match clause and relationship filter are interpolated.

**Cypher:**
```cypher
MATCH (n)
        %s AND (n.is_hidden IS NULL OR NOT n.is_hidden)
        CALL apoc.path.subgraphNodes([n], {relationshipFilter: "%s"}) YIELD node
        RETURN DISTINCT node.node_name as name, toStringOrNull(node.node_id) as node_id, 
            toStringOrNull(node.drug_bank_id) as drug_bank_id, toBoolean("drug" in labels(node)) as is_canonical
```
First `%s` is the `match_clause`, which is one of: `WHERE n.node_name =~ '(?i).*{fuzzy_match_term}.*'` (fuzzy, value interpolated), `WHERE n.node_name = $drug_name` (by name), or `WHERE n.node_id = $drug_id` (by id). Second `%s` is `FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1]`.

### `_build_facet_by_label_query` (DRUG branch) — src/foundation/infra/db/adapter/neo4j_foundational_facet_adapter.py
**What it does:** Builds and returns the facet-count query for drug nodes, aggregating frequency maps of related indications, contraindications, and off-label-use disease names across matched drug nodes. The matched label and optional regex WHERE filters are interpolated (flagged as a Cypher-injection risk in code).

**Cypher:**
```cypher
MATCH (node:`{normalized_node_label}`)
{optional_where_clause}

                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    indications: [(node)-[:indication]-(x:disease) | properties(x)],
                    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
                    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                    [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
                    [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
                    [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses,
                    [x in apoc.coll.flatten(collect(node.indicationCount)) | x.node_name] as indicationCount,
                    [x in apoc.coll.flatten(collect(node.contraindicationCount)) | x.node_name] as contraindicationCount,
                    [x in apoc.coll.flatten(collect(node.offLabelCount)) | x] as offLabelCount
                WITH nodes,
                    apoc.coll.frequenciesAsMap(indications) as indications,
                    apoc.coll.frequenciesAsMap(contraindications) as contraindications,
                    apoc.coll.frequenciesAsMap(offLabelUses) as offLabelUses
                RETURN {
                    facets: {
                        indications: indications,
                        contraindications: contraindications,
                        offLabelUses: offLabelUses
                    }
                } as json
```
The match line interpolates `normalize_node_label(label.value[1])` (DRUG). The `optional_where_clause` is empty or `where node.node_name =~ '(?i).*{value}.*'` clauses joined by `or` (one per supplied value, value interpolated).

### `_build_facet_by_label_query` (DISEASE branch) — src/foundation/infra/db/adapter/neo4j_foundational_facet_adapter.py
**What it does:** Builds and returns the facet-count query for disease nodes, aggregating frequency maps of related drug and gene/protein names across matched disease nodes. The matched label and optional regex WHERE filters are interpolated.

**Cypher:**
```cypher
MATCH (node:`{normalized_node_label}`)
{optional_where_clause}

                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    drugs: [(node)-[]-(x:drug) | properties(x)],
                    geneProteins: [(node)-[]-(x:gene_protein) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                    [x in apoc.coll.flatten(collect(node.drugs)) | x.node_name] as drugs,
                    [x in apoc.coll.flatten(collect(node.geneProteins)) | x.node_name] as geneProteins,
                    [x in apoc.coll.flatten(collect(node.drugCount)) | x] as drugCount,
                    [x in apoc.coll.flatten(collect(node.geneProteinCount)) | x.node_name] as geneProteinCount
                WITH nodes,
                    apoc.coll.frequenciesAsMap(drugs) as drugs,
                    apoc.coll.frequenciesAsMap(geneProteins) as geneProteins
                RETURN {
                    facets: {
                        drugs: drugs,
                        geneProteins: geneProteins
                    }
                } as json
```
The match line interpolates `normalize_node_label(label.value[1])` (DISEASE). The `optional_where_clause` is empty or `where node.node_name =~ '(?i).*{value}.*'` clauses joined by `or` (one per supplied value, value interpolated).

### `_build_n_hop_by_value_query` — src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py
**What it does:** Builds a variable-length (0 to n_hop) relationship traversal between a start node (matched by node_name) and an optional end node (matched by node_name), returning distinct relationship endpoints. Hop count, optional end condition, and the shared RETURN snippet are interpolated.

**Cypher:**
```cypher
MATCH (startNode { node_name: $start_name })-[r]-{0,%s}(endNode%s)
            %s
```
First `%s` is `n_hop`; second `%s` is `{ node_name: $end_name }` when an end value is given (else empty); third `%s` is the snippet from `_gen_n_hop_snippet` (see entry below).

### `_build_n_hop_by_id_query` — src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py
**What it does:** Builds a variable-length (0 to n_hop) relationship traversal between a start node (matched by node_id) and an optional end node (matched by node_id), returning distinct relationship endpoints with pagination. Hop count, optional end condition, and the paginated RETURN snippet are interpolated.

**Cypher:**
```cypher
MATCH (startNode { node_id: $start_id })-[r]-{0,%s}(endNode%s)
            %s
```
First `%s` is `n_hop`; second `%s` is `{ node_id: $end_id }` when an end id is given (else empty); third `%s` is the paginated snippet from `_gen_n_hop_snippet(page, page_size)`.

### `_gen_n_hop_snippet` — src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py
**What it does:** Produces the shared RETURN tail of the n-hop queries: unwinds the relationship list and returns distinct start/end node names, ids, labels, and the relationship type, ordered and paginated. SKIP/LIMIT offset and limit are interpolated.

**Cypher:**
```cypher
UNWIND(r) AS rel
            RETURN DISTINCT startNode(rel).node_name as startName, toStringOrNull(startNode(rel).node_id) as startId, 
                labels(startNode(rel)) as startLabels, endNode(rel).node_name as endName, toStringOrNull(endNode(rel).node_id) as endId,  
                labels(endNode(rel)) as endLabels, type(rel) as relType
            ORDER BY startName
            SKIP %s
            LIMIT %s
```
First `%s` is `offset`, second `%s` is `limit`, both computed by `Pagination.calculate_limit_and_offset(page, page_size)`.

### `upsert_embeddings` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Upserts an embeddings vector onto a node identified by label and node_index, setting the embeddings property on match and returning the node_index. The node label is interpolated.

**Cypher:**
```cypher
MERGE (n:`%s` {
                node_index: $node_index
            })
            ON MATCH
                SET n.embeddings = $embeddings
            RETURN n.node_index
```
`%s` is interpolated with `normalize_node_label(label)`.

### `_build_find_all_by_label` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Builds a query that returns all nodes of a given label with their node_id and node_name, ordered by name. The label is interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
                RETURN n.node_id as node_id, n.node_name as node_name
                ORDER BY n.node_name
```
`%s` is interpolated with `normalize_node_label(label)`.

### `_build_find_by_label` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Builds a paginated query returning nodes of a given label with node_id and node_name, ordered by name with SKIP/LIMIT. Label, offset, and limit are interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
                RETURN n.node_id as node_id, n.node_name as node_name
                ORDER BY node_name
                SKIP %s
                LIMIT %s
```
Interpolations: `normalize_node_label(label)`, then `offset` and `limit` from `Pagination.calculate_limit_and_offset(page, page_size)`.

### `build_verify_exists_by_node_index` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Builds a query that checks whether a node with a given label and node_index exists, returning its node_index. The label is interpolated.

**Cypher:**
```cypher
MATCH (n: %s { node_index: $node_index })
            RETURN n.node_index
```
`%s` is interpolated with `normalize_node_label(label)` (stripped).

### `build_find_node_id_by_node_name` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Returns the node_id and node_name for a node matched exactly by node_name (excluding hidden nodes). Uses a bound parameter, no interpolation.

**Cypher:**
```cypher
MATCH (n { node_name: $node_name })
        WHERE n.is_hidden IS NULL OR NOT n.is_hidden
        RETURN n.node_id, n.node_name
```

### `build_fuzzy_find_node_id_by_node_name` — src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py
**What it does:** Returns node_id and node_name for nodes whose node_name fuzzily (case-insensitive regex) matches the supplied value, excluding hidden nodes. The search value is interpolated directly into the regex.

**Cypher:**
```cypher
MATCH (n)
        WHERE n.node_name =~ '(?i).*%s.*' and (n.is_hidden IS NULL OR NOT n.is_hidden)
        RETURN n.node_id, n.node_name
```
`%s` is interpolated with the raw `value`.

### `_build_count_all_by_label` — src/foundation/infra/db/adapter/neo4j_foundational_node_count_adapter.py
**What it does:** Builds a query counting all nodes of a given label, returning the count. The label is interpolated directly (note: normalization is commented out here).

**Cypher:**
```cypher
MATCH (n:`%s`)
            RETURN count(n) as count
```
`%s` is interpolated with the raw `label`.

### `_build_find_node_details_by_node_ids` — src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py
**What it does:** Returns generic details (labels, id, name, source, description) for non-hidden nodes whose node_id is in a supplied list. Uses a bound `$node_ids` parameter, no interpolation.

**Cypher:**
```cypher
MATCH (n)
        WHERE (n.is_hidden IS NULL OR NOT n.is_hidden) and n.node_id in $node_ids
        RETURN labels(n) as labels, n.node_id as id, n.node_name as value,
            n.node_source as source, n.description as description
```

### `_build_one_hop_by_label_query` (DRUG branch) — src/foundation/infra/db/adapter/neo4j_foundational_one_hop_adapter.py
**What it does:** Builds a one-hop relationship query for drug nodes matched by fuzzy name, returning lists of related indication, contraindication, and off-label-use disease names as JSON. The drug label and search value are interpolated (flagged as a Cypher-injection risk).

**Cypher:**
```cypher
MATCH (node:`%s`)
                WHERE node.node_name =~ '(?i).*%s.*'
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    indications: [(node)-[:indication]-(x:disease) | properties(x)],
                    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
                    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
                [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
                [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses
                RETURN {
                    relationships: {
                        indications: indications,
                        contraindications: contraindications,
                        offLabelUses: offLabelUses
                    }
                } as json
```
First `%s` is `normalize_node_label(label.value[1])` (DRUG); second `%s` is the raw search `value`.

### `_build_one_hop_by_label_query` (DISEASE branch) — src/foundation/infra/db/adapter/neo4j_foundational_one_hop_adapter.py
**What it does:** Builds a one-hop relationship query for disease nodes matched by fuzzy name, returning lists of related drug and gene/protein names as JSON. The disease label and search value are interpolated.

**Cypher:**
```cypher
MATCH (node:`%s`)
                WHERE node.node_name =~ '(?i).*%s.*'
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    drugs: [(node)-[]-(x:drug) | properties(x)],
                    geneProteins: [(node)-[]-(x:gene_protein) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                [x in apoc.coll.flatten(collect(node.drugs)) | x.node_name] as drugs,
                [x in apoc.coll.flatten(collect(node.geneProteins)) | x.node_name] as geneProteins
                RETURN {
                    relationships: {
                        drugs: drugs,
                        geneProteins: geneProteins
                    }
                } as json
```
First `%s` is `normalize_node_label(label.value[1])` (DISEASE); second `%s` is the raw search `value`.

### `_build_shortest_path_by_ids_query` — src/foundation/infra/db/adapter/neo4j_foundational_path_adapter.py
**What it does:** Builds a query finding the top-N shortest paths (up to n_hop links) between a start node and end node matched by node_id, returning each path as a list of node ids. The TOP_N count and hop count are interpolated.

**Cypher:**
```cypher
MATCH path = SHORTEST %s
        (startNode { node_id: $start_id })-[link]-{0,%s}(endNode { node_id: $end_id })
        RETURN [n in nodes(path) | n.node_id] AS paths
```
First `%s` is `Neo4jFoundationalPathAdapter.TOP_N` (10); second `%s` is `n_hop`.

### `_build_reachability_by_ids_query` — src/foundation/infra/db/adapter/neo4j_foundational_path_adapter.py
**What it does:** Builds a query testing whether any path (up to n_hop links) exists between a start and end node matched by node_id, returning a boolean reachability flag. The hop count is interpolated.

**Cypher:**
```cypher
MATCH path = ANY
        (startNode { node_id: $start_id })-[link]-{0,%s}(endNode { node_id: $end_id })
        RETURN toBoolean(count(path)) as is_reachable
```
`%s` is interpolated with `n_hop`.

### `_build_similarity_query_by_label_and_values` — src/foundation/infra/db/adapter/neo4j_foundational_similarity_adapter.py
**What it does:** Builds a GDS filtered node-similarity query: matches source nodes of a given label (optionally filtered by fuzzy name), then streams cosine-similar node pairs and returns names, ids, and similarity scores ordered descending. The label, optional WHERE filters, and GDS graph projection name are interpolated.

**Cypher:**
```cypher
MATCH (d1:`{normalized_node_label}`)
{optional_where_clause}

            CALL gds.nodeSimilarity.filtered.stream('%s', {
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
The match line interpolates `normalize_node_label(label.value[1])`. The `optional_where_clause` is empty or `WHERE d1.node_name =~ '(?i).*{value}.*'` clauses joined by `or` (one per value, value interpolated). The `%s` in the CALL interpolates `graph_name` (`SIMILARITY_GRAPH_PROJECTION_NAME`).

### `_build_find_all_embeddings_by_label` — src/foundation/infra/db/adapter/neo4j_list_embeddings_adapter.py
**What it does:** Builds a query that fetches all nodes of a given label and returns each node's index, name, and the requested embeddings field (either graph or sentence embeddings).

**Cypher:**
```cypher
MATCH (n:`%s`)
                RETURN n.node_index as node_index, n.node_name as node_name, n.%s as %s
```
*Interpolation: first `%s` is the normalized node label; the next two `%s` are the embeddings field name (e.g. `embeddings` or `graph_embeddings`), used as both the property accessed and the returned alias.*

### `_generate_cypher_template` — src/foundation/infra/db/adapter/neo4j_missing_node_index_embedding_adapter.py
**What it does:** Builds a query that finds nodes of the given labels that are missing a `node_index`, zeroes out their embeddings with the supplied default vector, and returns the count of updated nodes.

**Cypher:**
```cypher
MATCH (n:{labels})
        WHERE n.node_index IS NULL
        SET n.embeddings = $embeddings
        return count(n) as updated_node_count
```
*Interpolation: `{labels}` is the pipe-joined (`|`) list of node labels; `$embeddings` is bound to a zero vector of the embedding dimension.*

### `_generate_cypher_template` — src/foundation/infra/db/adapter/neo4j_onehot_encoding_adapter.py
**What it does:** Builds a query that computes a one-hot encoding of each node's label (against the complete set of node labels) using GDS, then writes it onto the node as a `label_one_hot_encoding` property via APOC, returning the updated node.

**Cypher:**
```cypher
MATCH (n1:`%s`)
            WITH n1, gds.alpha.ml.oneHotEncoding(
            {node_labels}
            , ['%s']) AS encoding
            CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
            YIELD node
            RETURN node;
```
*Interpolation: `{node_labels}` is the full Python list of node labels embedded in the f-string; the two `%s` placeholders are both filled with the normalized label being processed (the node match label and the selected encoding category).*

### `_generate_patent_ids_by_drug_id` — src/foundation/infra/db/adapter/neo4j_patent_export_adapter.py
**What it does:** Builds a paginated export query that matches drug nodes related to patent applications and returns the drug id, USPTO patent id, and patent filing date, ordered by drug node id.

**Cypher:**
```cypher
MATCH (ct:`%s`)-[r:`%s`]-(p:`%s`)
            RETURN ct.node_id as drug_id, p.patent_id as uspto_patent_id, date(p.filing_date) as filing_date
            ORDER BY ct.node_id
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `DRUG`, `DISCLOSED_IN` relationship, and `PATENT_APPLICATION`; the trailing `%s` placeholders are the computed pagination offset and limit.*

### `_generate_patent_ids_by_clinical_trials` — src/foundation/infra/db/adapter/neo4j_patent_export_adapter.py
**What it does:** Builds a paginated export query that matches clinical trial nodes related to patent applications and returns the nct id, USPTO patent id, and patent filing date, ordered by nct id.

**Cypher:**
```cypher
MATCH (ct:`%s`)-[r:`%s`]-(p:`%s`)
            RETURN ct.nct_id as nct_id, p.patent_id as uspto_patent_id, date(p.filing_date) as filing_date
            ORDER BY nct_id
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `CLINICAL_TRIAL`, `SUPPORTS_PATENT_APPLICATION` relationship, and `PATENT_APPLICATION`; the trailing `%s` placeholders are the computed pagination offset and limit.*

### `_generate_patent_search_by_drug` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a paginated query that finds patent applications related to a specific drug id and returns the drug id, drug name, and patent id, ordered by patent id descending.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN n.node_id as drug_id, n.node_name as drug_name, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `DRUG`, `DISCLOSED_IN` relationship, and `PATENT_APPLICATION`; trailing `%s` are pagination offset and limit; `$drug_id` is bound at runtime.*

### `_generate_patent_search_by_clinicaltrail` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a paginated query that finds patent applications related to a specific clinical trial (nct id) and returns the nct id and patent id, ordered by patent id descending.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.nct_id = $nct_id
            RETURN n.nct_id as nct_id, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `CLINICAL_TRIAL`, `SUPPORTS_PATENT_APPLICATION` relationship, and `PATENT_APPLICATION`; trailing `%s` are pagination offset and limit; `$nct_id` is bound at runtime.*

### `_generate_patent_search_by_gene` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a paginated query that finds patent applications related to a specific gene/protein by name and returns the node name and patent id, ordered by patent id descending.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN n.node_name as node_name, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `GENE_PROTEIN`, `PATENT_APP_TARGET` relationship, and `PATENT_APPLICATION`; trailing `%s` are pagination offset and limit; `$gene` is bound at runtime.*

### `_generate_patent_count_by_drug_id` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a query that counts the patent applications related to a specific drug id.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN count(n2) as count
```
*Interpolation: labels are `DRUG`, `DISCLOSED_IN` relationship, and `PATENT_APPLICATION`; `$drug_id` is bound at runtime.*

### `_generate_patent_count_by_clinicaltrail` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a query that counts the patent applications related to a specific clinical trial (nct id).

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.nct_id = $nct_id
            RETURN count(n2) as count
```
*Interpolation: labels are `CLINICAL_TRIAL`, `SUPPORTS_PATENT_APPLICATION` relationship, and `PATENT_APPLICATION`; `$nct_id` is bound at runtime.*

### `_generate_patent_count_by_gene` — src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py
**What it does:** Builds a query that counts the patent applications related to a specific gene/protein by name.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN count(n2) as count
```
*Interpolation: labels are `GENE_PROTEIN`, `PATENT_APP_TARGET` relationship, and `PATENT_APPLICATION`; `$gene` is bound at runtime.*

### `_generate_cypher_template` — src/foundation/infra/db/adapter/neo4j_project_similarity_graph_adapter.py
**What it does:** Builds a GDS Cypher projection that matches source nodes and their optionally-related target nodes over the given relationship types and projects a named in-memory graph carrying a `strength` relationship property, used for similarity queries.

**Cypher:**
```cypher
MATCH (source:%s)
            OPTIONAL MATCH (source)-[r:%s]-(target:%s)
            RETURN gds.graph.project(
                '%s',
                source,
                target,
                { 
                    relationshipProperties: r { strength: 1 } 
                }
            )
```
*Interpolation: first `%s` is the pipe-joined normalized source node labels; second `%s` is the pipe-joined backtick-escaped relationship labels; third `%s` is the pipe-joined normalized target node labels; fourth `%s` is the projection graph name.*

### `_generate_pubmed_count_by_drug_id` — src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py
**What it does:** Builds a query that counts research (PubMed) nodes related to a specific drug id.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN count(n2) as count
```
*Interpolation: labels are `DRUG`, `FEATURED_IN` relationship, and `RESEARCH`; `$drug_id` is bound at runtime.*

### `_generate_pubmed_count_by_clinicaltrail` — src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py
**What it does:** Builds a query that, starting from a clinical trial, traverses to its related drug or gene/protein nodes, then optionally to research nodes, and counts the distinct PubMed pmids reachable.

**Cypher:**
```cypher
MATCH (start:`%s`)-[r]-(target:`%s`|`%s`)
            WHERE start.nct_id = $nct_id
            OPTIONAL MATCH (target)-[r2]-(end:`%s`)
            RETURN count(end.pmid) as count
```
*Interpolation: labels are `CLINICAL_TRIAL` (start), `DRUG` and `GENE_PROTEIN` (target alternatives), and `RESEARCH` (end); `$nct_id` is bound at runtime.*

### `_generate_pubmed_count_by_gene` — src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py
**What it does:** Builds a query that counts research (PubMed) nodes related to a specific gene/protein by name.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN count(n2) as count
```
*Interpolation: labels are `GENE_PROTEIN`, `ANALYZED_IN` relationship, and `RESEARCH`; `$gene` is bound at runtime.*

### `_generate_pubmed_search_by_drug` — src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py
**What it does:** Builds a paginated query that finds research (PubMed) nodes related to a specific drug id and returns the drug id, drug name, and pmid, ordered by pmid descending.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN n.node_id as drug_id, n.node_name as drug_name, n2.pmid as pmid
            ORDER BY pmid DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `DRUG`, `FEATURED_IN` relationship, and `RESEARCH`; trailing `%s` are pagination offset and limit; `$drug_id` is bound at runtime.*

### `_generate_pubmed_search_by_clinicaltrail` — src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py
**What it does:** Builds a paginated query that starts from a clinical trial, traverses to related drug or gene/protein nodes, then optionally to research nodes, returning nct id, target id, and pmid.

**Cypher:**
```cypher
MATCH (start:`%s`)-[r]-(target:`%s`|`%s`)
            WHERE start.nct_id = $nct_id
            OPTIONAL MATCH (target)-[r2]-(end:`%s`)
            RETURN start.nct_id as nct_id, target.node_id as target_id, end.pmid as pmid
            ORDER BY nct_id, target_id, pmid DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `CLINICAL_TRIAL` (start), `DRUG` and `GENE_PROTEIN` (target alternatives), and `RESEARCH` (end); trailing `%s` are pagination offset and limit; `$nct_id` is bound at runtime.*

### `_generate_pubmed_search_by_gene` — src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py
**What it does:** Builds a paginated query that finds research (PubMed) nodes related to a specific gene/protein by name and returns the node name and pmid, ordered by pmid descending.

**Cypher:**
```cypher
MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN n.node_name as node_name, n2.pmid as pmid
            ORDER BY pmid DESC
            SKIP %s
            LIMIT %s
```
*Interpolation: labels are `GENE_PROTEIN`, `ANALYZED_IN` relationship, and `RESEARCH`; trailing `%s` are pagination offset and limit; `$gene` is bound at runtime.*

### `_generate_cypher_template` — src/foundation/infra/db/adapter/neo4j_train_embeddings_adapter.py
**What it does:** Builds a GDS FastRP call that trains graph embeddings on a named projected graph and writes them to a node property, yielding the number of node properties written.

**Cypher:**
```cypher
call gds.fastRP.write(
            '%s',
            {
                embeddingDimension: %s,
                writeProperty: '%s',
                iterationWeights: [0, .6, .8],
                normalizationStrength: -0.5,
                randomSeed: 75,
                featureProperties: %s,
                propertyRatio: .50
            }
            )
            yield nodePropertiesWritten
```
*Interpolation: first `%s` is the projection graph name; second `%s` is the embedding dimension; third `%s` is the write property (default `prediction_embeddings`); fourth `%s` is the Python list of feature properties (default `['embeddings', 'label_one_hot_encoding']`).*

### `_generate_create_index_cypher` — src/foundation/infra/db/adapter/neo4j_train_embeddings_adapter.py
**What it does:** Builds a statement that creates (if not already present) a cosine-similarity vector index over a given node label and property, with the configured number of vector dimensions.

**Cypher:**
```cypher
CREATE VECTOR INDEX %s_%s_index IF NOT EXISTS
            FOR (n:%s)
            ON n.%s
            OPTIONS { indexConfig: {
                `vector.dimensions`: %s,
                `vector.similarity_function`: 'cosine'
            }
        }
```
*Interpolation: `%s` placeholders are, in order, node label and property name (forming the index name), node label (FOR clause), property name (ON clause), and the embeddings dimension (default 512).*


---

## Patent & PubMed domain — applications, PGPubs, articles, affiliations, summaries

### `_upsert` — src/patent/application/infra/db/neo4j_application_adapter.py
**What it does:** Upserts a USPTO application node keyed by application_number_text, setting title/applicant/status/classification metadata, and (when a patent_number is present) links it to the matching patent node; returns the application_number_text and refresh_date.

**Cypher:**
```cypher
MERGE (application:`%s` {
    application_number_text: $application_number_text
})
ON MATCH
    SET application.invention_title = $invention_title,
        application.first_applicant_name = $first_applicant_name,
        application.refresh_date = datetime(),
        application.applicants = $applicants,
        application.application_status_description_text = $application_status_description_text,
        application.application_status_code = $application_status_code,
        application.customer_number = $customer_number,
        application.application_type_code = $application_type_code,
        application.application_type_label_name = $application_type_label_name,
        application.cpc_classifications = $cpc_classifications,
        application.application_status_date = $application_status_date,
        application.effective_filing_date = $effective_filing_date,
        application.filing_date = $filing_date,
        application.patent_number = $patent_number,
        application.grant_date = $grant_date
ON CREATE
    SET application.invention_title = $invention_title,
        application.first_applicant_name = $first_applicant_name,
        application.refresh_date = datetime(),
        application.applicants = $applicants,
        application.application_status_description_text = $application_status_description_text,
        application.application_status_code = $application_status_code,
        application.customer_number = $customer_number,
        application.application_type_code = $application_type_code,
        application.application_type_label_name = $application_type_label_name,
        application.cpc_classifications = $cpc_classifications,
        application.application_status_date = $application_status_date,
        application.effective_filing_date = $effective_filing_date,
        application.filing_date = $filing_date,
        application.patent_number = $patent_number,
        application.grant_date = $grant_date,
        application.is_uspto = true

WITH application
MATCH (patent:patent { patent_no: $patent_number })
MERGE (patent)-[r1:`%s` { is_uspto: true }]-(application)

RETURN application.application_number_text, application.refresh_date
```
*The query is assembled dynamically: `%s` in the MERGE node is `USPTO_APPLICATION_NODE_TYPE`; the `WITH application ... MATCH (patent ...) MERGE ...` block (with `%s` = `USPTO_APPLICATION_PATENT_REL_TYPE`) is only appended when `application.patent_number` is not None and > 0; the trailing `RETURN` line is always concatenated.*

### `_upsert` — src/patent/pgpub/infra/db/adapter/neo4j_pgpub_adapter.py
**What it does:** Upserts a USPTO PGPub (pre-grant publication) node keyed by application_number_text with file metadata, abstract, description, claims, organizations, chemical synonyms, and embeddings, and (when application_number_text > 0) links it to the matching application node; returns application_number_text and refresh_date.

**Cypher:**
```cypher
MERGE (pgpub:`%s` {
    application_number_text: $application_number_text
})
ON MATCH
    SET pgpub.file_location_uri = $file_location_uri,
        pgpub.file_create_dtg = $file_create_dtg,
        pgpub.refresh_date = datetime(),
        pgpub.abstract = $abstract,
        pgpub.description = $description,
        pgpub.claims = $claims,
        pgpub.organizations = $organizations,
        pgpub.chemical_compound_synonyms = $chemical_compound_synonyms,
        pgpub.embeddings = $embeddings
ON CREATE
    SET pgpub.file_location_uri = $file_location_uri,
        pgpub.file_create_dtg = $file_create_dtg,
        pgpub.refresh_date = datetime(),
        pgpub.abstract = $abstract,
        pgpub.description = $description,
        pgpub.claims = $claims,
        pgpub.organizations = $organizations,
        pgpub.chemical_compound_synonyms = $chemical_compound_synonyms,
        pgpub.embeddings = $embeddings,
        pgpub.is_uspto = true

WITH pgpub
MATCH (application:`%s` { application_number_text: $application_number_text })
ON MATCH
    SET application.refresh_date = datetime(),
ON CREATE
    SET application.refresh_date = datetime(),
        application.is_uspto = true
MERGE (application)-[r1:`%s` { is_uspto: true }]-(pgpub)

RETURN pgpub.application_number_text, pgpub.refresh_date
```
*The query is assembled dynamically: `%s` in the MERGE node is `USPTO_PGPUB_NODE_TYPE`; the `WITH pgpub ... MATCH (application ...) MERGE ...` block (`%s` = `USPTO_APPLICATION_NODE_TYPE` and `USPTO_PGPUB_PATENT_REL_TYPE`) is only appended when application_number_text is not None and int(application_number_text) > 0; the trailing `RETURN` line is always concatenated.*

### `_find_by_application_number` — src/patent/pgpub/infra/db/adapter/neo4j_pgpub_search_adapter.py
**What it does:** Looks up a single PGPub node by its application_number_text and returns that application number (aliased as patent_application_no), or nothing if not found.

**Cypher:**
```cypher
MATCH (node:`{USPTO_PGPUB_NODE_TYPE}`)
WHERE node.application_number_text = $application_number
RETURN node.application_number_text as patent_application_no
```
*This is an f-string where `{USPTO_PGPUB_NODE_TYPE}` is interpolated as the node label.*

### `_find_by_embeddings` / `_generate_find_by_embeddings_query` — src/patent/pgpub/infra/db/adapter/neo4j_pgpub_search_adapter.py
**What it does:** Performs a vector similarity search over the PGPub embeddings index for the supplied query embeddings (default top 200) and returns each matched node's application_number_text together with its similarity score.

**Cypher:**
```cypher
WITH $embeddings as query
CALL db.index.vector.queryNodes('%s', %s, query)
YIELD node, score

RETURN score, node.application_number_text as patent_application_no
```
*Built in `_generate_find_by_embeddings_query`: the first `%s` is `USPTO_PGPUB_EMBEDDINGS_INDEX_NAME` and the second `%s` is the `limit` (default 200). In `_find_by_embeddings` the `RETURN score, node.application_number_text as patent_application_no` line is concatenated onto the generated CALL block.*

### `_upsert_summary` — src/patent/pgpub/infra/db/adapter/neo4j_pgpub_summary_adapter.py
**What it does:** Matches an existing PGPub application node, upserts a summary node (title/summary/rating/level) linked to it, and upserts one finding node plus a relationship per finding in the summary; returns the application number, summary_id, and refresh_date.

**Cypher:**
```cypher
MATCH (application:`%s` { application_number_text: $application_number })
MERGE (summary:`%s` {
    summary_id: $summary_id
})
ON MATCH
    SET summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()
ON CREATE
    SET summary.summary_id = $summary_id,
        summary.is_uspto = true,
        summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()

MERGE (finding%s:`%s` { 
        finding_id: "%s",
        summary: "%s",
        explanation: "%s" 
}) 

MERGE (summary)-[rel%s:`%s` { is_uspto: true }]-(finding%s) 

MERGE (application)-[article_rel:`%s` { is_uspto: true }]-(summary)

RETURN application.application_number_text, summary.summary_id, summary.refresh_date
```
*Dynamically assembled. The MATCH/MERGE summary block uses `%s` = `USPTO_PGPUB_NODE_TYPE` and `USPTO_PGPUB_SUMMARY_NODE_TYPE`. For each finding in `summary.findings`, a `MERGE (finding<n>:...)` clause is appended where the placeholders are the finding counter, `USPTO_PGPUB_SUMMARY_FINDING_NODE_TYPE`, finding.id, finding.summary, and finding.explanation (values inlined into the query text, not parameterized). For each finding a matching `MERGE (summary)-[rel<n>:...]-(finding<n>)` is appended with `USPTO_PGPUB_SUMMARY_FINDING_REL_TYPE`. The `link_article_upsert` clause uses `USPTO_PGPUB_SUMMARY_REL_TYPE`, followed by the constant RETURN line.*

### `_upsert` — src/pubmed/infra/db/neo4j_affiliation_adapter.py
**What it does:** Matches a PubMed article (doc) by pmcid, upserts an affiliation node (location, emails) keyed by affiliation_id, and links the article to the affiliation; returns the pmcid, affiliation_id, and refresh_date.

**Cypher:**
```cypher
MATCH (doc:`%s` { pmcid: $pmcid })
MERGE (affiliation:`%s` {
    affiliation_id: $affiliation_id
})
ON MATCH
    SET affiliation.location = $location,
        affiliation.emails = $emails,
        affiliation.refresh_date = datetime()
ON CREATE
    SET affiliation.location = $location,
        affiliation.emails = $emails,
        affiliation.refresh_date = datetime(),
        affiliation.affiliation_id = $affiliation_id,
        affiliation.is_pubmed = true

MERGE (doc)-[article_rel:`%s` { is_pubmed: true }]-(affiliation)

RETURN doc.pmcid, affiliation.affiliation_id, affiliation.refresh_date
```
*Assembled from three pieces: the MATCH/MERGE block (`%s` = `PUBMED_ARTICLE_NODE_TYPE` and `PUBMED_ARTICLE_AFFILIATION_NODE_TYPE`), the link clause (`%s` = `PUBMED_ARTICLE_EXTRACTION_REL_TYPE`), and the constant RETURN line.*

### `_build_find_by_node_index_query` (via `_find_node_index`) — src/pubmed/infra/db/neo4j_article_adapter.py
**What it does:** Builds and runs a case-insensitive lookup of an entity node by its normalized label and node_name, returning that node's node_name and node_index.

**Cypher:**
```cypher
MATCH (n:`%s`)
        WHERE n.node_name =~ '(?i)%s'
        RETURN n.node_name, n.node_index
```
*The first `%s` is `normalize_node_label(entity_type)` and the second `%s` is `normalize_node_name(entity)`, both inlined into the query text. The regex prefix `(?i)` makes the node_name match case-insensitive.*

### `_upsert_article` — src/pubmed/infra/db/neo4j_article_adapter.py
**What it does:** Upserts a PubMed article (doc1) node keyed by pmcid with DOI/PMID/title/keywords, title/keyword/merged embeddings, publication date, and PDF URI; returns the pmcid.

**Cypher:**
```cypher
MERGE (doc1:`%s` {
    pmcid: $pmcid
})
ON MATCH
    SET doc1.doi = $doi,
        doc1.pmid = $pmid,
        doc1.refresh_date = datetime(),
        doc1.title = $title,
        doc1.keywords = $keywords,
        doc1.title_embeddings = $title_embeddings,
        doc1.keyword_embeddings = $keyword_embeddings,
        doc1.merged_embeddings = $merged_embeddings,
        doc1.epub_date = $pub_date,
        doc1.pdf_uri = $pdf_uri
ON CREATE
    SET doc1.pmcid = $pmcid,
        doc1.is_pubmed = true,
        doc1.refresh_date = datetime(),
        doc1.doi = $doi,
        doc1.pmid = $pmid,
        doc1.keywords = $keywords,
        doc1.title_embeddings = $title_embeddings,
        doc1.keyword_embeddings = $keyword_embeddings,
        doc1.merged_embeddings = $merged_embeddings,
        doc1.title = $title,
        doc1.epub_date = $pub_date,
        doc1.pdf_uri = $pdf_uri
RETURN doc1.pmcid
```
*The single `%s` label is `normalize_node_label(PUBMED_ARTICLE_NODE_TYPE)`.*

### `_link_article_and_node` — src/pubmed/infra/db/neo4j_article_adapter.py
**What it does:** Optionally matches a PubMed article by pmcid and any entity by node_index, then merges a has-extraction relationship between them; returns the article pmcid, the relationship type, and the entity node_index.

**Cypher:**
```cypher
OPTIONAL MATCH (doc:%s { pmcid: $pmcid })
OPTIONAL MATCH (entity { node_index: $node_index })
MERGE (doc)-[r:%s { is_pubmed: true }]-(entity)
RETURN doc.pmcid, type(r), entity.node_index
```
*The first `%s` is `PUBMED_ARTICLE_NODE_TYPE` and the second `%s` is `PUBMED_ARTICLE_EXTRACTION_REL_TYPE`.*

### `_link_article_and_clinical_trial` — src/pubmed/infra/db/neo4j_article_adapter.py
**What it does:** Optionally matches a PubMed article by pmcid and a clinical trial entity by node_id, then merges a has-extraction relationship between them; returns the article pmcid, the relationship type, and the entity node_index.

**Cypher:**
```cypher
OPTIONAL MATCH (doc:%s { pmcid: $pmcid })
OPTIONAL MATCH (entity:%s { node_id: $node_id })
MERGE (doc)-[r:%s { is_pubmed: true }]-(entity)
RETURN doc.pmcid, type(r), entity.node_index
```
*The three `%s` placeholders are `PUBMED_ARTICLE_NODE_TYPE`, `CLINICAL_TRIAL_NODE_TYPE`, and `PUBMED_ARTICLE_EXTRACTION_REL_TYPE`.*

### `_upsert_summary` — src/pubmed/infra/db/neo4j_summary_adapter.py
**What it does:** Matches an existing PubMed article (doc) by pmcid, upserts a summary node (title/summary/rating/level) linked to it, and upserts one finding node plus a relationship per finding in the summary; returns the pmcid, summary_id, and refresh_date.

**Cypher:**
```cypher
MATCH (doc:`%s` { pmcid: $pmcid })
MERGE (summary:`%s` {
    summary_id: $summary_id
})
ON MATCH
    SET summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()
ON CREATE
    SET summary.summary_id = $summary_id,
        summary.is_pubmed = true,
        summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()

MERGE (finding%s:`%s` { 
        finding_id: "%s",
        summary: "%s",
        explanation: "%s" 
}) 

MERGE (summary)-[rel%s:`%s` { is_pubmed: true }]-(finding%s) 

MERGE (doc)-[article_rel:`%s` { is_pubmed: true }]-(summary)

RETURN doc.pmcid, summary.summary_id, summary.refresh_date
```
*Dynamically assembled. The MATCH/MERGE summary block uses `%s` = `PUBMED_ARTICLE_NODE_TYPE` and `PUBMED_ARTICLE_SUMMARY_NODE_TYPE`. For each finding in `summary.findings`, a `MERGE (finding<n>:...)` clause is appended where placeholders are the finding counter, `PUBMED_ARTICLE_SUMMARY_FINDING_NODE_TYPE`, finding.id, finding.summary, and finding.explanation (values inlined into the query text, not parameterized). For each finding a matching `MERGE (summary)-[rel<n>:...]-(finding<n>)` is appended with `PUBMED_ARTICLE_SUMMARY_FINDING_REL_TYPE`. The `link_article_upsert` clause uses `PUBMED_ARTICLE_SUMMARY_REL_TYPE`, followed by the constant RETURN line.*


---

## TPP & Organization domain — target product profiles, org resolution & search

### `_generate_tpp_upsert` — src/tpp/infra/db/adapter/neo4j_tpp_adapter.py
**What it does:** Builds the MERGE statement that upserts a target product profile (tpp) node by `node_id`, setting therapeutic area, product description, embeddings, and a refresh timestamp on both match and create. The `%s` is interpolated with `TPP_NODE_TYPE`.

**Cypher:**
```cypher
MERGE (tpp:`%s` {
    node_id: $node_id
})
ON MATCH
    SET tpp.threaputic_area = $threaputic_area,
        tpp.product_description = $product_description,
        tpp.refresh_date = datetime(),
        tpp.embeddings = $embeddings
ON CREATE
    SET tpp.threaputic_area = $threaputic_area,
        tpp.product_description = $product_description,
        tpp.refresh_date = datetime(),
        tpp.node_index = $node_index,
        tpp.embeddings = $embeddings,
        tpp.is_csl = true
```

### `_generate_tpp_question_upserts` — src/tpp/infra/db/adapter/neo4j_tpp_adapter.py
**What it does:** For each question on a tpp, builds a fragment that continues from the matched `tpp`, upserts a question node by `node_id`, sets its type/ideal/acceptable/excluded/embeddings, and links it to the tpp via a relationship. The template is generated once per question with a numeric `count` suffix interpolated into each `$question{count}_*` parameter name; `%s` placeholders are filled with `TPP_QUESTION_NODE_TYPE`, the per-question parameter names, and `TPP_QUESTION_REL_TYPE`.

**Cypher:**
```cypher
WITH tpp
MERGE (tpp_question:`%s` { node_id: %s })
ON MATCH
    SET tpp_question.question_type = %s,
        tpp_question.ideal = %s,
        tpp_question.acceptable = %s,
        tpp_question.excluded = %s,
        tpp_question.refresh_date = datetime(),
        tpp_question.embeddings = %s
ON CREATE
    SET tpp_question.question_type = %s,
        tpp_question.ideal = %s,
        tpp_question.acceptable = %s,
        tpp_question.excluded = %s,
        tpp_question.refresh_date = datetime(),
        tpp_question.embeddings = %s,
        tpp_question.node_index = %s,
        tpp_question.is_csl = true
MERGE (tpp)-[r1:`%s` { is_csl: true }]-(tpp_question)
```

### `_generate_find_by_tpp_id_query` — src/tpp/infra/db/adapter/neo4j_tpp_search_adapter.py
**What it does:** Matches a `csl_tpp` node by `node_id` and runs a vector index similarity search using the tpp's embeddings, returning the similarity score plus the tpp description and the matched patent's application number, abstract, and claims. The `%s` placeholders are interpolated with `USPTO_PGPUB_EMBEDDINGS_INDEX_NAME`, the result `limit` (default 200), and `EMBEDDINGS_FIELD_NAME`.

**Cypher:**
```cypher
MATCH (tpp:csl_tpp { node_id: $node_id })
CALL db.index.vector.queryNodes('%s', %s, tpp.%s)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims
```

### `_generate_find_by_tpp_question_query` — src/tpp/infra/db/adapter/neo4j_tpp_search_adapter.py
**What it does:** Matches a `csl_tpp` and its associated `csl_tpp_question` of a given question type, then runs a vector index similarity search using the question's embeddings, returning the score plus tpp description and matched patent application number, abstract, and claims. The `%s` placeholders are interpolated with the uppercased `question_type.name`, `USPTO_PGPUB_EMBEDDINGS_INDEX_NAME`, the `limit` (default 200), and `EMBEDDINGS_FIELD_NAME`.

**Cypher:**
```cypher
MATCH (tpp:csl_tpp { node_id: $node_id })-[:has_associated_question]-(tpp_question:csl_tpp_question { question_type: '%s'})
CALL db.index.vector.queryNodes('%s', %s, tpp_question.%s)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims
```

### `_generate_find_by_tpp_id_and_graph_embeddings_query` — src/tpp/infra/db/adapter/neo4j_tpp_search_adapter.py
**What it does:** Matches a `csl_tpp` by `node_id` and runs a vector index similarity search using the tpp's graph embeddings, returning the score plus tpp description and matched patent application number, abstract, and claims. The `%s` placeholders are interpolated with `USPTO_PGPUB_GRAPH_EMBEDDINGS_INDEX_NAME`, the `limit` (default 200), and `GRAPH_EMBEDDINGS_FIELD_NAME`.

**Cypher:**
```cypher
MATCH (tpp:csl_tpp { node_id: $node_id })
CALL db.index.vector.queryNodes('%s', %s, tpp.%s)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;
```

### `_upsert_summary` (base upsert) — src/tpp/infra/db/adapter/neo4j_tpp_summary_adapter.py
**What it does:** Matches an existing tpp node by its primary key, then upserts a summary node by `summary_id`, setting title, summary text, rating, rating explanation, level, and refresh date. The `%s` placeholders are interpolated with `TPP_NODE_TYPE`, `TPP_NODE_PRIMARY_KEY`, and `TPP_SUMMARY_NODE_TYPE`.

**Cypher:**
```cypher
MATCH (tpp:`%s` { %s: $tpp_id })
MERGE (summary:`%s` {
    summary_id: $summary_id
})
ON MATCH
    SET summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()
ON CREATE
    SET summary.summary_id = $summary_id,
        summary.is_csl = true,
        summary.title = $title,
        summary.summary = $summary,
        summary.rating = $rating,
        summary.rating_explanation = $rating_explanation,
        summary.level = $level,
        summary.refresh_date = datetime()
```

### `_upsert_summary` (finding upsert) — src/tpp/infra/db/adapter/neo4j_tpp_summary_adapter.py
**What it does:** For each finding on the summary, builds a fragment that merges a finding node whose `finding_id`, `summary`, and `explanation` values are inlined directly into the query string. The `%s` placeholders are interpolated with the loop's `finding_count`, `TPP_SUMMARY_FINDING_NODE_TYPE`, and the finding's `id`, `summary`, and `explanation`.

**Cypher:**
```cypher
MERGE (finding%s:`%s` {
        finding_id: "%s",
        summary: "%s",
        explanation: "%s" 
}) 
```

### `_upsert_summary` (summary-finding relationship) — src/tpp/infra/db/adapter/neo4j_tpp_summary_adapter.py
**What it does:** For each finding, builds a fragment that merges a relationship between the summary node and the corresponding finding node. The `%s` placeholders are interpolated with the loop's `finding_count`, `TPP_SUMMARY_FINDING_REL_TYPE`, and `finding_count` again.

**Cypher:**
```cypher
MERGE (summary)-[rel%s:`%s` { is_csl: true }]-(finding%s) 
```

### `_upsert_summary` (link tpp to summary) — src/tpp/infra/db/adapter/neo4j_tpp_summary_adapter.py
**What it does:** Merges the relationship that links the matched tpp node to the summary node. The `%s` placeholder is interpolated with `TPP_SUMMARY_REL_TYPE`.

**Cypher:**
```cypher
MERGE (tpp)-[article_rel:`%s` { is_csl: true }]-(summary)
```

### `_upsert_organization_resolution` (org merge) — src/organization/infra/db/neo4j_organization_adapter.py
**What it does:** Upserts an organization (company) node by `node_name`, refreshing its timestamp on match and setting node_id, names, and parent on create. The `%s` placeholder is interpolated with `normalize_node_label(OrganizationNodeEnum.COMPANY.value[1])`. This base query is then concatenated with generated alias upsert fragments and a `RETURN organization.node_id` clause before execution.

**Cypher:**
```cypher
MERGE (organization:%s { node_name: $offical_name })
ON MATCH
    SET organization.refresh_date = datetime()
ON CREATE
    SET organization.refresh_date = datetime(),
        organization.node_id = $org_id,
        organization.node_name = $offical_name,
        organization.offical_name = $offical_name,
        organization.parent = $parent
```

### `_generate_alias_upserts` — src/organization/infra/db/neo4j_organization_adapter.py
**What it does:** For each alias (subsidiary, acquisition, spelling variation, merger, demerger), builds a fragment that continues from the matched organization, upserts an alias node by `node_name`, and links the organization to the alias. The `%s` placeholders are interpolated with `normalize_node_label(node_type)`, the per-alias `$..._node_name` parameter, the `$..._node_id` parameter, the `$..._node_name` parameter again, and `OrganizationRelationshipEnum.HAS_ALIAS.value[1]`.

**Cypher:**
```cypher
WITH organization
            MERGE (alias:`%s` { node_name: %s })
            ON MATCH
                SET alias.refresh_date = datetime()
            ON CREATE
                SET alias.refresh_date = datetime(),
                    alias.node_id = %s,
                    alias.node_name = %s
            MERGE (organization)-[r1:`%s`]-(alias)
```

### `_generate_search` — src/organization/infra/db/neo4j_organization_adapter.py
**What it does:** Matches an organization node by `organization_id` and uses an APOC subgraph traversal (max depth 2) over alias relationships to return distinct related organization node names, ids, and organization names. The `%s` placeholders are interpolated with `OrganizationNodeEnum.ORGANIZATION_V2.value[1]` and `OrganizationRelationshipEnum.HAS_ALIAS.value[1]`.

**Cypher:**
```cypher
MATCH (o:`%s`)
        WHERE o.organization_id = $organization_name
        CALL apoc.path.subgraphNodes([n],
        { 
            relationshipFilter: "%s",
            maxLevel: 2
        }) YIELD org
        RETURN DISTINCT org.node_name as name, toStringOrNull(org.node_id) as org_id,
            toStringOrNull(org.organization_name) as org_name
```

### `_generate_search` — src/organization/infra/db/neo4j_organization_query_adapter.py
**What it does:** (Deprecated old-schema query.) Optionally matches an organization by `organization_name`, captures its organization_id, then optionally re-matches by that id, returning distinct org_id and org_name. Both `%s` placeholders are interpolated with `OrganizationNodeEnum.ORGANIZATION_V2.value[1]`.

**Cypher:**
```cypher
OPTIONAL MATCH (o:`%s`)
        WHERE o.organization_name = $organization_name AND (n.is_hidden IS NULL OR NOT n.is_hidden)
        WITH o.organization_id as org_id
        OPTIONAL MATCH (o:`%s`)
        WHERE o.organization_id = org_id
        RETURN DISTINCT toStringOrNull(org.node_id) as org_id, toStringOrNull(org.organization_name) as org_name
```

### `_find_companies_by_name_pattern` — src/organization/infra/db/neo4j_organization_search_adapter.py
**What it does:** Finds organization nodes whose `organization_canonical_name` matches a sanitized case-insensitive regex pattern, returning org_id, org_name, and org_type with pagination (skip/limit). The `%s` placeholder is interpolated with `OrganizationNodeEnum.ORGANIZATION_V3.value[1]`; the `$pattern` parameter receives `(?i)` plus the sanitized pattern.

**Cypher:**
```cypher
MATCH (o:`%s`)
        WHERE o.organization_canonical_name =~ $pattern
        RETURN o.org_id as org_id, o.organization_canonical_name as org_name, o.organization_type as org_type
        SKIP $skip
        LIMIT $limit
```

### `_find_assets_by_org_id` — src/organization/infra/db/neo4j_organization_search_adapter.py
**What it does:** Finds clinical-trial-linked assets (diseases and drugs) connected to an organization identified by `org_id`, returning the organization type/name, the relationship type to the trial, the trial's nct_id, the relationship type to the asset, and the asset's labels and name, ordered and paginated. The `%s` placeholders are interpolated with `OrganizationNodeEnum.ORGANIZATION_V3.value[1]`, `FoundationalNodeEnum.CLINICAL_TRIAL.value[1]`, and a `|`-joined, backtick-escaped label union of the DISEASE and DRUG node labels.

**Cypher:**
```cypher
MATCH (start:`%s`)-[rel1]-(ct:`%s`)-[rel2]-(end:%s)
        WHERE start.org_id = $org_id
        RETURN start.organization_type as org_type, start.organization_canonical_name as org_name,
               type(rel1) as org_to_ct_rel, ct.nct_id as trial, type(rel2) as ct_to_asset_rel, labels(end) as entity_labels, end.node_name as entity_name
        ORDER BY start.organization_canonical_name, trial desc
        SKIP $skip
        LIMIT $limit
```


---

## Graph / Stats / Clinical Trials / Centree / NL-to-Cypher

### `_merge_and_return` — src/graph/infra/db/neo4j_graphrag_adapter.py
**What it does:** Idempotently merges two entity nodes (source and target) and a relationship between them from an extraction, then returns the source value, target value, and relationship type. Node labels and the relationship type are interpolated from the extraction; node/relationship properties are passed as bound parameters.

**Cypher:**
```cypher
MERGE (n1:`%s` { value: $src_value, id: $src_id, description: $src_description, type: $src_type }) 
MERGE (n2:`%s` { value: $tgt_value, id: $tgt_id, description: $tgt_description, type: $tgt_type }) 
MERGE (n1)-[rel:`%s` { id: $rel_id, type: $rel_type, description: $rel_description }]->(n2) 
RETURN n1.value, n2.value, rel.type
```
(The three `%s` placeholders are interpolated, in order, with `normalize_node_label(rel.source.type)`, `normalize_node_label(rel.target.type)`, and `rel.relation`.)

### `_link_publication_and_node` — src/graph/infra/db/neo4j_graphrag_linking_adapter.py
**What it does:** Links a publication/document node to a base graph entity node by merging a `has_publication` relationship between them, returning the document primary key, the relationship type, and the entity's node_index. The document label, primary key property name, and relationship type are interpolated.

**Cypher:**
```cypher
OPTIONAL MATCH (doc:%s { %s: $primary_key })
OPTIONAL MATCH (entity { node_index: $node_index })
MERGE (doc)<-[r:%s]-(entity)
RETURN doc.%s, type(r), entity.node_index
```
(Interpolated values: 1st `%s` = `normalize_node_label(source_node_label)`; 2nd `%s` = `source_primary_key_label`; 3rd `%s` = `HAS_PUBLICATION_EXTRACTION_REL_TYPE`; 4th `%s` = `source_primary_key_label`. `$primary_key` and `$node_index` are bound parameters.)

### `_build_find_by_node_name_query` — src/graph/infra/db/neo4j_graphrag_linking_adapter.py
**What it does:** Builds a query that finds a node of a given entity type whose `node_name` matches the supplied name case-insensitively (regex), returning its `node_name` and `node_index`. Both the label and the node name are interpolated directly into the query string.

**Cypher:**
```cypher
MATCH (n:`%s`)
                WHERE n.node_name =~ '(?i)%s'
                RETURN n.node_name, n.node_index
```
(1st `%s` = `normalize_node_label(entity_type)`; 2nd `%s` = `normalize_node_name(node_name)`.)

### `_build_count_all_by_label` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Builds a query that counts all nodes carrying the given label, returning the total as `count`. The label is interpolated into the query.

**Cypher:**
```cypher
MATCH (n:`%s`)
            RETURN count(n) as count
```
(`%s` = the `label` argument.)

### `_build_count_all_relationships` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Counts all relationships in the graph (matching any node-to-node relationship), returning the total as `relationship_count`.

**Cypher:**
```cypher
MATCH(n)-[r]-(n2)
            RETURN count(r) as relationship_count
```

### `_build_count_all_nodes` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Counts every node in the graph, returning the total as `node_count`.

**Cypher:**
```cypher
MATCH (n)
            RETURN count(n) as node_count
```

### `_build_count_disambiguated_organizations` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Counts the number of distinct `organization_id` values across organization nodes, returning the result as `disambiguated_org_count`. The organization label is interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
            RETURN count(distinct(n.organization_id)) as disambiguated_org_count
```
(`%s` = `FoundationalNodeEnum.ORGANIZATION.value[1]`.)

### `_build_count_theraputic_areas` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Counts distinct therapeutic areas and therapeutic subgroups across clinical-trial nodes, returning `theraputic_area_count` and `theraputic_area_group_count`. The clinical-trial label is interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
        RETURN COUNT(DISTINCT(n.therapeutic_area)) as theraputic_area_count,
            COUNT(DISTINCT(n.therapeutic_subgroup)) as theraputic_area_group_count
```
(`%s` = `FoundationalNodeEnum.CLINICAL_TRIAL.value[1]`.)

### `_build_min_max_uspto_dates` — src/stats/infra/db/adapter/neo4j_database_stats_adapter.py
**What it does:** Computes the minimum and maximum patent-application `filing_date` values (as strings), returning `min_uspto_filing_date` and `max_uspto_filing_date`. The patent-application label is interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
            RETURN toStringOrNull(min(n.filing_date)) as min_uspto_filing_date, toStringOrNull(max(n.filing_date)) as max_uspto_filing_date
```
(`%s` = `FoundationalNodeEnum.PATENT_APPLICATION.value[1]`.)

### `_build_find_by_nct_query` — src/clinicaltrail/infra/db/neo4j_clinical_trial_adapter.py
**What it does:** Builds a query that finds a clinical-trial node by its NCT number (passed as a bound parameter) and returns its `node_id`. The clinical-trial label is interpolated into the query.

**Cypher:**
```cypher
MATCH (n:`%s`)
                WHERE n.nct_number = $nct_number
                RETURN n.node_id as node_id
```
(`%s` = `CLINICAL_TRIAL_NODE_TYPE`; `$nct_number` is a bound parameter.)

### `_build_find_by_node_index_query` — src/centree/infra/db/neo4j_centree_project_ingest_adapter.py
**What it does:** Builds a query that finds a Centree project node whose `node_name` matches the supplied entity name case-insensitively (regex), returning its `node_name` and `node_index`. The label and entity name are interpolated.

**Cypher:**
```cypher
MATCH (n:`%s`)
                WHERE n.node_name =~ '(?i)%s'
                RETURN n.node_name, n.node_index
```
(1st `%s` = `normalize_node_label(CENTREE_PROJECT_NODE_TYPE)`; 2nd `%s` = `normalize_node_name(entity)`.)

### `_upsert_project` — src/centree/infra/db/neo4j_centree_project_ingest_adapter.py
**What it does:** Upserts a Centree project node keyed on its `source` (primary id): on match it updates project metadata and refresh date; on create it additionally sets a generated `node_id` and confidentiality flag. Returns the project's `node_id`. The label is interpolated; all property values are bound parameters.

**Cypher:**
```cypher
MERGE (proj:`%s` {
                source: $primary_id
            })
            ON MATCH
                SET proj.source = $primary_id,
                    proj.node_name = $primary_label,
                    proj.primary_label = $primary_label,
                    proj.collaborators = $collaborators,
                    proj.project_source = $project_source,
                    proj.project_science_coordinators = $project_science_coordinators,
                    proj.project_type = $project_type,
                    proj.project_aim = $project_aim,
                    proj.is_active_project = $is_active_project,
                    proj.eln_rd_codes = $eln_rd_codes,
                    proj.has_therapeutic_areas = $has_therapeutic_areas,
                    proj.refresh_date = datetime()
            ON CREATE
            SET proj.node_id = $node_id,
                    proj.source = $primary_id,
                    proj.node_name = $primary_label,
                    proj.primary_label = $primary_label,
                    proj.collaborators = $collaborators,
                    proj.project_source = $project_source,
                    proj.project_science_coordinators = $project_science_coordinators,
                    proj.project_type = $project_type,
                    proj.project_aim = $project_aim,
                    proj.is_active_project = $is_active_project,
                    proj.eln_rd_codes = $eln_rd_codes,
                    proj.has_therapeutic_areas = $has_therapeutic_areas,
                    proj.is_csl_confidential = true,
                    proj.refresh_date = datetime()
            RETURN proj.node_id
```
(`%s` = `normalize_node_label(CENTREE_PROJECT_NODE_TYPE)`; all `$...` values are bound parameters.)

### `CYPHER_GENERATION_TEMPLATE` (example: researchers on a topic) — src/cypher_query.py
**What it does:** Example Cypher embedded in the LLM cypher-generation prompt template, illustrating how to answer "What do we know about researchers on a given topic?" by matching a researcher to any connected node where the researcher description contains or value equals the topic.

**Cypher:**
```cypher
MATCH (r:researcher)-[rel]-(t)
WHERE r.description contains "$topic"  OR r.value = "$topic" 
RETURN r, rel, t
```

### `CYPHER_GENERATION_TEMPLATE` (example: inflammatory conditions responding to treatment) — src/cypher_query.py
**What it does:** Example Cypher embedded in the LLM cypher-generation prompt template, illustrating how to answer "What inflammatory condition respond to a treatment?" by matching conditions whose description contains "inflammatory" to connected treatments.

**Cypher:**
```cypher
MATCH (a:condition)-[rel]-(c:treatment)
WHERE a.description CONTAINS "inflammatory"
RETURN a, rel, c
```
