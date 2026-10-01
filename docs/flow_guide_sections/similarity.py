"""Per-route flow guide for Eugene's similarity_router.

Produces EUGENE_SIMILARITY_FLOW_GUIDE.pdf. Loaded by
generate_route_flow_guides.py via the dispatcher.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_SIMILARITY_FLOW_GUIDE.pdf"
TITLE = "Eugene Similarity Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------------------------------------------- cover
    story += [
        h.p("Eugene Similarity Search &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP entry &rarr; DI wiring &rarr; "
            "Neo4j GDS nodeSimilarity Cypher &rarr; in-memory projection &rarr; "
            "embedding pipeline &rarr; Pydantic response.",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene answers "
            f"&ldquo;what is similar to {h.c('Lupus')}?&rdquo; by running "
            f"Neo4j Graph Data Science (GDS) {h.c('nodeSimilarity.filtered')} "
            "over a pre-projected in-memory graph, and how the "
            f"{h.c('POST /similarity/{label}')} endpoint stitches the request "
            "together at query time. Every reference uses the form "
            f"{h.c('path/to/file.py:line')} so you can open files in your IDE "
            "and step through with a debugger."
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('POST /similarity/drug')} body "
            f"{h.c('{&quot;values&quot;: [&quot;ibuprofen&quot;]}')} &mdash; "
            "rank canonical drugs by neighbourhood overlap with the matched "
            "anchor drug(s).",
            f"{h.c('POST /similarity/disease')} body "
            f"{h.c('{&quot;values&quot;: [&quot;lupus&quot;]}')} &mdash; same "
            "shape, but anchored on disease nodes.",
            f"Only those two labels are accepted &mdash; see "
            f"{h.c('FacetLabel')} and the adapter guard described in Section 2.",
        ]),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Section 0 explains the schema and where the &ldquo;similarity&rdquo; "
            "score actually comes from. It is <b>not</b> a vector search over "
            "stored embeddings; it is graph topology (GDS nodeSimilarity in "
            "COSINE mode over a relationship-set vector). The embedding "
            "pipeline still exists (Section 4) because FastRP training "
            "consumes it, but the live endpoint does not read it.",
            "Sections 1&ndash;3 trace the live request: HTTP &rarr; adapter Cypher "
            "&rarr; the projection it depends on.",
            "Sections 4&ndash;5 cover the offline pipeline: embedding upserts "
            "and the optional FastRP training step.",
            "Section 6 lists the response/Pydantic shape with an example JSON.",
            "Section 7 is a step-through debugging walk (curl + breakpoints).",
            "Section 8 is the file-path reference index.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 0. Schema
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "The similarity router operates on the canonical foundational "
            "graph &mdash; the same nodes the rest of Eugene reads. There is no "
            "separate similarity table or vector store."
        ),
        h.code(
            "(:drug    { node_id, node_index, node_name, embeddings?, ... })\n"
            "(:disease { node_id, node_index, node_name, embeddings?, ... })\n"
            "// plus all the foundational relationship types\n"
            "// (indication, contraindication, disease_protein,\n"
            "//  pathway_pathway, off_label_use, exposure_disease, ...)\n"
            "// connecting them to other foundational labels."
        ),
        *h.bullets([
            f"<b>Label whitelist.</b> Only {h.c('DRUG')} and {h.c('DISEASE')} "
            f"are valid path parameters. Enforced at the type boundary by "
            f"{h.c('FacetLabel')} "
            f"({h.c('src/foundation/router/model/facet_label.py')}) and "
            f"<i>again</i> defensively inside the adapter at "
            f"{h.c('neo4j_foundational_similarity_adapter.py:58-62')} which "
            f"raises {h.c('ValueError')} for anything else.",
            f"<b>{h.c('node_id')} vs {h.c('node_index')}.</b> "
            f"{h.c('node_id')} is the public identifier returned to clients "
            f"(stringified by {h.c('toStringOrNull')} in the Cypher). "
            f"{h.c('node_index')} is the upsert key used by the embedding "
            "writer (Section 4).",
            f"<b>{h.c('embeddings')} property.</b> Optional. Written by "
            f"{h.c('Neo4jFoundationalNodeAdapter.upsert_embeddings')} when the "
            f"ingest pipeline runs (Section 4). The similarity router itself "
            f"<b>does not read this property</b> &mdash; it is consumed only by "
            f"the FastRP training step in Section 5.",
            f"<b>No Neo4j CONSTRAINTs.</b> Like every other foundational route "
            f"in Eugene, idempotency is provided by {h.c('MERGE')} on "
            f"{h.c('node_id')} / {h.c('node_index')}, not by a "
            f"{h.c('CREATE CONSTRAINT')}. Do not assume uniqueness is enforced "
            "at the database level.",
            f"<b>Projection.</b> The GDS in-memory graph is named "
            f"{h.c('eugene_similarity_graph')} "
            f"({h.c('src/foundation/conf/const.py:2')}). It must exist before "
            "the endpoint can return rows &mdash; see Section 3.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 1. HTTP entry
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p(f"{h.c('src/foundation/router/similarity_router.py')}", h.PATH),
        h.p("Module-load dependency injection", h.H2),
        h.p(
            f"Line ~28 of {h.c('similarity_router.py')} builds the adapter at "
            "<i>import time</i>:"
        ),
        h.code(
            "foundational_similarity_adapter = neo4j_foundational_similarity_adapter()"
        ),
        h.p(
            f"The factory lives at "
            f"{h.c('src/foundation/conf/conf.py:177-184')}:"
        ),
        h.code(
            "def neo4j_foundational_similarity_adapter()\n"
            "        -> Neo4jFoundationalSimilarityAdapter:\n"
            "    return _neo4j_foundational_similarity_adapter(\n"
            "        driver=_neo4j_driver())\n"
            "\n"
            "def _neo4j_foundational_similarity_adapter(driver: Driver)\n"
            "        -> Neo4jFoundationalSimilarityAdapter:\n"
            "    return Neo4jFoundationalSimilarityAdapter(driver=driver)"
        ),
        h.p(
            f"This is Eugene&apos;s manual DI pattern: one adapter instance per "
            f"process, sharing a single {h.c('neo4j.Driver')}. No FastAPI "
            f"{h.c('Depends')}, no per-request construction. The driver pool "
            "is what gives the endpoint its throughput."
        ),
        h.p("Handler signature (lines 31-58)", h.H2),
        h.code(
            "@router.post(\"/{label}\", response_model_exclude_none=True)\n"
            "async def calculate_similarity_by_label_and_values(\n"
            "    label: Annotated[\n"
            "        FacetLabel,\n"
            "        Path(description=\"The node type to list. e.g. disease, drug\",\n"
            "             max_length=64, min_length=0,\n"
            "             examples=[\"disease, drug\"]),\n"
            "        AfterValidator(validate_label),\n"
            "    ],\n"
            "    similarity_search_values: SimilaritySearchValues,\n"
            "):\n"
            "    label_enum = str_to_label_enum(label.value[1])\n"
            "    values = (similarity_search_values.values\n"
            "              if similarity_search_values.values is not None\n"
            "              else [])\n"
            "    dataframe = foundational_similarity_adapter\\\n"
            "        .calculate_similar_by_label_and_values(\n"
            "            label=label_enum, values=values)\n"
            "    return to_similarity_response(dataframe)"
        ),
        h.p("Path and body validators", h.H2),
        *h.bullets([
            f"{h.c('FacetLabel')} "
            f"({h.c('src/foundation/router/model/facet_label.py')}) is the "
            "enum FastAPI uses to coerce the path string before the handler "
            "runs. Any value outside its members returns a 422.",
            f"{h.c('validate_label')} "
            f"({h.c('src/foundation/router/validate_util.py:13-21')}) is an "
            f"{h.c('AfterValidator')} that double-checks the value is a "
            f"member of {h.c('Label')} and maps it to a "
            f"{h.c('FoundationalNodeEnum')}. Belt-and-braces with the type "
            "system above.",
            f"{h.c('SimilaritySearchValues')} "
            f"({h.c('src/foundation/router/model/similarity_search_values.py')}) "
            f"is a Pydantic model with a single field "
            f"{h.c('values: list[str]')}. There is <b>no</b> "
            f"{h.c('validate_facet_search_values')} on the body in this "
            "router &mdash; that omission matters; see the FIXME in Section 2.",
            f"{h.c('str_to_label_enum')} "
            f"({h.c('src/foundation/router/validate_util.py')}) maps the "
            f"validated string into the {h.c('FoundationalNodeEnum')} the "
            "adapter expects.",
        ]),
        h.p("Set your first breakpoint", h.H2),
        h.p(
            f"At {h.c('similarity_router.py:48')} (the "
            f"{h.c('label_enum = ...')} line) you can inspect "
            f"{h.c('label.value')} and "
            f"{h.c('similarity_search_values.values')} before the adapter call."
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 2. adapter / cypher
    story += [
        h.p("2. Query adapter &mdash; the GDS nodeSimilarity Cypher", h.H1),
        h.p(
            f"{h.c('src/foundation/infra/db/adapter/neo4j_foundational_similarity_adapter.py')}",
            h.PATH,
        ),
        h.p("Public path", h.H2),
        *h.bullets([
            f"{h.c('calculate_similar_by_label_and_values()')} (line ~25) "
            f"calls {h.c('ensure_connection(self.driver)')} "
            f"({h.c('src/graph/util/util.py')}) for a per-request driver "
            f"health check, then delegates to "
            f"{h.c('_calculate_similar_by_label_and_values()')} with the "
            f"projection name read from "
            f"{h.c('SIMILARITY_GRAPH_PROJECTION_NAME')}.",
            f"{h.c('_calculate_similar_by_label_and_values()')} (line ~33) "
            f"builds the Cypher string and runs "
            f"{h.c('self.driver.execute_query(query_=..., result_transformer_=neo4j.Result.to_df)')}, "
            f"returning a pandas {h.c('DataFrame')}.",
            f"{h.c('DriverError')} and {h.c('Neo4jError')} are logged and "
            f"re-raised. The router has no {h.c('try/except')}, so they "
            "bubble up as a FastAPI 500.",
        ]),
        h.p(
            "Generated Cypher (after interpolation, for "
            f"{h.c('values=[&quot;lupus&quot;]')} on the "
            f"{h.c('disease')} label):",
            h.H2,
        ),
        h.code(
            "MATCH (d1:`disease`)\n"
            "WHERE d1.node_name =~ '(?i).*lupus.*'\n"
            "\n"
            "CALL gds.nodeSimilarity.filtered.stream('eugene_similarity_graph', {\n"
            "    degreeCutoff: 1,\n"
            "    similarityCutoff: .45,\n"
            "    similarityMetric: \"COSINE\",\n"
            "    sourceNodeFilter: [d1]\n"
            "})\n"
            "YIELD node1, node2, similarity\n"
            "RETURN similarity,\n"
            "    gds.util.asNode(node1).node_name AS name1,\n"
            "    gds.util.asNode(node2).node_name AS name2,\n"
            "    toStringOrNull(gds.util.asNode(node1).node_id) AS id1,\n"
            "    toStringOrNull(gds.util.asNode(node2).node_id) AS id2\n"
            "ORDER BY similarity DESCENDING, name1, name2"
        ),
        h.p("Anatomy of the query", h.H2),
        *h.bullets([
            f"<b>Label interpolation.</b> The string after "
            f"{h.c('MATCH (d1:`')} is built from "
            f"{h.c('normalize_node_label(label.value[1])')} "
            f"({h.c('src/graph/util/node_util.py')}). This is safe because the "
            f"enum value is constrained to {h.c('drug')} / {h.c('disease')}; "
            f"the backticks make Cypher treat it as an identifier.",
            f"<b>Regex WHERE clause.</b> The builder iterates "
            f"{h.c('values')} and produces one "
            f"{h.c('d1.node_name =~ &apos;(?i).*&lt;value&gt;.*&apos;')} per "
            f"entry, joined by {h.c('or')}. With "
            f"{h.c('[&quot;lupus&quot;, &quot;arthritis&quot;]')} you get "
            f"two regex predicates OR&apos;d together.",
            f"<b>{h.c('gds.nodeSimilarity.filtered.stream')}.</b> The "
            f"{h.c('.filtered')} variant accepts a "
            f"{h.c('sourceNodeFilter')} so only the regex-matched anchors "
            "act as sources of comparisons. This is what makes the call "
            "cheap enough for a synchronous HTTP endpoint &mdash; the "
            "unfiltered procedure compares every node against every other "
            "node in the projection.",
            f"<b>{h.c('degreeCutoff: 1')}.</b> Source nodes with fewer than "
            "one outgoing relationship in the projection are skipped (no "
            "meaningful neighbour set to compare).",
            f"<b>{h.c('similarityCutoff: 0.45')}.</b> Pairs scoring below "
            "0.45 are dropped before they cross the wire. There is no "
            "explicit top-k clause; results return in descending score "
            "order and the client may paginate.",
            f"<b>{h.c('similarityMetric: &quot;COSINE&quot;')}.</b> For each "
            "(source, target) pair, treat the multiset of relationships to "
            "shared neighbours as a vector and compute cosine similarity. "
            "<b>No learned embeddings are used here</b> &mdash; the "
            f"{h.c('embeddings')} property of Section 4 is irrelevant to "
            "this call.",
            f"<b>{h.c('sourceNodeFilter: [d1]')}.</b> Passes the node objects "
            f"matched by the {h.c('MATCH')} above. Each invocation of the "
            "stream procedure compares every filtered source against every "
            "node in the projection.",
        ]),
        h.p("FIXME: Cypher injection", h.H2),
        h.p(
            f"The source carries an explicit FIXME at "
            f"{h.c('neo4j_foundational_similarity_adapter.py:54-56')}:"
        ),
        h.code(
            "# FIXME: cypher injection issue\n"
            "# WARNING: this is wrong to inject a user query into the cypher\n"
            "# however the api does not let me pass a parameter into a query\n"
            "# when using a regex like this?"
        ),
        h.p(
            f"Each {h.c('value')} in the request body is spliced raw into the "
            f"Cypher regex. The Neo4j {h.c('=~')} operator does not accept a "
            "query parameter in the position used here, so the original "
            "author opted for string interpolation. Until that is reworked "
            "(e.g. with an APOC procedure that supports parametrised "
            "regexes, or a server-side allow-list), treat the "
            f"{h.c('values')} field as <b>untrusted</b> and validate it "
            "upstream. Regex metacharacters in the input will also alter "
            "match semantics &mdash; not just security, also correctness."
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 3. projection
    story += [
        h.p("3. Graph projection &mdash; building eugene_similarity_graph", h.H1),
        h.p(
            f"{h.c('src/foundation/infra/db/adapter/neo4j_project_similarity_graph_adapter.py')}",
            h.PATH,
        ),
        h.p(
            f"The endpoint will return zero rows (or raise a GDS "
            f"&ldquo;graph does not exist&rdquo; error) until "
            f"{h.c('eugene_similarity_graph')} has been projected into "
            f"Neo4j&apos;s in-memory store. The projection is built by "
            f"{h.c('Neo4jProjectSimilarityGraphAdapter.project_similarity_graph()')} "
            f"(line ~31), which itself extends "
            f"{h.c('Neo4jProjectGraphAdapter')} (so the "
            f"{h.c('drop_graph_if_exists')} helper is inherited)."
        ),
        h.p("Projection Cypher template (lines ~85-102)", h.H2),
        h.code(
            "MATCH (source:%s)\n"
            "OPTIONAL MATCH (source)-[r:%s]-(target:%s)\n"
            "RETURN gds.graph.project(\n"
            "    '%s',\n"
            "    source,\n"
            "    target,\n"
            "    {\n"
            "        relationshipProperties: r { strength: 1 }\n"
            "    }\n"
            ")"
        ),
        h.p(
            f"The three label/relationship lists are joined with "
            f"{h.c('|')} so the {h.c('MATCH')} matches the union. Source "
            f"labels are normalized via {h.c('normalize_node_label()')} and "
            f"relationship labels are backtick-escaped via "
            f"{h.c('_escape_label()')} (lines 104-105)."
        ),
        h.p("Caller", h.H2),
        h.p(
            f"The orchestrator that calls "
            f"{h.c('project_similarity_graph()')} composes the lists of "
            f"foundational source labels, target labels and relationship "
            f"labels from {h.c('FoundationalNodeEnum')} / "
            f"{h.c('FoundationalRelationshipEnum')}, and passes "
            f"{h.c('replace=True')} on a refresh to drop any stale "
            "projection first."
        ),
        h.p("Notes", h.H2),
        *h.bullets([
            f"The projection is <i>in-memory only</i>. It does not survive a "
            "Neo4j restart and must be rebuilt as part of bring-up.",
            f"{h.c('OPTIONAL MATCH')} on the relationship means even nodes "
            "with no qualifying edges are projected. Combined with "
            f"{h.c('degreeCutoff: 1')} in Section 2, those orphans are "
            "filtered out at query time.",
            f"The {h.c('strength: 1')} relationship property is a constant "
            "weight &mdash; the projection is effectively unweighted today. "
            "Replacing it with a real strength field is a natural extension "
            "point for tuning cosine scores.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 4. embedding pipeline
    story += [
        h.p("4. Embedding pipeline (offline)", h.H1),
        h.p(
            f"{h.c('src/foundation/infra/embedding/foundational_node_embedding_provider.py')}",
            h.PATH,
        ),
        h.p(
            f"The live similarity endpoint does <b>not</b> read the "
            f"{h.c('embeddings')} property &mdash; it relies purely on graph "
            f"topology (Section 2). The embedding pipeline still exists "
            f"because (a) {h.c('embeddings')} is one of the "
            f"{h.c('featureProperties')} consumed by FastRP in Section 5 to "
            f"produce {h.c('prediction_embeddings')}, and (b) it is a "
            "natural extension point if you want to swap nodeSimilarity for "
            "a true vector search."
        ),
        h.p("Provider", h.H2),
        h.code(
            "class FoundationalNodeEmbeddingProvider(EmbeddingProvider):\n"
            "    def __init__(self, model: SentenceTransformer | StaticModel | None\n"
            "                       = None,\n"
            "                 model_cache_dir: str | None = None):\n"
            "        super().__init__(model_cache_dir=model_cache_dir)\n"
            "        self._model = model or self.init_model()\n"
            "\n"
            "    def to_embedding(self, value: str) -> ndarray:\n"
            "        if value is None: return None\n"
            "        return self._model.encode([value])"
        ),
        *h.bullets([
            f"The model is either a {h.c('sentence_transformers.SentenceTransformer')} "
            f"or a {h.c('model2vec.StaticModel')}, selected by the concrete "
            f"{h.c('init_model()')} implementation on the base class.",
            f"Embeddings are computed once per node value (typically "
            f"{h.c('node_name')}) and persisted on the node itself &mdash; not "
            "in a separate index.",
        ]),
        h.p("Upsert Cypher", h.H2),
        h.p(
            f"{h.c('src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:50-89')} &mdash; "
            f"{h.c('upsert_embeddings(label, node_index, embeddings)')}:"
        ),
        h.code(
            "MERGE (n:`<label>` { node_index: $node_index })\n"
            "ON MATCH\n"
            "    SET n.embeddings = $embeddings\n"
            "RETURN n.node_index"
        ),
        *h.bullets([
            f"The label is normalised through {h.c('normalize_node_label()')} "
            "and interpolated into the Cypher with backticks (the same "
            "pattern as Section 2).",
            f"{h.c('node_index')} (not {h.c('node_id')}) is the upsert key. "
            f"The numpy {h.c('ndarray')} is converted to a plain list via "
            f"{h.c('get_or_default_ndarray()')} so the Neo4j driver can "
            "serialise it.",
            f"<b>Note</b> the use of {h.c('ON MATCH')} only &mdash; if the node "
            f"does not already exist, {h.c('MERGE')} creates a bare node with "
            f"just the {h.c('node_index')} property and <i>no</i> "
            f"{h.c('embeddings')}. The expectation is that foundational "
            "ingest has already created the node; the embedding step "
            "decorates it.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 5. FastRP
    story += [
        h.p("5. (Optional) FastRP training", h.H1),
        h.p(
            f"{h.c('src/foundation/infra/db/adapter/neo4j_train_embeddings_adapter.py')}",
            h.PATH,
        ),
        h.p(
            f"FastRP (Fast Random Projection) is a GDS-native graph "
            f"embedding algorithm. It is <i>not</i> required for the live "
            f"endpoint; the call to {h.c('train_fastrp_with_write()')} is an "
            "offline step that decorates each projected node with a "
            "low-dimensional vector that downstream consumers (e.g. "
            "vector-index-based recommenders, link prediction models) can "
            "use."
        ),
        h.p("Training Cypher (lines ~101-121)", h.H2),
        h.code(
            "CALL gds.fastRP.write(\n"
            "    'eugene_similarity_graph',\n"
            "    {\n"
            "        embeddingDimension: 512,\n"
            "        writeProperty: 'prediction_embeddings',\n"
            "        iterationWeights: [0, .6, .8],\n"
            "        normalizationStrength: -0.5,\n"
            "        randomSeed: 75,\n"
            "        featureProperties: ['embeddings', 'label_one_hot_encoding'],\n"
            "        propertyRatio: .50\n"
            "    }\n"
            ")\n"
            "YIELD nodePropertiesWritten"
        ),
        *h.bullets([
            f"<b>{h.c('embeddingDimension: 512')}</b> matches the default of "
            f"the {h.c('train_fastrp_with_write()')} parameter.",
            f"<b>{h.c('iterationWeights: [0, .6, .8]')}</b> &mdash; three "
            "iterations of message-passing. The zero weight on iteration 0 "
            "means the initial node features alone do not enter the output; "
            "1-hop and 2-hop neighbourhoods carry weight 0.6 and 0.8.",
            f"<b>{h.c('featureProperties')}</b> includes "
            f"{h.c('embeddings')} (from Section 4) and "
            f"{h.c('label_one_hot_encoding')} (written by "
            f"{h.c('Neo4jOnehotEncodingAdapter')}, out of scope here). "
            f"{h.c('propertyRatio: .50')} blends them with the random "
            "projection signal.",
            f"<b>{h.c('randomSeed: 75')}</b> is hard-coded so reruns are "
            "deterministic.",
            f"Output goes to a {h.c('prediction_embeddings')} property on "
            f"each projected node ({h.c('GRAPH_EMBEDDINGS_FIELD_NAME')} in "
            f"{h.c('src/foundation/conf/const.py:5')}).",
        ]),
        h.p("Companion vector index", h.H2),
        h.p(
            f"{h.c('create_embedding_index()')} (line ~48) issues a "
            f"{h.c('CREATE VECTOR INDEX')} with "
            f"{h.c('vector.similarity_function: &apos;cosine&apos;')} so the "
            f"{h.c('prediction_embeddings')} can be used by a future "
            "vector-search path (not wired into the current router)."
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 6. response
    story += [
        h.p("6. Response mapper &amp; model", h.H1),
        h.p(
            f"{h.c('src/foundation/router/response_util.py')} &mdash; "
            f"{h.c('to_similarity_response()')} at line ~42",
            h.PATH,
        ),
        h.code(
            "def to_similarity_response(dataframe):\n"
            "    if dataframe is None:\n"
            "        return SimilarityResponse(count=0, results=[])\n"
            "    results = []\n"
            "    for index, row in dataframe.iterrows():\n"
            "        results.append(SimilarNodes(\n"
            "            score=row[\"similarity\"],\n"
            "            id1=row[\"id1\"], id2=row[\"id2\"],\n"
            "            name1=row[\"name1\"], name2=row[\"name2\"],\n"
            "        ))\n"
            "    return SimilarityResponse(\n"
            "        count=len(results), results=results)"
        ),
        h.p("Pydantic models", h.H2),
        h.p(
            f"{h.c('src/foundation/router/model/similarity_response.py')}:"
        ),
        h.code(
            "class SimilarNodes(BaseModel):\n"
            "    score: float\n"
            "    id1: str\n"
            "    name1: str\n"
            "    id2: str\n"
            "    name2: str\n"
            "\n"
            "class SimilarityResponse(BaseModel):\n"
            "    count: int\n"
            "    results: list[SimilarNodes]"
        ),
        h.p("Example response", h.H2),
        h.code(
            "{\n"
            "  \"count\": 3,\n"
            "  \"results\": [\n"
            "    { \"score\": 0.87, \"id1\": \"DIS:0001\", \"name1\": \"Lupus\",\n"
            "                       \"id2\": \"DIS:0042\", \"name2\": \"Sjogren syndrome\" },\n"
            "    { \"score\": 0.71, \"id1\": \"DIS:0001\", \"name1\": \"Lupus\",\n"
            "                       \"id2\": \"DIS:0099\", \"name2\": \"Rheumatoid arthritis\" },\n"
            "    { \"score\": 0.52, \"id1\": \"DIS:0001\", \"name1\": \"Lupus\",\n"
            "                       \"id2\": \"DIS:0107\", \"name2\": \"Scleroderma\" }\n"
            "  ]\n"
            "}"
        ),
        *h.bullets([
            f"{h.c('score')} is the raw GDS {h.c('similarity')} (cosine in "
            "[0,1]); no further normalisation.",
            f"{h.c('id1')}/{h.c('id2')} come from {h.c('node_id')} via "
            f"{h.c('toStringOrNull')} so the response field is always a "
            "string even if the underlying property is numeric.",
            f"The handler is decorated with "
            f"{h.c('response_model_exclude_none=True')} &mdash; any null fields "
            "are elided. In practice all five fields are populated by the "
            "Cypher projection above.",
            f"The mapper does <b>not</b> deduplicate (a, b) vs (b, a). The "
            f"{h.c('sourceNodeFilter')} pins the source side to the matched "
            "anchor, so both orderings should not appear unless the "
            "anchor regex matches both nodes of a pair.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 7. debug walk
    story += [
        h.p("7. Suggested debugging walk", h.H1),
        *h.bullets([
            f"<b>Step 1 &mdash; bring up the stack.</b> "
            f"{h.c('docker-compose up eugene_neo4j eugene_ws')}. Confirm "
            f"{h.c('.env')} points the API at the right Neo4j and that the "
            f"GDS plugin is installed (Neo4j Browser: "
            f"{h.c('RETURN gds.version()')}).",
            f"<b>Step 2 &mdash; verify the projection exists.</b> Open Neo4j "
            f"Browser and run "
            f"{h.c('CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount')}. "
            f"You must see {h.c('eugene_similarity_graph')} with non-zero "
            f"counts. If it is missing, run the orchestrator that calls "
            f"{h.c('Neo4jProjectSimilarityGraphAdapter.project_similarity_graph(replace=True)')} "
            "(Section 3) before retrying the endpoint.",
            f"<b>Step 3 &mdash; (optional) refresh embeddings.</b> Only if you "
            f"plan to consume {h.c('prediction_embeddings')} elsewhere: "
            f"re-run the foundational embedding ingest "
            f"({h.c('FoundationalNodeEmbeddingProvider')} &rarr; "
            f"{h.c('Neo4jFoundationalNodeAdapter.upsert_embeddings')}) and "
            f"then {h.c('Neo4jTrainEmbeddingsAdapter.train_fastrp_with_write(SIMILARITY_GRAPH_PROJECTION_NAME)')}.",
            f"<b>Step 4 &mdash; curl the endpoint.</b> "
            f"{h.c('curl -sS -X POST http://localhost:8000/similarity/disease -H &apos;Content-Type: application/json&apos; -d &apos;{&quot;values&quot;: [&quot;lupus&quot;]}&apos; | jq .')}. "
            "Expect a JSON document matching Section 6. Empty results "
            "usually means either the projection is missing, the regex "
            f"matched no anchor, or all pairs fell below the {h.c('0.45')} "
            "cutoff.",
            f"<b>Step 5 &mdash; breakpoint sweep.</b> Set breakpoints at "
            f"{h.c('similarity_router.py:48')} (inspect the parsed "
            f"{h.c('label.value')} and request body), "
            f"{h.c('neo4j_foundational_similarity_adapter.py:36')} (log the "
            f"assembled {h.c('query')} string &mdash; copy it into Neo4j "
            f"Browser to see the raw rows before DataFrame conversion), and "
            f"{h.c('response_util.py:49')} (watch the row-by-row Pydantic "
            "mapping).",
            f"<b>Step 6 &mdash; force a known failure.</b> Try "
            f"{h.c('POST /similarity/gene_protein')} &mdash; FastAPI should "
            f"return a 422 because {h.c('gene_protein')} is not a member of "
            f"{h.c('FacetLabel')}. Then call the adapter directly from a "
            f"Python shell with {h.c('FoundationalNodeEnum.GENE_PROTEIN')} "
            f"to hit the {h.c('ValueError')} guard at "
            f"{h.c('neo4j_foundational_similarity_adapter.py:62')}.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 8. index
    story += [
        h.p("8. Reference index", h.H1),
        h.code(
            "HTTP entry\n"
            "  src/foundation/router/similarity_router.py        # router + DI L28, handler L31-58\n"
            "  src/foundation/router/model/facet_label.py        # FacetLabel enum (drug, disease)\n"
            "  src/foundation/router/model/similarity_search_values.py\n"
            "  src/foundation/router/validate_util.py            # validate_label L13-21, str_to_label_enum\n"
            "\n"
            "DI / wiring\n"
            "  src/foundation/conf/conf.py                       # factory L177-184\n"
            "  src/foundation/conf/const.py                      # SIMILARITY_GRAPH_PROJECTION_NAME\n"
            "\n"
            "Query adapter (live request path)\n"
            "  src/foundation/infra/db/adapter/\n"
            "      neo4j_foundational_similarity_adapter.py      # _build_similarity_query L51-96\n"
            "  src/graph/util/util.py                            # ensure_connection\n"
            "  src/graph/util/node_util.py                       # normalize_node_label\n"
            "\n"
            "Projection (offline; required before endpoint works)\n"
            "  src/foundation/infra/db/adapter/\n"
            "      neo4j_project_similarity_graph_adapter.py     # project_similarity_graph L31-66\n"
            "  src/foundation/infra/db/adapter/neo4j_project_graph_adapter.py\n"
            "\n"
            "Embedding pipeline (offline; feeds FastRP, not the endpoint)\n"
            "  src/foundation/infra/embedding/\n"
            "      foundational_node_embedding_provider.py       # SentenceTransformer / model2vec\n"
            "  src/foundation/infra/db/adapter/\n"
            "      neo4j_foundational_node_adapter.py            # upsert_embeddings L50-89\n"
            "\n"
            "FastRP training (optional)\n"
            "  src/foundation/infra/db/adapter/\n"
            "      neo4j_train_embeddings_adapter.py             # train_fastrp_with_write L25-46\n"
            "                                                    # create_embedding_index  L48-68\n"
            "\n"
            "Response\n"
            "  src/foundation/router/response_util.py            # to_similarity_response L42-59\n"
            "  src/foundation/router/model/similarity_response.py\n"
            "\n"
            "Schema enums\n"
            "  src/foundation/model/foundational_node_enum.py    # DRUG, DISEASE, ...\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
        ),
    ]

    return story
