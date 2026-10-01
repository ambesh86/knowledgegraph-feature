"""Per-route flow guide for Eugene's TPP (target product profile) search router.

Produces EUGENE_TPP_SEARCH_FLOW_GUIDE.pdf. Loaded by
generate_route_flow_guides.py via the dispatcher.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_TPP_SEARCH_FLOW_GUIDE.pdf"
TITLE = "Eugene TPP Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------------------------------------------- cover
    story += [
        h.p(
            "Eugene TPP Search &mdash; End-to-End Flow",
            h.H_TITLE,
        ),
        h.p(
            "Developer walkthrough: pptx ETL &rarr; "
            f"{h.c(':csl_tpp')} + {h.c(':csl_tpp_question')} subgraph &rarr; "
            f"Neo4j vector index ({h.c('db.index.vector.queryNodes')}) &rarr; "
            f"FastAPI router under {h.c('/embeddings')} &rarr; "
            f"{h.c('SearchResponse')}.",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene matches a "
            "<b>Target Product Profile</b> (TPP) &mdash; a CSL-Behring asset "
            "definition slide &mdash; against the USPTO patent-application "
            f"corpus ({h.c(':USPTO_PGPUB')} nodes) using Neo4j native vector "
            "indexes. The four routes on this router are all variations on "
            "the same theme: pick an embedding source (free-text, the TPP "
            "node, its FastRP graph embedding, or one of its question nodes) "
            "and stream the top patent matches through the same vector "
            f"index. Every reference uses the form {h.c('path/to/file.py:line')}."
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('POST /embeddings/')} body "
            f"{h.c('{&quot;include_terms&quot;: &quot;Hemophilia A non-viral, in vivo GenM&quot;, &quot;exclude_terms&quot;: &quot;von Willebrand Disease&quot;}')} "
            "&mdash; ad-hoc free-text search; the include/exclude terms are "
            f"merged through {h.c('SemanticSearchEmbeddingProvider.to_embedding')} "
            "before hitting the vector index.",
            f"{h.c('GET /embeddings/tpps/{tpp_id}')} &mdash; anchor on an "
            f"existing {h.c(':csl_tpp')} node and search against the patent "
            f"text embedding index ({h.c('pgpub_embeddings_index')}).",
            f"{h.c('GET /embeddings/tpps/{tpp_id}/graph')} &mdash; same "
            f"anchor, but query the patent <b>graph</b> embedding index "
            f"({h.c('pgpub_prediction_embeddings_index')}) using the TPP&apos;s "
            f"own {h.c('prediction_embeddings')} property (FastRP, see "
            "Section 4).",
            f"{h.c('GET /embeddings/tpps/{tpp_id}/question/{question_type}')} "
            "&mdash; narrow the anchor to a single question node "
            f"({h.c(':csl_tpp_question')}) on the TPP, e.g. "
            f"{h.c('INDICATION')} or {h.c('MECHANISM_OF_ACTION')}, and "
            "search with that question&apos;s targeted embedding.",
        ]),
        h.p("Caveat &mdash; not registered in eugene_ws", h.H2),
        h.p(
            f"At the time of writing, {h.c('src/eugene_ws.py')} (the FastAPI "
            f"app factory in {h.c('add_routers()')}, lines 31-78) "
            f"<b>does not</b> import {h.c('tpp.router.search_router')}. The "
            f"router is fully wired internally (module-load DI via "
            f"{h.c('tpp.conf.eugene_ws_conf.tpp_search_orchestrator()')}), "
            f"the orchestrator and adapters are tested, but the router is "
            f"not included by the core API. Treat this guide as the design "
            "doc for the route; before exercising it over HTTP you must "
            f"add {h.c('from tpp.router import search_router')} and append "
            f"it to the {h.c('routers')} list, or mount it on a separate "
            "FastAPI app."
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Section 0 explains the TPP schema and the two patent vector "
            "indexes the router targets.",
            "Sections 1&ndash;3 trace the live request: HTTP entry, query "
            "adapter (Cypher), and response mapper.",
            "Section 4 covers the offline ETL: pptx parsing, embedding, "
            f"upsert into {h.c(':csl_tpp')} / {h.c(':csl_tpp_question')} and "
            "the GDS projection that feeds graph-embedding mode.",
            "Section 5 is a step-through debugging walk.",
            "Section 6 is the file-path reference index.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 0. Schema
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "The TPP search routes touch two clusters of nodes: the "
            "CSL-Behring TPP subgraph (written by the ETL in Section 4) and "
            f"the USPTO patent-application corpus ({h.c(':USPTO_PGPUB')} "
            "nodes, ingested by a separate patent pipeline that this guide "
            "treats as a given)."
        ),
        h.code(
            "(:csl_tpp {\n"
            "    node_id,                # md5(product_description + theraputic_area + question_types)\n"
            "    node_index,             # KSUID, set once at creation\n"
            "    product_description,    # cleaned text from the pptx slide\n"
            "    threaputic_area,        # TheraputicAreaEnum.name (usually UNKNOWN)\n"
            "    embeddings,             # merged sentence-transformer vector\n"
            "    prediction_embeddings,  # written by FastRP (Section 4)\n"
            "    refresh_date,\n"
            "    is_csl = true\n"
            "})\n"
            "\n"
            "(:csl_tpp_question {\n"
            "    node_id,                # md5(question_type + ideal + acceptable + excluded)\n"
            "    node_index,\n"
            "    question_type,          # QuestionTypeEnum.name, e.g. INDICATION\n"
            "    ideal, acceptable, excluded,\n"
            "    embeddings,             # include-minus-exclude merged vector\n"
            "    refresh_date,\n"
            "    is_csl = true\n"
            "})\n"
            "\n"
            "(:csl_tpp)-[:has_associated_question { is_csl: true }]-(:csl_tpp_question)\n"
            "\n"
            "(:USPTO_PGPUB {\n"
            "    application_number_text,    # returned as patent_application_no\n"
            "    abstract,\n"
            "    claims,                     # list[str]\n"
            "    embeddings,                 # indexed by pgpub_embeddings_index\n"
            "    prediction_embeddings       # indexed by pgpub_prediction_embeddings_index\n"
            "})"
        ),
        *h.bullets([
            f"<b>Labels.</b> {h.c('CSL_TPP')} and {h.c('CSL_TPP_QUESTION')} "
            f"are declared in "
            f"{h.c('src/foundation/model/foundational_node_enum.py:42-43')} "
            f"(entries {h.c('300')} / {h.c('301')}). They are stored on disk "
            f"as the lowercase strings {h.c('csl_tpp')} / "
            f"{h.c('csl_tpp_question')} via "
            f"{h.c('normalize_node_label()')} in "
            f"{h.c('src/tpp/infra/db/const.py:4-5')}.",
            f"<b>Relationship.</b> {h.c(':has_associated_question')} "
            f"(constant {h.c('TPP_QUESTION_REL_TYPE')} in "
            f"{h.c('src/tpp/infra/db/const.py:7')}). Carries "
            f"{h.c('is_csl: true')} to distinguish CSL assets from any "
            "future external TPP imports.",
            f"<b>{h.c('tpp_id')} == {h.c('node_id')}.</b> The router&apos;s "
            f"path parameter is the md5 hex digest produced by "
            f"{h.c('Neo4jTppAdapter._generate_tpp_composite_node_id()')} "
            f"({h.c('neo4j_tpp_adapter.py:206-223')}). FastAPI&apos;s "
            f"{h.c('Path(...)')} pins it at exactly 32 characters &mdash; see "
            "Section 1.",
            f"<b>Two patent vector indexes.</b> "
            f"{h.c('USPTO_PGPUB_EMBEDDINGS_INDEX_NAME = &quot;pgpub_embeddings_index&quot;')} "
            f"and "
            f"{h.c('USPTO_PGPUB_GRAPH_EMBEDDINGS_INDEX_NAME = &quot;pgpub_prediction_embeddings_index&quot;')} "
            f"({h.c('src/patent/pgpub/infra/db/const.py:9-10')}). The first "
            f"is built from text embeddings on {h.c('USPTO_PGPUB.embeddings')}; "
            f"the second from FastRP graph embeddings on "
            f"{h.c('USPTO_PGPUB.prediction_embeddings')}.",
            f"<b>Field-name constants.</b> "
            f"{h.c('EMBEDDINGS_FIELD_NAME = &quot;embeddings&quot;')} and "
            f"{h.c('GRAPH_EMBEDDINGS_FIELD_NAME = &quot;prediction_embeddings&quot;')} "
            f"in {h.c('src/foundation/conf/const.py:4-5')}. The adapter "
            "interpolates both the index name and the field name into the "
            "Cypher, so they must agree across both ends.",
            f"<b>No Neo4j CONSTRAINTs.</b> Idempotency relies on "
            f"{h.c('MERGE')} on {h.c('node_id')} in "
            f"{h.c('Neo4jTppAdapter._generate_tpp_upsert()')} "
            f"({h.c('neo4j_tpp_adapter.py:93-112')}). Do not assume database-"
            "level uniqueness.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 1. HTTP entry
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p(f"{h.c('src/tpp/router/search_router.py')}", h.PATH),
        h.p("Module-load dependency injection", h.H2),
        h.p(
            "Lines 26-27 of the router build both the orchestrator and the "
            "free-text embedding provider once at import time:"
        ),
        h.code(
            "search_orchestrator = tpp_search_orchestrator()\n"
            "embedding_provider  = semantic_search_embedding_provider()"
        ),
        h.p(
            f"The factories live in {h.c('src/tpp/conf/eugene_ws_conf.py')}:"
        ),
        h.code(
            "def tpp_search_orchestrator() -> TppSearchOrchestrator:\n"
            "    driver = _neo4j_driver()\n"
            "    return _tpp_search_orchestrator(\n"
            "        neo4j_pgpub_search_adapter=_neo4j_pgpub_search_adapter(driver),\n"
            "        neo4j_tpp_search_adapter=_neo4j_tpp_search_adapter(driver),\n"
            "    )\n"
            "\n"
            "def semantic_search_embedding_provider()\n"
            "        -> SemanticSearchEmbeddingProvider:\n"
            "    return _semantic_search_embedding_provider(\n"
            "        embedding_merger=embedding_merger())"
        ),
        *h.bullets([
            f"One {h.c('neo4j.Driver')} is shared between "
            f"{h.c('Neo4jTppSearchAdapter')} and "
            f"{h.c('Neo4jPgpubSearchAdapter')} &mdash; the same DI pattern as "
            "the rest of Eugene (no FastAPI Depends, no per-request "
            "construction).",
            f"The driver comes from "
            f"{h.c('GraphDbConnectionFactory.remote_neo4j_instance_from_env()')} "
            f"(env vars resolved by {h.c('.env')}).",
            f"{h.c('SemanticSearchEmbeddingProvider')} is only used by the "
            f"free-text {h.c('POST /')} route; the three GET routes never "
            "call it because the anchor TPP node already carries its own "
            f"{h.c('embeddings')}.",
        ]),
        h.p("Router prefix and the four handlers", h.H2),
        h.code(
            "router = APIRouter(prefix=\"/embeddings\", tags=[\"embeddings\"])\n"
            "\n"
            "@router.post(\"/\", response_model=SearchResponse,\n"
            "             response_model_exclude_none=True)\n"
            "async def find_patents_by_embeddings(\n"
            "    embedding_search_params: EmbeddingSearchParams):\n"
            "    merged_embeddings = embedding_provider.to_embedding(\n"
            "        include_terms=embedding_search_params.include_terms,\n"
            "        exclude_terms=embedding_search_params.exclude_terms,\n"
            "    )\n"
            "    results = search_orchestrator\\\n"
            "        .find_patent_applications_by_embedding(merged_embeddings)\n"
            "    return to_search_response(results)\n"
            "\n"
            "@router.get(\"/tpps/{tpp_id}\", ...)\n"
            "async def find_patents_by_tpp_id(\n"
            "    tpp_id: Annotated[str, Path(..., max_length=32,\n"
            "                                     min_length=32)]):\n"
            "    results = search_orchestrator\\\n"
            "        .find_patent_applications_by_tpp(tpp_id=tpp_id)\n"
            "    return to_search_response(results)\n"
            "\n"
            "@router.get(\"/tpps/{tpp_id}/graph\", ...)\n"
            "async def find_patents_by_tpp_id_and_graph_embeddings(...): ...\n"
            "\n"
            "@router.get(\"/tpps/{tpp_id}/question/{question_type}\", ...)\n"
            "async def find_patents_by_tpp_id_and_question_embeddings(\n"
            "    tpp_id: Annotated[str, Path(..., max_length=32, min_length=32)],\n"
            "    question_type: Annotated[str, Path(...),\n"
            "                             AfterValidator(validate_question_type)],\n"
            "):\n"
            "    question = to_question_enum(question_type)\n"
            "    results = search_orchestrator\\\n"
            "        .find_patent_applications_by_tpp_question(\n"
            "            tpp_id=tpp_id, tpp_question=question)\n"
            "    return to_search_response(results)"
        ),
        h.p("Path and body validators", h.H2),
        *h.bullets([
            f"<b>{h.c('tpp_id')}.</b> All three GET handlers pin "
            f"{h.c('max_length=32, min_length=32')}. FastAPI returns a 422 "
            f"automatically for any other length &mdash; this is the only "
            f"sanitisation on the path. Note: no character-class check, but "
            f"{h.c('tpp_id')} is bound straight into a Cypher parameter "
            f"({h.c('$node_id')}), not interpolated, so injection is not "
            "possible.",
            f"<b>{h.c('question_type')}.</b> Validated by "
            f"{h.c('validate_question_type')} in "
            f"{h.c('src/tpp/router/search_util.py:46-48')} which delegates to "
            f"{h.c('to_question_enum()')} (lines 31-43). It uppercases the "
            f"value and looks it up in {h.c('QuestionTypeEnum[...]')}; an "
            f"unknown key raises {h.c('ValueError')}, which FastAPI surfaces "
            "as a 422 with the list of valid types in the message:",
            f"&nbsp;&nbsp;&nbsp;&nbsp;{h.c('[UNKNOWN, INDICATION, CONTRAINDICATION, MECHANISM_OF_ACTION, ROUTE_OF_ADMINISTRATION, EFFICACY, SAFTEY_AND_TOLERABILITY, COST_OF_GOODS_SOLD]')} &mdash; "
            f"see {h.c('src/tpp/model/question_type_enum.py:4-12')}. "
            f"(Yes, {h.c('SAFTEY')} is the spelling on disk; if you fix it "
            "you also fix the data.)",
            f"<b>{h.c('EmbeddingSearchParams')}.</b> Pydantic model in "
            f"{h.c('src/tpp/router/search_util.py:15-28')} with two fields, "
            f"{h.c('include_terms: str')} and "
            f"{h.c('exclude_terms: str | None')}. No validators &mdash; the "
            f"strings are passed verbatim to the sentence-transformer in "
            f"{h.c('SemanticSearchEmbeddingProvider.to_embedding()')}. "
            f"Unlike the foundational search routes, the TPP router does "
            f"<b>not</b> reuse {h.c('validate_value()')} from "
            f"{h.c('src/foundation/router/validate_util.py:35-42')}.",
            f"<b>No {h.c('AfterValidator')} for the body.</b> "
            f"{h.c('validate_question_type')} is the only "
            f"{h.c('AfterValidator')} on the router (line 98 of "
            f"{h.c('search_router.py')}). Free-text input bypasses it.",
        ]),
        h.p("Set your first breakpoint", h.H2),
        h.p(
            f"At {h.c('search_router.py:101')} (the "
            f"{h.c('question = to_question_enum(question_type)')} line) you "
            f"can inspect the validated enum value before the orchestrator "
            f"call. For the free-text route, break at "
            f"{h.c('search_router.py:34')} to inspect the merged ndarray "
            "before it hits the patent vector index."
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 2. adapter / cypher
    story += [
        h.p("2. Query adapter &mdash; the vector-index Cypher", h.H1),
        h.p(
            f"{h.c('src/tpp/provider/tpp_search_orchestrator.py')} &amp; "
            f"{h.c('src/tpp/infra/db/adapter/neo4j_tpp_search_adapter.py')}",
            h.PATH,
        ),
        h.p("Orchestrator fan-out", h.H2),
        h.p(
            f"{h.c('TppSearchOrchestrator')} (lines 16-81) holds two "
            "adapters and chooses one per route:"
        ),
        *h.bullets([
            f"{h.c('find_patent_applications_by_embedding(ndarray)')} &rarr; "
            f"{h.c('Neo4jPgpubSearchAdapter.find_by_embeddings(...)')} &mdash; "
            f"the only route that goes through the pgpub adapter; the "
            f"adapter wraps the vector array as a "
            f"{h.c('TppSearchResult(score, application_no)')} (no "
            f"abstract/claims). Mapping happens at lines 41-47.",
            f"{h.c('find_patent_applications_by_tpp(tpp_id)')} &rarr; "
            f"{h.c('Neo4jTppSearchAdapter.find_by_tpp(tpp_id)')} &mdash; text "
            "vector mode.",
            f"{h.c('find_patent_applications_by_tpp_and_graph_embeddings(tpp_id)')} "
            f"&rarr; {h.c('Neo4jTppSearchAdapter.find_by_tpp_and_graph_embeddings(tpp_id)')} "
            "&mdash; FastRP graph-embedding mode.",
            f"{h.c('find_patent_applications_by_tpp_question(tpp_id, tpp_question)')} "
            f"&rarr; {h.c('Neo4jTppSearchAdapter.find_by_tpp_question(...)')} "
            "&mdash; per-question text vector mode.",
            f"{h.c('None')} on any required arg short-circuits to "
            f"{h.c('None')} before opening a session &mdash; the router "
            f"surfaces this as an empty {h.c('SearchResponse')} via "
            f"{h.c('to_search_response(None)')}.",
        ]),
        h.p("Cypher 1 &mdash; find_by_tpp (text embedding)", h.H2),
        h.p(
            f"{h.c('Neo4jTppSearchAdapter._generate_find_by_tpp_id_query()')} "
            f"({h.c('neo4j_tpp_search_adapter.py:171-181')}); "
            f"{h.c('limit=200')}:"
        ),
        h.code(
            "MATCH (tpp:`csl_tpp` { node_id: $node_id })\n"
            "CALL db.index.vector.queryNodes('pgpub_embeddings_index',\n"
            "                                200, tpp.embeddings)\n"
            "YIELD node, score\n"
            "RETURN score,\n"
            "       tpp.product_description       AS tpp_description,\n"
            "       node.application_number_text  AS patent_application_no,\n"
            "       node.abstract                 AS patent_abstract,\n"
            "       node.claims                   AS patent_claims"
        ),
        h.p("Cypher 2 &mdash; find_by_tpp_question", h.H2),
        h.p(
            f"{h.c('_generate_find_by_tpp_question_query(question_type)')} "
            f"({h.c('neo4j_tpp_search_adapter.py:183-196')}). The "
            f"{h.c('question_type.name.upper()')} is spliced directly into "
            "the Cypher string &mdash; safe because the enum is validated "
            "upstream (Section 1):"
        ),
        h.code(
            "MATCH (tpp:`csl_tpp` { node_id: $node_id })\n"
            "      -[:has_associated_question]-\n"
            "      (tpp_question:`csl_tpp_question`\n"
            "                    { question_type: 'INDICATION' })\n"
            "CALL db.index.vector.queryNodes('pgpub_embeddings_index',\n"
            "                                200, tpp_question.embeddings)\n"
            "YIELD node, score\n"
            "RETURN score,\n"
            "       tpp.product_description       AS tpp_description,\n"
            "       node.application_number_text  AS patent_application_no,\n"
            "       node.abstract                 AS patent_abstract,\n"
            "       node.claims                   AS patent_claims"
        ),
        h.p("Cypher 3 &mdash; find_by_tpp_and_graph_embeddings", h.H2),
        h.p(
            f"{h.c('_generate_find_by_tpp_id_and_graph_embeddings_query()')} "
            f"({h.c('neo4j_tpp_search_adapter.py:198-210')}). Same anchor as "
            f"Cypher 1, but probes the graph vector index using the TPP&apos;s "
            f"FastRP-derived {h.c('prediction_embeddings')}:"
        ),
        h.code(
            "MATCH (tpp:`csl_tpp` { node_id: $node_id })\n"
            "CALL db.index.vector.queryNodes('pgpub_prediction_embeddings_index',\n"
            "                                200, tpp.prediction_embeddings)\n"
            "YIELD node, score\n"
            "RETURN score,\n"
            "       tpp.product_description       AS tpp_description,\n"
            "       node.application_number_text  AS patent_application_no,\n"
            "       node.abstract                 AS patent_abstract,\n"
            "       node.claims                   AS patent_claims;"
        ),
        h.p("Anatomy", h.H2),
        *h.bullets([
            f"<b>{h.c('db.index.vector.queryNodes(indexName, k, queryVector)')}.</b> "
            f"Neo4j&apos;s built-in vector index probe. The index must already "
            f"exist on {h.c(':USPTO_PGPUB')} for the matching field; the "
            f"score is cosine-similarity in {h.c('[0, 1]')} (configured at "
            "index creation time on the patent ingest side).",
            f"<b>Hard-coded {h.c('limit=200')}.</b> Both index queries take "
            f"the top 200 nearest patents. There is no pagination, no "
            f"client-controlled {h.c('k')}, and the {h.c('limit')} keyword "
            "is built into the SQL builder.",
            f"<b>Parameter usage.</b> Only {h.c('$node_id')} is bound (the "
            f"sanitised 32-char path arg); index names, k, and field names "
            f"are interpolated at query-build time from "
            f"{h.c('USPTO_PGPUB_*_INDEX_NAME')} / "
            f"{h.c('*_FIELD_NAME')} constants, so they cannot drift across "
            "deployments.",
            f"<b>Backticked labels.</b> {h.c(':`csl_tpp`')} and "
            f"{h.c(':`csl_tpp_question`')} use backticks so the lowercase "
            f"label survives the parser (and matches the on-disk label "
            f"normalised by {h.c('TPP_NODE_TYPE')} in "
            f"{h.c('src/tpp/infra/db/const.py:4-5')}).",
            f"<b>Errors.</b> The transaction body catches "
            f"{h.c('DriverError')} and {h.c('Neo4jError')}, logs the query, "
            f"and re-raises &mdash; FastAPI surfaces them as 500. The router "
            f"itself has no {h.c('try/except')}.",
        ]),
        h.p("Transaction shape", h.H2),
        h.p(
            f"All three TPP-anchored queries flow through "
            f"{h.c('_wrap_tx()')} "
            f"({h.c('neo4j_tpp_search_adapter.py:212-227')}): open a "
            f"session, open an explicit {h.c('begin_transaction()')}, run "
            f"the query callable, return its mapped list. "
            f"{h.c('find_by_tpp_question')} reimplements the wrap inline "
            f"({h.c('neo4j_tpp_search_adapter.py:40-49')}) because it needs "
            f"to pass the {h.c('question_type')} into the closure."
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 3. response
    story += [
        h.p("3. Mapper &amp; response model", h.H1),
        h.p(
            f"{h.c('src/tpp/infra/db/model/tpp_search_result.py')} &amp; "
            f"{h.c('src/tpp/router/search_util.py')}",
            h.PATH,
        ),
        h.p("Row &rarr; TppSearchResult", h.H2),
        h.p(
            f"{h.c('Neo4jTppSearchAdapter._convert_results()')} "
            f"({h.c('neo4j_tpp_search_adapter.py:229-247')}) is the only "
            "mapper for the three TPP-anchored routes:"
        ),
        h.code(
            "for record in records:\n"
            "    results.append(TppSearchResult(\n"
            "        score=float(record[\"score\"]),\n"
            "        application_no=record[\"patent_application_no\"],\n"
            "        product_description=record[\"tpp_description\"],\n"
            "        abstract=record[\"patent_abstract\"],\n"
            "        claims=record[\"patent_claims\"],\n"
            "    ))"
        ),
        h.p(
            f"For the free-text {h.c('POST /')} route, the orchestrator "
            f"builds a thinner {h.c('TppSearchResult(score, application_no)')} "
            f"inline ({h.c('tpp_search_orchestrator.py:41-47')}); "
            f"{h.c('product_description')}, {h.c('abstract')} and "
            f"{h.c('claims')} are omitted and elided by "
            f"{h.c('response_model_exclude_none=True')}."
        ),
        h.p("Pydantic models", h.H2),
        h.code(
            "class TppSearchResult(BaseModel):\n"
            "    score: float | None              = None\n"
            "    application_no: str | None       = None\n"
            "    product_description: str | None  = None\n"
            "    abstract: str | None             = None\n"
            "    claims: list[str] | None         = None\n"
            "\n"
            "class SearchResponse(BaseModel):\n"
            "    count: int\n"
            "    results: list[TppSearchResult]"
        ),
        h.p(
            f"{h.c('to_search_response(results)')} "
            f"({h.c('search_util.py:51-57')}) wraps a "
            f"{h.c('None')} or empty list as "
            f"{h.c('SearchResponse(count=0, results=[])')} &mdash; never a "
            "404. Hash &amp; equality on "
            f"{h.c('TppSearchResult')} ({h.c('tpp_search_result.py:11-22')}) "
            f"key off {h.c('(score, application_no)')} only, so a result "
            "set is deduplicable downstream even when the heavyweight "
            "fields differ."
        ),
        h.p("Example response &mdash; GET /embeddings/tpps/{tpp_id}", h.H2),
        h.code(
            "{\n"
            "  \"count\": 3,\n"
            "  \"results\": [\n"
            "    { \"score\": 0.91,\n"
            "      \"application_no\": \"US20230012345A1\",\n"
            "      \"product_description\": \"Hemophilia A non-viral, in vivo gene therapy.\",\n"
            "      \"abstract\": \"A method for delivering Factor VIII ...\",\n"
            "      \"claims\": [\"1. A composition comprising ...\",\n"
            "                  \"2. The composition of claim 1 ...\"] },\n"
            "    { \"score\": 0.83,\n"
            "      \"application_no\": \"US20220098765A1\",\n"
            "      \"product_description\": \"Hemophilia A non-viral, in vivo gene therapy.\",\n"
            "      \"abstract\": \"Lipid nanoparticle formulations encoding ...\",\n"
            "      \"claims\": [\"1. A lipid nanoparticle ...\"] },\n"
            "    { \"score\": 0.77,\n"
            "      \"application_no\": \"US20210045678A1\",\n"
            "      \"product_description\": \"Hemophilia A non-viral, in vivo gene therapy.\",\n"
            "      \"abstract\": \"AAV-free delivery of clotting factors ...\",\n"
            "      \"claims\": [\"1. A method comprising ...\"] }\n"
            "  ]\n"
            "}"
        ),
        h.p("Example response &mdash; POST /embeddings/ (free text)", h.H2),
        h.code(
            "{\n"
            "  \"count\": 2,\n"
            "  \"results\": [\n"
            "    { \"score\": 0.88, \"application_no\": \"US20230012345A1\" },\n"
            "    { \"score\": 0.74, \"application_no\": \"US20220098765A1\" }\n"
            "  ]\n"
            "}"
        ),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 4. ETL
    story += [
        h.p("4. ETL / training pipeline &mdash; building the TPP subgraph", h.H1),
        h.p(
            f"{h.c('src/tpp/mapper/tpp_mapper.py')}, "
            f"{h.c('src/tpp/infra/embedding/tpp_embedding_provider.py')}, "
            f"{h.c('src/tpp/provider/tpp_orchestrator.py')}, "
            f"{h.c('src/tpp/infra/db/adapter/neo4j_tpp_adapter.py')}, "
            f"{h.c('src/tpp/provider/similarity_search_train_orchestrator.py')}",
            h.PATH,
        ),
        h.p(
            "The live router reads two properties that are written entirely "
            f"offline: {h.c('csl_tpp.embeddings')} / "
            f"{h.c('csl_tpp_question.embeddings')} (sentence-transformer "
            f"vectors), and {h.c('csl_tpp.prediction_embeddings')} (FastRP "
            "graph embeddings). Both flow through this pipeline."
        ),
        h.p("Step 1 &mdash; pptx parsing", h.H2),
        *h.bullets([
            f"{h.c('TppMapper.map(pptx)')} "
            f"({h.c('src/tpp/mapper/tpp_mapper.py:19-25')}) opens a "
            f"PowerPoint deck and walks every slide. A slide is recognised "
            f"as a TPP when any shape&apos;s text starts with "
            f"{h.c('&quot;Target Product Profile&quot;')} "
            f"({h.c('tpp_mapper.py:50-52')}).",
            f"For each TPP slide, the mapper concatenates the slide text "
            f"into {h.c('product_description')} (cleaned by "
            f"{h.c('_clean_tpp_product_description()')} which strips "
            f"{h.c('&quot;Confidential &mdash; Internal Use Only&quot;')}, "
            f"pipes, and the {h.c('&quot;Target Product Profile&quot;')} "
            f"marker), and walks every table looking for the question grid.",
            f"{h.c('_map_row_to_question(row)')} reads four columns &mdash; "
            f"<i>type</i>, <i>ideal</i>, <i>acceptable</i>, <i>excluded</i> "
            f"&mdash; and maps the first column through "
            f"{h.c('_map_col_to_question_type()')} into a "
            f"{h.c('QuestionTypeEnum')}. Rows whose header is not one of the "
            f"seven known labels are dropped silently.",
            f"Output is a {h.c('set[Tpp]')} (one Tpp per slide, deduped by "
            f"hash of the composite key).",
        ]),
        h.p("Step 2 &mdash; embeddings", h.H2),
        h.p(
            f"{h.c('TppEmbeddingProvider.apply_embeddings(tpp)')} "
            f"({h.c('tpp_embedding_provider.py:19-32')}) is called for "
            f"every TPP and sets the {h.c('embeddings: ndarray')} field on "
            "both the TPP and each of its questions."
        ),
        *h.bullets([
            f"<b>Base TPP embedding.</b> {h.c('_to_base_embeddings()')} "
            f"({h.c('tpp_embedding_provider.py:54-67')}) encodes "
            f"{h.c('product_description')} and "
            f"{h.c('threaputic_area.name')} via "
            f"{h.c('self.model.encode(chunks, show_progress_bar=False)')}.",
            f"<b>Per-question embedding.</b> "
            f"{h.c('_question_to_embedding()')} "
            f"({h.c('tpp_embedding_provider.py:69-79')}) builds <i>positive</i> "
            f"chunks from {h.c('(question_type.name, acceptable, ideal)')} "
            f"and a <i>negative</i> chunk from {h.c('excluded')}, then "
            f"calls {h.c('EmbeddingMerger.merge(embeddings=[pos], exclusion_embeddings=[neg])')} "
            f"to obtain an include-minus-exclude vector. Same merger is "
            f"reused for the free-text route &mdash; "
            f"{h.c('SemanticSearchEmbeddingProvider.to_embedding(include_terms, exclude_terms)')}.",
            f"<b>Final TPP embedding.</b> {h.c('to_embeddings()')} "
            f"({h.c('tpp_embedding_provider.py:34-52')}) concatenates the "
            f"base chunks with every question&apos;s positive chunks and "
            "calls the merger one last time to produce the single ndarray "
            f"stored on {h.c('csl_tpp.embeddings')}.",
        ]),
        h.p("Step 3 &mdash; upsert", h.H2),
        h.p(
            f"{h.c('TppOrchestrator.process(tpp_file)')} "
            f"({h.c('tpp_orchestrator.py:49-73')}) is the entry point. It "
            f"calls the mapper, applies embeddings, then ingests each TPP "
            f"via {h.c('Neo4jTppAdapter.upsert(tpp)')} "
            f"({h.c('neo4j_tpp_adapter.py:35-47')}). Composite "
            f"{h.c('node_id')} values are generated by "
            f"{h.c('_generate_tpp_composite_node_id()')} (md5 over the "
            f"product description, theraputic area, and the sorted question "
            f"type names) and {h.c('_generate_tpp_question_composite_node_id()')} "
            f"(md5 over question_type + ideal + acceptable + excluded). "
            f"{h.c('node_index')} is a KSUID set once at creation."
        ),
        h.p(
            f"Upsert Cypher &mdash; "
            f"{h.c('Neo4jTppAdapter._generate_tpp_upsert()')} "
            f"({h.c('neo4j_tpp_adapter.py:93-112')}):"
        ),
        h.code(
            "MERGE (tpp:`csl_tpp` { node_id: $node_id })\n"
            "ON MATCH\n"
            "    SET tpp.threaputic_area     = $threaputic_area,\n"
            "        tpp.product_description = $product_description,\n"
            "        tpp.refresh_date        = datetime(),\n"
            "        tpp.embeddings          = $embeddings\n"
            "ON CREATE\n"
            "    SET tpp.threaputic_area     = $threaputic_area,\n"
            "        tpp.product_description = $product_description,\n"
            "        tpp.refresh_date        = datetime(),\n"
            "        tpp.node_index          = $node_index,\n"
            "        tpp.embeddings          = $embeddings,\n"
            "        tpp.is_csl              = true"
        ),
        h.p(
            f"Per-question MERGE blocks "
            f"({h.c('neo4j_tpp_adapter.py:140-176')}) chain via "
            f"{h.c('WITH tpp')} and connect with "
            f"{h.c('MERGE (tpp)-[r1:`has_associated_question` { is_csl: true }]-(tpp_question)')}. "
            f"All chunks are joined into one Cypher transaction terminated "
            f"by {h.c('RETURN tpp.node_id, tpp.node_index, tpp.refresh_date')}."
        ),
        h.p("Step 4 &mdash; graph projection for FastRP", h.H2),
        h.p(
            f"The {h.c('GET /embeddings/tpps/{tpp_id}/graph')} route depends "
            f"on {h.c('csl_tpp.prediction_embeddings')} being populated by "
            f"FastRP over a GDS in-memory projection. "
            f"{h.c('SimilaritySearchTrainOrchestrator.project_for_similarity_search()')} "
            f"({h.c('src/tpp/provider/similarity_search_train_orchestrator.py:29-33')}) "
            f"projects the {h.c('SIMILARITY_GRAPH_PROJECTION_NAME')} graph "
            f"with the following labels and relationships, then a sibling "
            f"FastRP training step writes "
            f"{h.c('prediction_embeddings')} back onto each node (the same "
            f"pipeline used by {h.c('/similarity/{label}')} &mdash; see the "
            "Similarity flow guide for the FastRP Cypher):"
        ),
        h.code(
            "source_node_labels = [DISEASE, DRUG]\n"
            "target_node_labels = [ANATOMY, DISEASE, DRUG, EFFECT_PHENOTYPE,\n"
            "                      EXPOSURE, GENE_PROTEIN, PATHWAY]\n"
            "relationship_labels = [CONTRAINDICATION,\n"
            "                       DISEASE_PHENOTYPE_NEGATIVE,\n"
            "                       DISEASE_PHENOTYPE_POSITIVE,\n"
            "                       DISEASE_PROTEIN, EXPOSURE_DISEASE,\n"
            "                       INDICATION, OFF_LABEL_USE,\n"
            "                       PATHWAY_PATHWAY, PATHWAY_PROTEIN]\n"
            "self.neo4j_project_similarity_graph_adapter\\\n"
            "    .project_similarity_graph(\n"
            "        projection_graph_name=SIMILARITY_GRAPH_PROJECTION_NAME,\n"
            "        source_node_labels=source_node_labels,\n"
            "        target_node_labels=target_node_labels,\n"
            "        relationship_labels=relationship_labels,\n"
            "        replace=True,\n"
            "    )"
        ),
        *h.bullets([
            f"Note that {h.c('CSL_TPP')} is <b>not</b> in the source/target "
            f"label list &mdash; the projection only spans the foundational "
            f"medical graph. The TPP&apos;s own "
            f"{h.c('prediction_embeddings')} is therefore expected to be "
            f"written by a separate FastRP run that explicitly includes "
            f"{h.c(':csl_tpp')}; verify this in your deployment before "
            "relying on the graph route.",
            f"The patent ingest pipeline (out of scope here) creates "
            f"{h.c('pgpub_embeddings_index')} and "
            f"{h.c('pgpub_prediction_embeddings_index')} over "
            f"{h.c(':USPTO_PGPUB')}. Without those indexes, "
            f"{h.c('db.index.vector.queryNodes(...)')} in Section 2 raises "
            "&ldquo;there is no such vector schema index&rdquo;.",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 5. debug walk
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"<b>Step 1 &mdash; bring up the stack.</b> "
            f"{h.c('docker-compose up eugene_neo4j eugene_ws')}. Confirm "
            f"that both patent vector indexes exist: "
            f"{h.c('SHOW VECTOR INDEXES YIELD name')} in Neo4j Browser "
            f"should list {h.c('pgpub_embeddings_index')} and "
            f"{h.c('pgpub_prediction_embeddings_index')}. If the router is "
            f"not registered (see the Caveat in the cover), temporarily "
            f"include it in {h.c('add_routers()')} of "
            f"{h.c('src/eugene_ws.py')}.",
            f"<b>Step 2 &mdash; load TPPs.</b> Drop a CSL pptx into the "
            f"watched ingest folder and run the TPP orchestrator entry "
            f"point. Breakpoint at "
            f"{h.c('tpp_orchestrator.py:61')} to watch "
            f"{h.c('TppMapper.map')} parse one slide, then at "
            f"{h.c('tpp_orchestrator.py:66')} to inspect the embedded "
            f"ndarrays before {h.c('Neo4jTppAdapter.upsert')} runs.",
            f"<b>Step 3 &mdash; pick a tpp_id.</b> In Neo4j Browser: "
            f"{h.c('MATCH (t:csl_tpp { is_csl: true }) RETURN t.node_id, t.product_description LIMIT 5')}. "
            f"Copy a 32-char hex id.",
            f"<b>Step 4 &mdash; hit the routes.</b> "
            f"{h.c('curl -sS http://localhost:8000/embeddings/tpps/&lt;tpp_id&gt; | jq .')} "
            f"for the text-vector path. Add {h.c('/graph')} for the FastRP "
            f"path, or {h.c('/question/INDICATION')} for the per-question "
            f"path. For free text: "
            f"{h.c('curl -sS -X POST http://localhost:8000/embeddings/ -H &apos;Content-Type: application/json&apos; -d &apos;{&quot;include_terms&quot;: &quot;Hemophilia A non-viral, in vivo GenM&quot;, &quot;exclude_terms&quot;: &quot;von Willebrand Disease&quot;}&apos; | jq .')}.",
            f"<b>Step 5 &mdash; breakpoint sweep.</b> Set breakpoints at "
            f"{h.c('search_router.py:56')} (right before the orchestrator "
            f"call &mdash; inspect the parsed path arg), "
            f"{h.c('tpp_search_orchestrator.py:57')} (delegation into the "
            f"adapter), and "
            f"{h.c('neo4j_tpp_search_adapter.py:81')} (the actual "
            f"{h.c('tx.run')}). Copy the assembled Cypher into Neo4j "
            f"Browser with {h.c('{node_id: &apos;...&apos;}')} to see the "
            "raw 200-row index result before mapping.",
            f"<b>Step 6 &mdash; force the failure modes.</b> Send a "
            f"31-char id &rarr; FastAPI 422 from the {h.c('Path')} "
            f"constraint. Send an unknown question type like "
            f"{h.c('/question/banana')} &rarr; 422 from "
            f"{h.c('validate_question_type')} with the list of valid "
            f"values. Send an id that does not exist &rarr; "
            f"{h.c('MATCH')} returns zero anchors, the adapter returns an "
            f"empty list, and {h.c('to_search_response()')} emits "
            f"{h.c('{count: 0, results: []}')} (200, not 404).",
        ]),
        h.PageBreak(),
    ]

    # ----------------------------------------------------- 6. index
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP entry\n"
            "  src/tpp/router/search_router.py                # router + DI L26-27, handlers L30-106\n"
            "  src/tpp/router/search_util.py                  # SearchResponse, EmbeddingSearchParams,\n"
            "                                                 # to_question_enum, validate_question_type,\n"
            "                                                 # to_search_response\n"
            "  src/foundation/router/validate_util.py         # validate_value (not used here, reference only)\n"
            "\n"
            "DI / wiring\n"
            "  src/tpp/conf/eugene_ws_conf.py                 # tpp_search_orchestrator(),\n"
            "                                                 # semantic_search_embedding_provider()\n"
            "  src/eugene_ws.py                               # NB: search_router NOT yet registered\n"
            "\n"
            "Orchestration\n"
            "  src/tpp/provider/tpp_search_orchestrator.py    # TppSearchOrchestrator L16-81\n"
            "\n"
            "Query adapter (live request path)\n"
            "  src/tpp/infra/db/adapter/\n"
            "      neo4j_tpp_search_adapter.py                # _generate_find_by_tpp_id_query             L171-181\n"
            "                                                 # _generate_find_by_tpp_question_query      L183-196\n"
            "                                                 # _generate_find_by_tpp_id_and_graph_...    L198-210\n"
            "                                                 # _wrap_tx                                  L212-227\n"
            "                                                 # _convert_results                          L229-247\n"
            "  src/patent/pgpub/infra/db/adapter/\n"
            "      neo4j_pgpub_search_adapter.py              # find_by_embeddings (free-text route)\n"
            "  src/patent/pgpub/infra/db/const.py             # USPTO_PGPUB_EMBEDDINGS_INDEX_NAME L9-10\n"
            "  src/foundation/conf/const.py                   # EMBEDDINGS_FIELD_NAME L4-5\n"
            "\n"
            "Response\n"
            "  src/tpp/infra/db/model/tpp_search_result.py    # TppSearchResult\n"
            "  src/tpp/router/search_util.py                  # SearchResponse, to_search_response\n"
            "\n"
            "ETL / training pipeline\n"
            "  src/tpp/mapper/tpp_mapper.py                   # pptx -> set[Tpp]\n"
            "  src/tpp/infra/embedding/tpp_embedding_provider.py  # sentence-transformer + EmbeddingMerger\n"
            "  src/tpp/provider/tpp_orchestrator.py           # process(), _apply_embeddings, _ingest\n"
            "  src/tpp/infra/db/adapter/neo4j_tpp_adapter.py  # upsert L35-91, MERGE template L93-112,\n"
            "                                                 # question MERGE L114-178, composite id L206-239\n"
            "  src/tpp/infra/db/const.py                      # TPP_NODE_TYPE, TPP_QUESTION_NODE_TYPE,\n"
            "                                                 # TPP_QUESTION_REL_TYPE\n"
            "  src/tpp/provider/similarity_search_train_orchestrator.py  # GDS projection for FastRP\n"
            "\n"
            "Schema enums\n"
            "  src/foundation/model/foundational_node_enum.py # CSL_TPP (300), CSL_TPP_QUESTION (301)\n"
            "                                                 # USPTO_PGPUB (201)\n"
            "  src/tpp/model/question_type_enum.py            # INDICATION, CONTRAINDICATION,\n"
            "                                                 # MECHANISM_OF_ACTION, ROUTE_OF_ADMINISTRATION,\n"
            "                                                 # EFFICACY, SAFTEY_AND_TOLERABILITY,\n"
            "                                                 # COST_OF_GOODS_SOLD\n"
            "  src/tpp/model/theraputic_area_enum.py          # TheraputicAreaEnum (UNKNOWN today)\n"
            "  src/tpp/model/tpp.py                           # Tpp domain object\n"
            "  src/tpp/model/tpp_question.py                  # TppQuestion domain object\n"
        ),
    ]

    return story
