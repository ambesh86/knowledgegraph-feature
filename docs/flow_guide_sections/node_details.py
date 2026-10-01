"""End-to-end flow guide for Eugene's node_details_router.

Renders EUGENE_NODE_DETAILS_FLOW_GUIDE.pdf into docs/.

This route powers the "node details" panel in the Next.js UI: the client
sends a batch of node_ids, and the server returns a small, generic
projection (labels, id, value, source, description) for each node found
in Neo4j, regardless of label. It is intentionally label-agnostic.
"""
from __future__ import annotations

from docs.flow_guide_sections._helpers import (
    H_TITLE, H_SUB, H1, H2, BODY, BULLET, CODE, PATH,
    p, code, bullets, rule, c, Spacer, PageBreak,
)


OUT_NAME = "EUGENE_NODE_DETAILS_FLOW_GUIDE.pdf"
TITLE = "Eugene Node Details - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---- cover -----------------------------------------------------------
    story += [
        p("Eugene Node Details &mdash; End-to-End Flow", H_TITLE),
        p(
            "Developer walkthrough: HTTP POST &rarr; Pydantic validation &rarr; "
            "label-agnostic Cypher &rarr; pandas DataFrame &rarr; "
            "<font face='Courier'>GenericNodeDetails</font> response",
            H_SUB,
        ),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who need "
            "a file-referenced trace of the node-details lookup. Every reference uses "
            f"the form {c('path/to/file.py:line')} so it can be opened directly in "
            "an IDE and stepped through with a debugger."
        ),
        p("Reference endpoint", H2),
        p(
            f"{c('POST /node/details')} &mdash; declared at "
            f"{c('src/foundation/router/node_details_router.py:25-36')}."
        ),
        p("Sample request:"),
        code(
            "curl -X POST 'http://localhost:18501/node/details' \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"ids\": [\"DB00945\", \"C031180\", \"DB00436\"]}'"
        ),
        p("Sample response (200 OK):"),
        code(
            "[\n"
            "  {\n"
            "    \"labels\": [\"drug\"],\n"
            "    \"id\": \"DB00945\",\n"
            "    \"value\": \"Acetylsalicylic acid\",\n"
            "    \"source\": \"DrugBank\",\n"
            "    \"description\": \"...\"\n"
            "  },\n"
            "  ...\n"
            "]"
        ),
        p("How to read this guide", H2),
        *bullets([
            "Sections follow the request path top-down: HTTP entry, validation, "
            "DI factory chain, Cypher, DataFrame, mapping, response.",
            f"Section 0 (Schema) is non-obvious: the Cypher does <b>not</b> filter on "
            f"any label and relies on three conventional properties &mdash; "
            f"{c('node_id')}, {c('node_name')}, {c('node_source')} &mdash; that "
            "every canonical Eugene node carries.",
            "Section 4 points at the upstream ETL pipelines that populate the "
            "properties this route reads back.",
            "Section 5 contains concrete curl + breakpoint lines + a Neo4j sanity "
            "query that mirrors the route's Cypher exactly.",
            "Section 6 is a flat reference index of every file in the request path.",
        ]),
        PageBreak(),
    ]

    # ---- 0. schema -------------------------------------------------------
    story += [
        p("0. Graph schema and conventions used by this route", H1),
        p(
            "The node-details route is the most schema-light route in the codebase. "
            "It does not constrain by label and it does not paginate. It returns whatever "
            f"nodes in the graph match {c('n.node_id IN $node_ids')} and are not hidden."
        ),
        p("Required node properties", H2),
        p(
            f"Each row of the response is built from five Cypher projections, all of which "
            f"assume the canonical Eugene property names. If a node is missing any of these, "
            f"the corresponding field on {c('GenericNodeDetails')} will be {c('None')}:"
        ),
        *bullets([
            f"{c('n.node_id')} &mdash; primary natural key; this is the value clients "
            "pass in the request body.",
            f"{c('n.node_name')} &mdash; human-readable label, mapped to "
            f"{c('value')} in the response.",
            f"{c('n.node_source')} &mdash; ontology of record (e.g. DrugBank, MeSH, "
            "ClinVar).",
            f"{c('n.description')} &mdash; long-form text used by the UI side panel.",
            f"{c('n.is_hidden')} &mdash; boolean flag; rows are excluded when this is "
            f"explicitly {c('true')} (see filter clause in &sect;2).",
        ]),
        p("Node labels in scope", H2),
        p(
            f"The Cypher returns {c('labels(n)')} so the caller can branch on the node "
            f"type. Labels are defined in "
            f"{c('src/foundation/model/foundational_node_enum.py')}:"
        ),
        *bullets([
            c('DRUG = 8, "drug"') + ", " + c('DISEASE = 7, "disease"') + ", "
            + c('GENE_PROTEIN = 12, "gene_protein"') + ", "
            + c('PATHWAY = 15, "pathway"'),
            c('CLINICAL_TRIAL = 4, "ClinicalTrial"') + ", "
            + c('PATENT_APPLICATION = 31, "Patent_Application"') + ", "
            + c('APPROVED_PATENT = 30, "Approved_Patent"'),
            c('ORGANIZATION = 32, "Organization"') + ", "
            + c('RESEARCH = 33, "Research"') + ", "
            + c('INVESTIGATORS = 34, "Investigators"'),
            "GraphRAG-derived labels " + c('SUMMARY') + " / " + c('SUMMARY_FINDING')
            + " (100, 101) and USPTO labels (200, 201) are also addressable by id, "
            "since the query is label-agnostic.",
        ]),
        p("Hard limits", H2),
        *bullets([
            f"Maximum batch size: <b>50 ids</b>. Enforced twice &mdash; in the validator "
            f"({c('validate_util.py:88-92')}) and again in the adapter "
            f"({c('Neo4jFoundationalNodeDetailsAdapter.MAX_QUERY_IDS = 50')}). The router "
            "also de-duplicates with set() before calling the provider.",
            f"Forbidden characters in ids: {c('%')}, {c('$')}, {c(';')}, {c(':')}, "
            f"{c('^')}, {c('*')} &mdash; raises {c('ValueError')} from "
            f"{c('validate_util.py:98-104')}.",
        ]),
        p(
            "<b>Implication for debugging:</b> if a client gets an empty array back for "
            f"an id it knows exists in Neo4j, check {c('is_hidden')} first &mdash; "
            "it is the single most common cause of unexpected omissions."
        ),
        PageBreak(),
    ]

    # ---- 1. router -------------------------------------------------------
    story += [
        p("1. HTTP entry &mdash; the FastAPI router", H1),
        p("Wiring (eugene_ws.py)", H2),
        p(
            f"{c('src/eugene_ws.py:42-44')} imports the router module as "
            f"{c('foundational_node_details_router')}. "
            f"{c('src/eugene_ws.py:55-78')} registers it inside "
            f"{c('add_routers(app)')} which iterates a flat list and calls "
            f"{c('app.include_router(router.router)')}."
        ),
        p("Router file", H2),
        p(c("src/foundation/router/node_details_router.py"), PATH),
        p("Module-load dependency injection (line 22):"),
        code(
            "node_details_provider = foundational_node_details_provider()"
        ),
        p(
            f"This is Eugene's manual DI pattern &mdash; a plain factory call at module "
            f"import time, no framework, no decorators, no FastAPI {c('Depends')}. "
            f"Because the provider is instantiated at import, the Neo4j driver inside it "
            f"is also constructed eagerly. Cold-start latency on this route is therefore "
            f"effectively zero after the first import."
        ),
        p("DI factory chain", H2),
        p(f"{c('src/foundation/conf/conf.py:389-393')} &mdash; the top of the chain:"),
        code(
            "def foundational_node_details_provider() -> FoundationalNodeDetailsProvider:\n"
            "    return _foundational_node_details_provider(\n"
            "        neo4j_foundational_node_details_adapter="
            "neo4j_foundational_node_details_adapter(),\n"
            "        node_details_mapper=_node_details_mapper(),\n"
            "    )"
        ),
        *bullets([
            f"{c('src/foundation/conf/conf.py:117-124')} builds "
            f"{c('Neo4jFoundationalNodeDetailsAdapter(driver=_neo4j_driver())')}.",
            f"{c('src/foundation/conf/conf.py:233-234')} builds the stateless "
            f"{c('NodeDetailsMapper()')}.",
            f"{c('src/foundation/conf/conf.py:396-403')} composes the "
            f"{c('FoundationalNodeDetailsProvider')}.",
        ]),
        p("Endpoint handler", H2),
        p(f"{c('src/foundation/router/node_details_router.py:25-36')}:"),
        code(
            "@router.post(\n"
            "    \"/details\",\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def lookup_node_details_by_id(\n"
            "    node_details_request: Annotated[\n"
            "        NodeDetailsRequest,\n"
            "        AfterValidator(validate_node_details_request),\n"
            "    ],\n"
            "):\n"
            "    ids = set(node_details_request.ids)\n"
            "    return node_details_provider.find_node_details_by_node_ids(ids)"
        ),
        *bullets([
            f"Route prefix {c('/node')} is set on the {c('APIRouter')} "
            f"({c('node_details_router.py:17-20')}), so the full path is "
            f"{c('POST /node/details')}.",
            f"The handler is declared {c('async')} but the provider call is synchronous "
            "blocking I/O. This is acceptable for the current traffic profile, but a "
            "future change to a thread executor would be a single-line move.",
            f"{c('response_model_exclude_none=True')} drops None fields from each "
            f"{c('GenericNodeDetails')} dict on the wire, keeping the payload small.",
        ]),
        p("Validators", H2),
        p(f"{c('src/foundation/router/validate_util.py:80-95')}:"),
        code(
            "def validate_node_details_request(\n"
            "    request: NodeDetailsRequest,\n"
            ") -> NodeDetailsRequest:\n"
            "    if request is None: return request\n"
            "    ids = request.ids\n"
            "    if ids is None: return request\n"
            "    num_ids = len(ids)\n"
            "    max = 50\n"
            "    if num_ids > max:\n"
            "        raise ValueError(\n"
            "            f\"Too many ids given in request: ... max: {max}\"\n"
            "        )\n"
            "    for id in ids:\n"
            "        validate_id(id)\n"
            "    return request"
        ),
        p(
            f"{c('validate_id')} (lines 98-104) rejects ids containing "
            f"{c('%$;:^*')}. Both validation errors surface to FastAPI as HTTP 422."
        ),
        p("Request model", H2),
        p(f"{c('src/foundation/router/model/node_details_request.py')}:"),
        code(
            "class NodeDetailsRequest(BaseModel):\n"
            "    ids: list[Annotated[\n"
            "        str,\n"
            "        Field(None, examples=[\n"
            "            \"C031180\", \"DB00846\", \"DB00436\"\n"
            "        ]),\n"
            "    ]]"
        ),
        p(
            f"<b>Set your first breakpoint at "
            f"{c('node_details_router.py:35')}</b> "
            f"({c('ids = set(node_details_request.ids)')})."
        ),
        PageBreak(),
    ]

    # ---- 2. adapter ------------------------------------------------------
    story += [
        p("2. Provider + Query adapter &mdash; the Cypher", H1),
        p("Provider (thin orchestration)", H2),
        p(c("src/foundation/provider/foundational_node_details_provider.py"), PATH),
        *bullets([
            f"{c('FoundationalNodeDetailsProvider.find_node_details_by_node_ids')} "
            f"(lines 29-36) is decorated with {c('@log_time')} and does exactly two "
            "things: (1) call the adapter to get a DataFrame, (2) hand the DataFrame "
            "to the mapper.",
            "No business logic lives here. This separation makes it trivial to swap the "
            "adapter for a fake in tests.",
        ]),
        p("Adapter file", H2),
        p(c("src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py"), PATH),
        *bullets([
            f"{c('find_node_details_by_node_ids')} (lines 23-30) short-circuits on "
            f"empty/None input, calls {c('_ensure_query_limit_or_raise')} (the second "
            f"50-id guard), runs {c('ensure_connection(self.driver)')} from "
            f"{c('graph/util/util.py')}, then delegates to "
            f"{c('_find_node_details_by_node_ids')}.",
            f"{c('_find_node_details_by_node_ids')} (lines 32-51) calls "
            f"{c('self.driver.execute_query(...)')} with "
            f"{c('result_transformer_=neo4j.Result.to_df')} &mdash; the result lands "
            "directly as a pandas DataFrame, no manual record iteration.",
            f"On {c('DriverError')} or {c('Neo4jError')} the adapter logs the query "
            f"plus the exception and re-raises &mdash; FastAPI surfaces this as HTTP 500.",
            f"{c('_ensure_query_limit_or_raise')} (lines 61-69) raises "
            f"{c('ValueError')} if the set has more than 50 ids. The router-level "
            "validator should make this branch unreachable, but it is defense in depth "
            "for any future caller that bypasses the validator.",
        ]),
        p("Generated Cypher (verbatim)", H2),
        p(
            f"Built by {c('_build_find_node_details_by_node_ids')} "
            f"({c('neo4j_foundational_node_details_adapter.py:53-59')}). There is no "
            "label or relationship interpolation &mdash; the string is a constant:"
        ),
        code(
            "MATCH (n)\n"
            "WHERE (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "  AND n.node_id IN $node_ids\n"
            "RETURN labels(n)       AS labels,\n"
            "       n.node_id       AS id,\n"
            "       n.node_name     AS value,\n"
            "       n.node_source   AS source,\n"
            "       n.description   AS description"
        ),
        p(
            f"Note the {c('IS NULL OR NOT')} idiom on {c('is_hidden')} &mdash; this "
            f"means nodes without the property are <b>included</b>, only nodes with "
            f"{c('is_hidden = true')} are excluded. The property was added late in the "
            "graph's life and not back-filled, hence the null-tolerant check."
        ),
        p("Pagination", H2),
        p(
            f"<b>None.</b> Unlike {c('patent_search_router')} or "
            f"{c('pubmed_search_router')}, this route has no page/page_size parameters "
            f"and no {c('SKIP')}/{c('LIMIT')} clauses. The 50-id cap is the only bound "
            f"on result size. A request for 50 ids that all match exactly one node each "
            f"will return at most ~50 rows (more if a node carries the same "
            f"{c('node_id')} under multiple labels, which Eugene's MERGE convention "
            "prevents)."
        ),
        p("DataFrame schema", H2),
        p(f"The DataFrame returned by {c('execute_query(..., to_df)')} has columns:"),
        code(
            "columns: ['labels', 'id', 'value', 'source', 'description']\n"
            "dtypes : object (labels: list[str]), object, object, object, object\n"
            "shape  : (<=50, 5)"
        ),
        p(
            f"The {c('labels')} column is a Python list of strings (Neo4j returns "
            f"{c('LabelSet')}, the driver coerces to {c('list')}). The mapper widens "
            f"it to a {c('Tuple[str, ...]')} on the dataclass."
        ),
        PageBreak(),
    ]

    # ---- 3. mapping ------------------------------------------------------
    story += [
        p("3. Response mapping &mdash; DataFrame to dataclass", H1),
        p("Mapper file", H2),
        p(c("src/foundation/mapper/node_details_mapper.py"), PATH),
        p(f"{c('NodeDetailsMapper.map')} (lines 17-22) is decorated with "
          f"{c('@log_time')} and short-circuits on a None DataFrame "
          f"(this is the empty-ids signal the adapter sends back)."),
        code(
            "def map(self, df: DataFrame | None) -> list[GenericNodeDetails] | None:\n"
            "    if df is None:\n"
            "        return None\n"
            "    return self._map_response_rows(df)"
        ),
        p(f"Row-wise mapping ({c('node_details_mapper.py:24-42')}):"),
        code(
            "def _map_response_rows(self, df: DataFrame) -> list[GenericNodeDetails]:\n"
            "    if df is None: return None\n"
            "    results = [\n"
            "        el for el in df.apply(self._map_response_row, axis=1)\n"
            "        if el is not None\n"
            "    ]\n"
            "    return results\n"
            "\n"
            "def _map_response_row(self, row) -> GenericNodeDetails | None:\n"
            "    if row is None: return None\n"
            "    return GenericNodeDetails(\n"
            "        labels=row[\"labels\"],\n"
            "        id=row[\"id\"],\n"
            "        value=row[\"value\"],\n"
            "        source=row[\"source\"],\n"
            "        description=row[\"description\"],\n"
            "    )"
        ),
        *bullets([
            f"{c('df.apply(..., axis=1)')} iterates row-wise. Each row is converted "
            f"to a frozen, hashable {c('GenericNodeDetails')} dataclass instance.",
            "There is no field-level cleansing &mdash; whatever Neo4j returns is passed "
            "through. Empty descriptions and missing sources surface as Python None.",
            "FastAPI serializes the dataclass instances via Pydantic v2's "
            f"{c('TypeAdapter')} machinery. Because the response is a plain "
            f"{c('list[GenericNodeDetails]')} (no declared "
            f"{c('response_model')}), the dataclass field names become the JSON keys.",
        ]),
        p("Response model", H2),
        p(c("src/foundation/model/generic_node_details.py"), PATH),
        code(
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class GenericNodeDetails:\n"
            "    labels: Tuple[str, ...]\n"
            "    id: str\n"
            "    value: str\n"
            "    source: str\n"
            "    description: str"
        ),
        p(
            f"The {c('frozen=True, unsafe_hash=True')} pair lets the UI cache these "
            "objects in React Query's normalized cache by structural equality, and "
            "lets them be dropped into a Python set in tests without ceremony."
        ),
        PageBreak(),
    ]

    # ---- 4. data source / ETL --------------------------------------------
    story += [
        p("4. Data source &mdash; upstream ETL pipelines", H1),
        p(
            "This route is read-only and label-agnostic, so its data surface is "
            "every Eugene ingest pipeline. Each pipeline writes nodes via "
            f"{c('MERGE (n:`label` { node_id: $id }) ON CREATE SET n.node_name = ..., n.node_source = ..., n.description = ...')}, "
            f"which is the contract the {c('node-details')} Cypher reads back."
        ),
        p("Drug ingest", H2),
        *bullets([
            f"{c('src/ingest_drug_aliases.py')} &mdash; CSV ingest that writes "
            f"{c('(:drug)')}, {c('(:drug_product)')}, {c('(:drug_synonym)')} "
            f"nodes. Sets {c('node_source = &quot;DrugBank&quot;')}. See "
            f"{c('docs/EUGENE_DRUG_ALIAS_FLOW_GUIDE.pdf')} for the full trace.",
            f"DrugBank canonical seed is loaded via "
            f"{c('bin/seed/csl_behring_assets.cypher')}, "
            f"{c('bin/seed/biogen_assets.cypher')}, and "
            f"{c('bin/seed/csl_drug_node_properties.cypher')} &mdash; these "
            f"establish the {c('node_id')} primary keys for the alias attach.",
        ]),
        p("Patent ingest", H2),
        *bullets([
            f"{c('src/ingest_uspto_patents.py')} &mdash; pulls USPTO XML, "
            f"writes {c('(:Approved_Patent)')}, {c('(:Patent_Application)')}, "
            f"{c('(:USPTO_APPLICATION)')}, {c('(:USPTO_PGPUB)')} nodes with "
            f"{c('node_source = &quot;USPTO&quot;')}. See "
            f"{c('docs/EUGENE_PATENT_FLOW_GUIDE.pdf')}.",
            f"The {c('node_id')} format for patents is the publication number "
            f"as a string (e.g. {c('US-2021-0123456-A1')}); the inspector "
            "panel calls this route directly when the user clicks a patent "
            "node on the context graph.",
        ]),
        p("Biomedical knowledge graph (primeKG)", H2),
        *bullets([
            f"{c('src/ingest_primekg.py')} &mdash; loads the primeKG TSVs into "
            f"{c('(:disease)')}, {c('(:gene_protein)')}, {c('(:pathway)')}, "
            f"{c('(:anatomy)')}, {c('(:biological_process)')}, "
            f"{c('(:cellular_component)')}, {c('(:molecular_function)')}, "
            f"{c('(:effect_phenotype)')}. Source tag: "
            f"{c('node_source = &quot;primekg&quot;')}.",
            f"{c('description')} on primeKG nodes is often empty &mdash; this "
            f"is why the inspector panel renders a placeholder for many "
            "disease / gene nodes.",
        ]),
        p("Clinical trials", H2),
        *bullets([
            f"{c('src/ingest_clinical_trials.py')} &mdash; reads "
            f"ClinicalTrials.gov export and writes {c('(:ClinicalTrial)')}, "
            f"{c('(:Sponsor)')}, {c('(:Phase)')}, {c('(:Investigators)')}, "
            f"{c('(:Intervention)')}, {c('(:Condition)')}, "
            f"{c('(:PrimaryOutcomeMeasure)')}, "
            f"{c('(:SecondaryOutcomeMeasure)')} nodes. The "
            f"{c('node_id')} is the NCT id (validated elsewhere via "
            f"{c('validate_clinical_trail_id')}).",
        ]),
        p("PubMed", H2),
        *bullets([
            f"{c('src/ingest_pubmed.py')} &mdash; writes "
            f"{c('(:PUBMED_DOCUMENT)')} and the GraphRAG-derived "
            f"{c('(:PUBMED_SUMMARY)')} / {c('(:PUBMED_SUMMARY_FINDING)')} "
            f"nodes. {c('node_source = &quot;pubmed&quot;')}. PMIDs become "
            f"{c('node_id')}.",
        ]),
        p("Corporate / seed data", H2),
        *bullets([
            f"Seed cypher files in {c('bin/seed/')} establish "
            f"{c('(:Organization)')}, {c('(:Research)')}, "
            f"{c('(:Collaborator)')}, and the canonical {c('(:drug)')} stubs "
            "the drug-alias pipeline later decorates. These are hand-curated "
            "and version-controlled.",
        ]),
        p("Hidden-node sources", H2),
        p(
            f"A few pipelines mark intermediate scaffolding nodes with "
            f"{c('is_hidden = true')} (GraphRAG summary intermediates, ETL "
            f"checkpoint markers). These are filtered out by the route's "
            f"{c('WHERE')} clause and are not visible to clients. If you add "
            f"a new ETL that creates internal-only nodes, set "
            f"{c('is_hidden = true')} on them rather than picking a "
            "&ldquo;private&rdquo; label name.",
        ),
        PageBreak(),
    ]

    # ---- 5. debug walk ---------------------------------------------------
    story += [
        p("5. Suggested debugging walk", H1),
        *bullets([
            f"Start FastAPI locally: {c('uvicorn src.eugene_ws:app --port 18501')}.",
            "Hit the endpoint with a known-good drug id: " + c(
                'curl -X POST localhost:18501/node/details '
                '-H "Content-Type: application/json" '
                '-d \'{"ids": ["DB00945"]}\''
            ) + ".",
            f"Breakpoint at {c('src/foundation/router/node_details_router.py:35')} "
            f"({c('ids = set(...)')}). Inspect the request object &mdash; the validator "
            "has already run by this point.",
            f"Step into {c('FoundationalNodeDetailsProvider.find_node_details_by_node_ids')} "
            f"({c('foundational_node_details_provider.py:30')}).",
            f"Step into the adapter at "
            f"{c('neo4j_foundational_node_details_adapter.py:36')}; the variable "
            f"{c('query')} holds the Cypher exactly as printed in &sect;2 and "
            f"{c('params')} is " + c('{"node_ids": [...]}') + ".",
            f"After {c('execute_query')} returns, inspect the DataFrame: "
            f"{c('records.shape')}, {c('records.columns')}, "
            f"{c('records.iloc[0].to_dict()')}.",
            f"Set a final breakpoint inside "
            f"{c('NodeDetailsMapper._map_response_row')} "
            f"({c('node_details_mapper.py:33')}) to confirm field coercion.",
        ]),
        p("Neo4j sanity query (mirrors the route)", H2),
        p(
            f"Run this in the Neo4j browser at {c('http://localhost:7474')} "
            "with the same ids you sent to the route. The row set should match the "
            "HTTP response one-for-one:"
        ),
        code(
            "MATCH (n)\n"
            "WHERE (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "  AND n.node_id IN ['DB00945','C031180','DB00436']\n"
            "RETURN labels(n) AS labels,\n"
            "       n.node_id AS id,\n"
            "       n.node_name AS value,\n"
            "       n.node_source AS source,\n"
            "       n.description AS description"
        ),
        p("Common failure modes and what to check", H2),
        *bullets([
            f"<b>HTTP 422</b> &mdash; the validator rejected an id. Look at the FastAPI "
            f"error body for {c('Too many ids')} (>50) or "
            f"{c('id cannot have a special character')}.",
            f"<b>Empty array</b> for an id you expect to exist: "
            f"(a) the node has {c('is_hidden = true')}; "
            f"(b) the id was supplied with the wrong casing &mdash; the Cypher matches "
            f"on {c('n.node_id')} exactly; "
            f"(c) the node was MERGEd under a different natural-key property and lacks "
            f"a {c('node_id')} entirely.",
            f"<b>HTTP 500</b> with a {c('Neo4jError')} in the logs &mdash; check the "
            f"driver health by running any trivial Cypher; "
            f"{c('ensure_connection')} (adapter line 27) will have logged the failure.",
            f"<b>Field is {c('null')} on the wire</b> &mdash; the underlying node lacks "
            "the property. Useful for backfill scripts: "
            + c('MATCH (n) WHERE n.node_id = "X" RETURN properties(n)') + ".",
        ]),
        PageBreak(),
    ]

    # ---- 6. reference index ----------------------------------------------
    story += [
        p("6. Reference index (file:line)", H1),
        code(
            "Schema\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "\n"
            "HTTP entry and wiring\n"
            "  src/eugene_ws.py:42-44               (import)\n"
            "  src/eugene_ws.py:55-78               (include_router)\n"
            "  src/foundation/router/node_details_router.py:17-20  (APIRouter prefix)\n"
            "  src/foundation/router/node_details_router.py:22     (DI hook)\n"
            "  src/foundation/router/node_details_router.py:25-36  (handler)\n"
            "\n"
            "Validation\n"
            "  src/foundation/router/validate_util.py:80-95   (validate_node_details_request)\n"
            "  src/foundation/router/validate_util.py:98-104  (validate_id)\n"
            "  src/foundation/router/model/node_details_request.py  (Pydantic model)\n"
            "\n"
            "DI factories\n"
            "  src/foundation/conf/conf.py:117-124  (Neo4j adapter factory)\n"
            "  src/foundation/conf/conf.py:233-234  (mapper factory)\n"
            "  src/foundation/conf/conf.py:389-393  (provider factory entry)\n"
            "  src/foundation/conf/conf.py:396-403  (provider composition)\n"
            "\n"
            "Provider / orchestration\n"
            "  src/foundation/provider/foundational_node_details_provider.py:14-36\n"
            "\n"
            "Adapter / Cypher\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py:13-21\n"
            "      class header + MAX_QUERY_IDS = 50\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py:23-30\n"
            "      public entrypoint, guard + ensure_connection\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py:32-51\n"
            "      driver.execute_query(..., result_transformer_=neo4j.Result.to_df)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py:53-59\n"
            "      Cypher builder (constant query string)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_details_adapter.py:61-69\n"
            "      _ensure_query_limit_or_raise\n"
            "  src/graph/util/util.py                       (ensure_connection)\n"
            "\n"
            "Mapper / response\n"
            "  src/foundation/mapper/node_details_mapper.py:12-22  (NodeDetailsMapper.map)\n"
            "  src/foundation/mapper/node_details_mapper.py:24-31  (_map_response_rows)\n"
            "  src/foundation/mapper/node_details_mapper.py:33-42  (_map_response_row)\n"
            "  src/foundation/mapper/node_details_mapper_test.py   (unit tests)\n"
            "\n"
            "Model\n"
            "  src/foundation/model/generic_node_details.py        (GenericNodeDetails)\n"
            "  src/foundation/router/model/node_details_request.py (NodeDetailsRequest)\n"
            "\n"
            "Upstream ETL (sources of node_id / node_name / node_source / description)\n"
            "  src/ingest_drug_aliases.py\n"
            "  src/ingest_uspto_patents.py\n"
            "  src/ingest_primekg.py\n"
            "  src/ingest_clinical_trials.py\n"
            "  src/ingest_pubmed.py\n"
            "  bin/seed/csl_behring_assets.cypher\n"
            "  bin/seed/biogen_assets.cypher\n"
            "  bin/seed/csl_drug_node_properties.cypher\n"
            "\n"
            "MCP cross-reference (callers of this route)\n"
            "  agents/eugene-mcp/src/tools/eugene_node_tools.py\n"
            "  agents/eugene-mcp/src/tools/eugene_fetch_tools.py\n"
        ),
    ]

    return story
