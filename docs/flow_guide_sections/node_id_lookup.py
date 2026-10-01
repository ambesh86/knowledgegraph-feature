"""End-to-end flow guide for Eugene's node_id_lookup_router.

Renders EUGENE_NODE_ID_LOOKUP_FLOW_GUIDE.pdf into docs/.

This route powers the "find node by name" lookup: the client supplies a
node_name value (and optional fuzzy_match flag) and the server returns
matching (node_id, node_name) pairs from Neo4j. Unlike node_details, the
match key is node_name (human-readable label), not node_id.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_NODE_ID_LOOKUP_FLOW_GUIDE.pdf"
TITLE = "Eugene Node ID Lookup - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---- cover -----------------------------------------------------------
    story += [
        h.p("Eugene Node ID Lookup &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP GET &rarr; path validator &rarr; "
            "label-agnostic Cypher (exact or regex) &rarr; pandas DataFrame &rarr; "
            f"{h.c('NodeIdLookup')} response",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who need "
            "a file-referenced trace of the node-id lookup. Every reference uses "
            f"the form {h.c('path/to/file.py:line')} so it can be opened directly in "
            "an IDE and stepped through with a debugger."
        ),
        h.p("Reference endpoint", h.H2),
        h.p(
            f"{h.c('GET /node/find/{node_value}')} &mdash; declared at "
            f"{h.c('src/foundation/router/node_id_lookup_router.py:22-47')}."
        ),
        h.p("Sample requests:"),
        h.code(
            "# exact match on node_name\n"
            "curl 'http://localhost:18501/node/find/Flurandrenolide'\n"
            "\n"
            "# case-insensitive regex (substring) match\n"
            "curl 'http://localhost:18501/node/find/aspirin?fuzzy_match=true'"
        ),
        h.p("Sample response (200 OK):"),
        h.code(
            "{\n"
            "  \"results\": [\n"
            "    { \"id\": \"DB01580\", \"value\": \"Flurandrenolide\" }\n"
            "  ],\n"
            "  \"count\": 1,\n"
            "  \"query\": \"Flurandrenolide\",\n"
            "  \"fuzzy_match\": false\n"
            "}"
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Sections follow the request path top-down: schema, HTTP entry, "
            "validation + DI, Cypher, mapping, response, ETL, debugging.",
            f"Section 0 (Schema) is non-obvious: the Cypher does <b>not</b> filter on "
            f"a label &mdash; the match is by the {h.c('node_name')} property alone. "
            "This route is therefore label-agnostic by design.",
            f"The {h.c('fuzzy_match=true')} branch interpolates the value directly "
            f"into the Cypher as a regex. {h.c('validate_value')} is the only "
            "defense against Cypher injection on this route &mdash; section 1 covers "
            "the exact character blacklist.",
            "Section 4 points at the upstream ETL pipelines that populate node_name.",
            "Section 5 contains concrete curl + breakpoint lines + a Neo4j sanity "
            "query that mirrors the route's Cypher exactly.",
            "Section 6 is a flat reference index of every file in the request path.",
        ]),
        h.PageBreak(),
    ]

    # ---- 0. schema -------------------------------------------------------
    story += [
        h.p("0. Graph schema and conventions used by this route", h.H1),
        h.p(
            "The node-id lookup route, like node-details, is schema-light. It does not "
            "constrain by label, does not paginate, and returns whatever nodes in the "
            f"graph carry the requested {h.c('node_name')} (or match the regex), "
            "minus hidden nodes."
        ),
        h.p("Required node properties", h.H2),
        h.p(
            "Each row of the response uses two Cypher projections; both assume the "
            "canonical Eugene property names:"
        ),
        *h.bullets([
            f"{h.c('n.node_name')} &mdash; human-readable label, used both as the "
            f"WHERE-clause match key and as {h.c('value')} on the response.",
            f"{h.c('n.node_id')} &mdash; primary natural key, returned to the "
            f"caller as {h.c('id')} so it can be used as input to "
            f"{h.c('/node/details')}, {h.c('/n-hop')}, or any other id-driven route.",
            f"{h.c('n.is_hidden')} &mdash; boolean flag; rows are excluded when "
            f"this is explicitly {h.c('true')} (see filter clause in &sect;2). "
            f"Nodes lacking the property are <b>included</b>.",
        ]),
        h.p("Node labels in scope", h.H2),
        h.p(
            f"Because the Cypher uses {h.c('MATCH (n ...)')} with no label, every "
            f"label declared in "
            f"{h.c('src/foundation/model/foundational_node_enum.py')} is reachable:"
        ),
        *h.bullets([
            f"{h.c('DRUG = 8, &quot;drug&quot;')}, "
            f"{h.c('DISEASE = 7, &quot;disease&quot;')}, "
            f"{h.c('GENE_PROTEIN = 12, &quot;gene_protein&quot;')}, "
            f"{h.c('PATHWAY = 15, &quot;pathway&quot;')}",
            f"{h.c('CLINICAL_TRIAL = 4, &quot;ClinicalTrial&quot;')}, "
            f"{h.c('PATENT_APPLICATION = 31, &quot;Patent_Application&quot;')}, "
            f"{h.c('APPROVED_PATENT = 30, &quot;Approved_Patent&quot;')}",
            f"{h.c('DRUG_PRODUCT = 21, &quot;drug_product&quot;')}, "
            f"{h.c('DRUG_SYNONYM = 22, &quot;drug_synonym&quot;')} &mdash; useful "
            f"because brand and synonym names that fail to match on "
            f"{h.c('(:drug)')} will frequently match on these.",
            f"GraphRAG labels {h.c('SUMMARY')} / {h.c('SUMMARY_FINDING')} (100, 101) "
            f"and PubMed {h.c('PUBMED_DOCUMENT')} / {h.c('PUBMED_SUMMARY')} are also "
            "addressable, since the query is label-agnostic.",
        ]),
        h.p("Relationships", h.H2),
        h.p(
            f"This route does not traverse edges. For completeness, edge types are "
            f"declared in "
            f"{h.c('src/foundation/model/foundational_relationship_enum.py')} &mdash; "
            f"e.g. {h.c('HAS_DRUG_ALIAS')}, {h.c('INDICATION')}, "
            f"{h.c('DRUG_PROTEIN')}, {h.c('DISEASE_PROTEIN')}. Once the caller has the "
            f"{h.c('node_id')} from this route, downstream routes "
            f"({h.c('/n-hop')}, {h.c('/path')}) walk those edges."
        ),
        h.p("Hard limits", h.H2),
        *h.bullets([
            f"Maximum value length: <b>2048 characters</b>. Enforced by the FastAPI "
            f"{h.c('Path(max_length=2048)')} constraint "
            f"({h.c('node_id_lookup_router.py:29-34')}).",
            f"Forbidden characters in the path value: "
            f"{h.c('%')}, {h.c('_')}, {h.c('$')}, {h.c(';')}, {h.c(':')}, "
            f"{h.c('^')}, {h.c('*')} &mdash; raises {h.c('ValueError')} from "
            f"{h.c('validate_util.py:35-42')} (the {h.c('specials')} list, "
            f"line 10).",
            f"Note: {h.c('_')} is in the blacklist for this route &mdash; a node_name "
            f"containing an underscore (rare but possible on some primeKG ids) "
            "cannot be looked up by exact match. Use fuzzy_match in that case.",
            "<b>No paging.</b> A fuzzy regex that matches thousands of nodes will "
            "return them all in one payload.",
        ]),
        h.p(
            f"<b>Implication for debugging:</b> if the response is "
            f"{h.c('count: 0')} for a value you know exists in Neo4j, check "
            f"(1) case &mdash; the exact path matches case-sensitively, "
            f"(2) {h.c('is_hidden')}, "
            f"(3) the value was actually stored on {h.c('node_name')} (not "
            f"{h.c('node_id')} or a label-specific property)."
        ),
        h.PageBreak(),
    ]

    # ---- 1. router -------------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring (eugene_ws.py)", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:39-41')} imports the router module as "
            f"{h.c('foundation_node_id_lookup_router')}. "
            f"{h.c('src/eugene_ws.py:55-78')} registers it inside the "
            f"{h.c('routers')} list (entry at line 63), and a downstream loop calls "
            f"{h.c('app.include_router(router.router)')} on each."
        ),
        h.p("Router file", h.H2),
        h.p(h.c("src/foundation/router/node_id_lookup_router.py"), h.PATH),
        h.p("Module-load dependency injection (line 19):"),
        h.code(
            "node_id_provider = foundational_node_id_provider()"
        ),
        h.p(
            f"This is Eugene's manual DI pattern &mdash; a plain factory call at module "
            f"import time, no framework, no decorators, no FastAPI {h.c('Depends')}. "
            f"Because the provider is instantiated at import, the Neo4j driver inside it "
            f"is also constructed eagerly. Cold-start latency on this route is therefore "
            f"effectively zero after the first import."
        ),
        h.p("DI factory chain", h.H2),
        h.p(f"{h.c('src/foundation/conf/conf.py:372-376')} &mdash; the top of the chain:"),
        h.code(
            "def foundational_node_id_provider() -> FoundationalNodeIdProvider:\n"
            "    return _foundational_node_id_provider(\n"
            "        neo4j_foundational_node_adapter=neo4j_foundational_node_adapter(),\n"
            "        node_id_lookup_mapper=_node_id_lookup_mapper(),\n"
            "    )"
        ),
        *h.bullets([
            f"{h.c('src/foundation/conf/conf.py:109-114')} builds "
            f"{h.c('Neo4jFoundationalNodeAdapter(driver=_neo4j_driver())')}.",
            f"{h.c('src/foundation/conf/conf.py:229-230')} builds the stateless "
            f"{h.c('NodeIdLookupMapper()')}.",
            f"{h.c('src/foundation/conf/conf.py:379-386')} composes the "
            f"{h.c('FoundationalNodeIdProvider')}.",
        ]),
        h.p("Endpoint handler", h.H2),
        h.p(f"{h.c('src/foundation/router/node_id_lookup_router.py:22-47')}:"),
        h.code(
            "@router.get(\n"
            "    \"/find/{node_value}\",\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def lookup_node_id_by_value(\n"
            "    node_value: Annotated[\n"
            "        str,\n"
            "        Path(\n"
            "            description=\"The node value to search\",\n"
            "            max_length=2048,\n"
            "            min_length=0,\n"
            "            example=\"Flurandrenolide\",\n"
            "        ),\n"
            "        AfterValidator(validate_value),\n"
            "    ],\n"
            "    fuzzy_match: Annotated[\n"
            "        bool,\n"
            "        Query(\n"
            "            title=\"True to do a fuzzy search, ... A fuzzy match is a regex match\",\n"
            "            example=False,\n"
            "        ),\n"
            "    ] = False,\n"
            "):\n"
            "    return node_id_provider.find_node_id_by_node_name(\n"
            "        value=node_value, fuzzy_match=fuzzy_match\n"
            "    )"
        ),
        *h.bullets([
            f"Route prefix {h.c('/node')} is set on the {h.c('APIRouter')} "
            f"({h.c('node_id_lookup_router.py:14-17')}), so the full path is "
            f"{h.c('GET /node/find/{node_value}')}.",
            f"The handler is declared {h.c('async')} but the provider call is synchronous "
            "blocking I/O. Adequate for the current traffic profile.",
            f"{h.c('response_model_exclude_none=True')} drops None fields from the "
            f"{h.c('NodeIdLookup')} dataclass on the wire.",
            f"FastAPI's {h.c('AfterValidator')} runs the validator <b>after</b> "
            f"Pydantic type coercion. A non-string value never reaches "
            f"{h.c('validate_value')}.",
        ]),
        h.p("Validator", h.H2),
        h.p(f"{h.c('src/foundation/router/validate_util.py:35-42')}:"),
        h.code(
            "specials = [\"%\", \"_\", \"$\", \";\", \":\", \"^\", \"*\"]\n"
            "\n"
            "def validate_value(value: str) -> str:\n"
            "    if value is None:\n"
            "        raise ValueError(\"value cannot be None\")\n"
            "    is_valid = not has_special_char(value)\n"
            "    if not is_valid:\n"
            "        raise ValueError(\n"
            "            f\"value cannot have a special character: {specials}\"\n"
            "        )\n"
            "    return value"
        ),
        h.p(
            f"{h.c('has_special_char')} (line 114) delegates to "
            f"{h.c('has_invalid_char')} (lines 118-128), a short-circuit linear scan. "
            f"Validation errors surface to FastAPI as HTTP 422."
        ),
        h.p(
            f"<b>Set your first breakpoint at "
            f"{h.c('node_id_lookup_router.py:45')}</b> "
            f"({h.c('return node_id_provider.find_node_id_by_node_name(...)')})."
        ),
        h.PageBreak(),
    ]

    # ---- 2. adapter ------------------------------------------------------
    story += [
        h.p("2. Provider + Query adapter &mdash; the Cypher", h.H1),
        h.p("Provider (thin orchestration)", h.H2),
        h.p(h.c("src/foundation/provider/foundational_node_id_provider.py"), h.PATH),
        *h.bullets([
            f"{h.c('FoundationalNodeIdProvider.find_node_id_by_node_name')} "
            f"(lines 27-37) is decorated with {h.c('@log_time')} and does exactly two "
            "things: (1) call the adapter to get a DataFrame, (2) hand the DataFrame "
            "to the mapper.",
            "No business logic lives here. This separation makes it trivial to swap the "
            "adapter for a fake in tests.",
        ]),
        h.p("Adapter file", h.H2),
        h.p(h.c("src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py"), h.PATH),
        *h.bullets([
            f"{h.c('find_node_id_by_node_name')} (lines 25-31) short-circuits on "
            f"a None value, calls {h.c('ensure_connection(self.driver)')} from "
            f"{h.c('graph/util/util.py')}, then delegates to "
            f"{h.c('_find_node_id_by_node_name')}.",
            f"{h.c('_find_node_id_by_node_name')} (lines 171-193) branches on "
            f"{h.c('fuzzy_match')}: exact path uses a parameterised query with "
            f"{h.c('params = {&quot;node_name&quot;: value}')}; fuzzy path "
            "interpolates the value directly into the Cypher string and runs with "
            f"{h.c('params = {}')}.",
            f"In both branches the result lands as a pandas DataFrame via "
            f"{h.c('result_transformer_=neo4j.Result.to_df')}.",
            f"On {h.c('DriverError')} or {h.c('Neo4jError')} the adapter logs the query "
            "plus the exception and re-raises &mdash; FastAPI surfaces this as HTTP 500.",
        ]),
        h.p("Generated Cypher &mdash; exact path (verbatim)", h.H2),
        h.p(
            f"Built by {h.c('build_find_node_id_by_node_name')} "
            f"({h.c('neo4j_foundational_node_adapter.py:195-200')}). Constant query, "
            f"no label, no interpolation:"
        ),
        h.code(
            "MATCH (n { node_name: $node_name })\n"
            "WHERE n.is_hidden IS NULL OR NOT n.is_hidden\n"
            "RETURN n.node_id, n.node_name"
        ),
        h.p("Generated Cypher &mdash; fuzzy path (verbatim)", h.H2),
        h.p(
            f"Built by {h.c('build_fuzzy_find_node_id_by_node_name')} "
            f"({h.c('neo4j_foundational_node_adapter.py:202-209')}). The supplied "
            f"value is concatenated into the regex literal via Python "
            f"{h.c('%')}-formatting; the validator's character blacklist is the only "
            "guard:"
        ),
        h.code(
            "MATCH (n)\n"
            "WHERE n.node_name =~ '(?i).*<value>.*'\n"
            "  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "RETURN n.node_id, n.node_name"
        ),
        h.p(
            f"The {h.c('(?i)')} prefix makes the regex case-insensitive and "
            f"{h.c('.*&hellip;.*')} makes it a substring match. So "
            f"{h.c('fuzzy_match=true')} on {h.c('aspirin')} matches "
            f"{h.c('Aspirin')}, {h.c('Acetylsalicylic acid (aspirin)')}, etc."
        ),
        h.p(
            f"Note the {h.c('IS NULL OR NOT')} idiom on {h.c('is_hidden')} &mdash; "
            f"nodes without the property are <b>included</b>; only nodes with "
            f"{h.c('is_hidden = true')} are excluded."
        ),
        h.p("DataFrame schema", h.H2),
        h.p(f"The DataFrame returned by {h.c('execute_query(..., to_df)')} has columns:"),
        h.code(
            "columns: ['n.node_id', 'n.node_name']\n"
            "dtypes : object, object\n"
            "shape  : (<= match count, 2)"
        ),
        h.p(
            f"Note the column names retain the Cypher {h.c('n.')} prefix &mdash; the "
            f"adapter does not alias them in the RETURN clause. The mapper indexes "
            f"into the DataFrame with the literal strings "
            f"{h.c('row[&quot;n.node_id&quot;]')} and "
            f"{h.c('row[&quot;n.node_name&quot;]')}."
        ),
        h.PageBreak(),
    ]

    # ---- 3. mapping ------------------------------------------------------
    story += [
        h.p("3. Response mapping &mdash; DataFrame to dataclass", h.H1),
        h.p("Mapper file", h.H2),
        h.p(h.c("src/foundation/mapper/node_id_lookup_mapper.py"), h.PATH),
        h.p(
            f"{h.c('NodeIdLookupMapper.map')} (lines 19-29) is decorated with "
            f"{h.c('@log_time')}. A None DataFrame produces an empty-result "
            f"{h.c('NodeIdLookup')} that still echoes the query and fuzzy_match flag:"
        ),
        h.code(
            "def map(self, value: str, fuzzy_match: bool, df: DataFrame | None\n"
            ") -> NodeIdLookup:\n"
            "    if df is None:\n"
            "        return NodeIdLookup(\n"
            "            query=value, count=0, fuzzy_match=fuzzy_match, results=()\n"
            "        )\n"
            "    results = self._map_response_rows(df)\n"
            "    return NodeIdLookup(\n"
            "        results=results, count=len(results),\n"
            "        query=value, fuzzy_match=fuzzy_match,\n"
            "    )"
        ),
        h.p(f"Row-wise mapping ({h.c('node_id_lookup_mapper.py:31-42')}):"),
        h.code(
            "def _map_response_rows(self, df: DataFrame) -> Tuple[IdAndValue, ...]:\n"
            "    if df is None: return None\n"
            "    return tuple(df.apply(self._map_response_row, axis=1))\n"
            "\n"
            "def _map_response_row(self, row) -> IdAndValue | None:\n"
            "    if row is None: return None\n"
            "    return IdAndValue(\n"
            "        id=row[\"n.node_id\"],\n"
            "        value=row[\"n.node_name\"],\n"
            "    )"
        ),
        *h.bullets([
            f"{h.c('df.apply(..., axis=1)')} iterates row-wise. Each row becomes a "
            f"frozen {h.c('IdAndValue')} dataclass instance.",
            f"{h.c('results')} is a {h.c('Tuple[IdAndValue, ...]')} (note: tuple, not "
            f"list) &mdash; this matches the field type on {h.c('NodeIdLookup')} and "
            "preserves dataclass hashability.",
            f"FastAPI serializes the dataclass via Pydantic v2's "
            f"{h.c('TypeAdapter')} machinery. With "
            f"{h.c('response_model_exclude_none=True')} on the route, any None field "
            "is dropped from the JSON payload.",
        ]),
        h.p("Response model", h.H2),
        h.p(h.c("src/foundation/model/node_id_lookup.py"), h.PATH),
        h.code(
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class NodeIdLookup:\n"
            "    results: Tuple[IdAndValue, ...]\n"
            "    count: int\n"
            "    query: str\n"
            "    fuzzy_match: bool"
        ),
        h.p(h.c("src/foundation/model/id_and_value.py"), h.PATH),
        h.code(
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class IdAndValue:\n"
            "    id: str\n"
            "    value: str"
        ),
        h.p(
            f"The {h.c('frozen=True, unsafe_hash=True')} pair lets the UI cache these "
            "objects in React Query's normalized cache by structural equality, and lets "
            "them drop into a Python set in tests without ceremony."
        ),
        h.p("Wire shape", h.H2),
        h.code(
            "{\n"
            "  \"results\": [\n"
            "    { \"id\": \"DB00945\", \"value\": \"Acetylsalicylic acid\" },\n"
            "    { \"id\": \"DB00945-syn-1\", \"value\": \"Aspirin\" }\n"
            "  ],\n"
            "  \"count\": 2,\n"
            "  \"query\": \"aspirin\",\n"
            "  \"fuzzy_match\": true\n"
            "}"
        ),
        h.PageBreak(),
    ]

    # ---- 4. data source / ETL --------------------------------------------
    story += [
        h.p("4. Data source &mdash; upstream ETL pipelines", h.H1),
        h.p(
            f"This route is read-only and label-agnostic, so its data surface is "
            f"every Eugene ingest pipeline that writes a {h.c('node_name')}. Each "
            f"pipeline writes nodes via "
            f"{h.c('MERGE (n:`label` { node_id: $id }) ON CREATE SET n.node_name = ...')}, "
            f"which is the contract this Cypher reads back."
        ),
        h.p("Drug ingest", h.H2),
        *h.bullets([
            f"{h.c('src/ingest_drug_aliases.py')} &mdash; CSV ingest that writes "
            f"{h.c('(:drug)')}, {h.c('(:drug_product)')}, {h.c('(:drug_synonym)')} "
            f"nodes. The {h.c('node_name')} on a drug is the DrugBank generic name; "
            f"on a synonym it is the synonym string itself. See "
            f"{h.c('docs/EUGENE_DRUG_ALIAS_FLOW_GUIDE.pdf')} for the full trace.",
            f"Because synonyms have their own nodes, a fuzzy lookup for a brand "
            f"name typically returns the {h.c('(:drug_synonym)')} entry first; the "
            f"caller then follows {h.c('HAS_DRUG_ALIAS')} to reach the canonical "
            f"{h.c('(:drug)')} node.",
        ]),
        h.p("Patent ingest", h.H2),
        *h.bullets([
            f"{h.c('src/ingest_uspto_patents.py')} &mdash; pulls USPTO XML, "
            f"writes {h.c('(:Approved_Patent)')}, {h.c('(:Patent_Application)')}, "
            f"{h.c('(:USPTO_APPLICATION)')}, {h.c('(:USPTO_PGPUB)')} nodes. The "
            f"{h.c('node_name')} is the patent title (long, often punctuation-heavy).",
            f"Fuzzy lookups on patent titles are common &mdash; the regex path is the "
            f"intended use case there. Note the {h.c('_')} character is in the "
            "validator blacklist, which can bite when looking up titles that contain "
            "underscores (rare for USPTO titles but possible in internal seed data).",
        ]),
        h.p("Biomedical knowledge graph (primeKG)", h.H2),
        *h.bullets([
            f"{h.c('src/ingest_primekg.py')} &mdash; loads the primeKG TSVs into "
            f"{h.c('(:disease)')}, {h.c('(:gene_protein)')}, {h.c('(:pathway)')}, "
            f"{h.c('(:anatomy)')}, {h.c('(:biological_process)')}, "
            f"{h.c('(:cellular_component)')}, {h.c('(:molecular_function)')}, "
            f"{h.c('(:effect_phenotype)')}. {h.c('node_name')} comes straight "
            "from the source TSV.",
            f"Gene/protein names from primeKG are HGNC symbols (e.g. {h.c('TP53')}, "
            f"{h.c('BRCA1')}) &mdash; exact matches work well for these.",
        ]),
        h.p("Clinical trials", h.H2),
        *h.bullets([
            f"{h.c('src/ingest_clinical_trials.py')} &mdash; reads "
            f"ClinicalTrials.gov export and writes {h.c('(:ClinicalTrial)')}, "
            f"{h.c('(:Sponsor)')}, {h.c('(:Phase)')}, {h.c('(:Investigators)')}, "
            f"{h.c('(:Intervention)')}, {h.c('(:Condition)')} nodes. "
            f"{h.c('node_name')} for a trial is the trial title; for a sponsor it "
            "is the organisation name; for a condition it is the condition string.",
        ]),
        h.p("PubMed", h.H2),
        *h.bullets([
            f"{h.c('src/ingest_pubmed.py')} &mdash; writes "
            f"{h.c('(:PUBMED_DOCUMENT)')} and the GraphRAG-derived "
            f"{h.c('(:PUBMED_SUMMARY)')} / {h.c('(:PUBMED_SUMMARY_FINDING)')} "
            f"nodes. {h.c('node_name')} on a document is the article title.",
        ]),
        h.p("Corporate / seed data", h.H2),
        *h.bullets([
            f"Seed cypher files in {h.c('bin/seed/')} establish "
            f"{h.c('(:Organization)')}, {h.c('(:Research)')}, "
            f"{h.c('(:Collaborator)')}, and the canonical {h.c('(:drug)')} stubs "
            "the drug-alias pipeline later decorates.",
        ]),
        h.p("Hidden-node sources", h.H2),
        h.p(
            f"GraphRAG summary intermediates and ETL checkpoint markers carry "
            f"{h.c('is_hidden = true')} and are filtered out by the route's "
            f"{h.c('WHERE')} clause. If you add a new ETL that creates internal-only "
            f"nodes, set {h.c('is_hidden = true')} rather than picking a "
            "&ldquo;private&rdquo; label name."
        ),
        h.PageBreak(),
    ]

    # ---- 5. debug walk ---------------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Start FastAPI locally: {h.c('uvicorn src.eugene_ws:app --port 18501')}.",
            f"Hit the endpoint with a known-good name: "
            f"{h.c('curl localhost:18501/node/find/Flurandrenolide')}. Then try the "
            f"fuzzy form: "
            f"{h.c('curl &apos;localhost:18501/node/find/aspirin?fuzzy_match=true&apos;')}.",
            f"Breakpoint at {h.c('src/foundation/router/node_id_lookup_router.py:45')}. "
            f"Inspect {h.c('node_value')} and {h.c('fuzzy_match')} &mdash; the "
            "validator has already run by this point.",
            f"Step into {h.c('FoundationalNodeIdProvider.find_node_id_by_node_name')} "
            f"({h.c('foundational_node_id_provider.py:28')}).",
            f"Step into the adapter at "
            f"{h.c('neo4j_foundational_node_adapter.py:171')}; the variable "
            f"{h.c('query')} holds the Cypher exactly as printed in &sect;2 and "
            f"{h.c('params')} is either {h.c('{&quot;node_name&quot;: value}')} (exact) "
            f"or {h.c('{}')} (fuzzy).",
            f"After {h.c('execute_query')} returns, inspect the DataFrame: "
            f"{h.c('records.shape')}, {h.c('records.columns')} (note the "
            f"{h.c('n.')} prefix on column names), "
            f"{h.c('records.iloc[0].to_dict()')}.",
        ]),
        h.p("Neo4j sanity query (mirrors the route)", h.H2),
        h.p(
            f"Run these in the Neo4j browser at {h.c('http://localhost:7474')} with "
            "the same values you sent to the route. The row set should match the HTTP "
            "response one-for-one:"
        ),
        h.code(
            "// exact path\n"
            "MATCH (n { node_name: 'Flurandrenolide' })\n"
            "WHERE n.is_hidden IS NULL OR NOT n.is_hidden\n"
            "RETURN n.node_id, n.node_name;\n"
            "\n"
            "// fuzzy path (interpolation done client-side here)\n"
            "MATCH (n)\n"
            "WHERE n.node_name =~ '(?i).*aspirin.*'\n"
            "  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "RETURN n.node_id, n.node_name;"
        ),
        h.p("Common failure modes and what to check", h.H2),
        *h.bullets([
            f"<b>HTTP 422</b> &mdash; the validator rejected the value. Look at the "
            f"FastAPI error body for {h.c('value cannot have a special character')} "
            f"or {h.c('String should have at most 2048 characters')}.",
            f"<b>count: 0</b> for a value you expect to exist: "
            f"(a) the node has {h.c('is_hidden = true')}; "
            f"(b) wrong case &mdash; the exact path matches case-sensitively, try "
            f"{h.c('fuzzy_match=true')}; "
            f"(c) the value lives on a different property (e.g. "
            f"{h.c('synonym')} on a {h.c('(:drug)')} node rather than on a "
            f"{h.c('(:drug_synonym)')} node's {h.c('node_name')}).",
            f"<b>Unexpectedly huge result on fuzzy</b> &mdash; the regex "
            f"{h.c('.*x.*')} matches across all 22+ label types. Narrow with a "
            "longer value, or follow up with the label-aware "
            f"{h.c('/node/details')} or a label-scoped route.",
            f"<b>HTTP 500</b> with a {h.c('Neo4jError')} in the logs &mdash; almost "
            "always a malformed regex (unbalanced bracket, dangling quantifier). "
            f"Check the {h.c('query')} string at "
            f"{h.c('neo4j_foundational_node_adapter.py:180')}.",
        ]),
        h.PageBreak(),
    ]

    # ---- 6. reference index ----------------------------------------------
    story += [
        h.p("6. Reference index (file:line)", h.H1),
        h.code(
            "Schema\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "\n"
            "HTTP entry and wiring\n"
            "  src/eugene_ws.py:39-41                              (import)\n"
            "  src/eugene_ws.py:55-78                              (routers list + include_router)\n"
            "  src/foundation/router/node_id_lookup_router.py:14-17  (APIRouter prefix)\n"
            "  src/foundation/router/node_id_lookup_router.py:19     (DI hook)\n"
            "  src/foundation/router/node_id_lookup_router.py:22-47  (handler)\n"
            "\n"
            "Validation\n"
            "  src/foundation/router/validate_util.py:10       (specials list)\n"
            "  src/foundation/router/validate_util.py:35-42    (validate_value)\n"
            "  src/foundation/router/validate_util.py:114-128  (has_special_char / has_invalid_char)\n"
            "\n"
            "DI factories\n"
            "  src/foundation/conf/conf.py:109-114  (Neo4j adapter factory)\n"
            "  src/foundation/conf/conf.py:229-230  (mapper factory)\n"
            "  src/foundation/conf/conf.py:372-376  (provider factory entry)\n"
            "  src/foundation/conf/conf.py:379-386  (provider composition)\n"
            "\n"
            "Provider / orchestration\n"
            "  src/foundation/provider/foundational_node_id_provider.py:14-37\n"
            "\n"
            "Adapter / Cypher\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:16-23\n"
            "      class header\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:25-31\n"
            "      public entrypoint (find_node_id_by_node_name)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:171-193\n"
            "      _find_node_id_by_node_name (exact/fuzzy branch + execute_query)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:195-200\n"
            "      build_find_node_id_by_node_name (exact Cypher)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py:202-209\n"
            "      build_fuzzy_find_node_id_by_node_name (regex Cypher)\n"
            "  src/graph/util/util.py                       (ensure_connection)\n"
            "\n"
            "Mapper / response\n"
            "  src/foundation/mapper/node_id_lookup_mapper.py:14-29  (NodeIdLookupMapper.map)\n"
            "  src/foundation/mapper/node_id_lookup_mapper.py:31-34  (_map_response_rows)\n"
            "  src/foundation/mapper/node_id_lookup_mapper.py:36-42  (_map_response_row)\n"
            "  src/foundation/mapper/node_id_lookup_mapper_test.py   (unit tests)\n"
            "\n"
            "Model\n"
            "  src/foundation/model/node_id_lookup.py  (NodeIdLookup)\n"
            "  src/foundation/model/id_and_value.py    (IdAndValue)\n"
            "\n"
            "Upstream ETL (sources of node_name)\n"
            "  src/ingest_drug_aliases.py\n"
            "  src/ingest_uspto_patents.py\n"
            "  src/ingest_primekg.py\n"
            "  src/ingest_clinical_trials.py\n"
            "  src/ingest_pubmed.py\n"
            "  bin/seed/csl_behring_assets.cypher\n"
            "  bin/seed/biogen_assets.cypher\n"
            "  bin/seed/csl_drug_node_properties.cypher\n"
            "\n"
            "Related routes (consume node_id returned by this route)\n"
            "  src/foundation/router/node_details_router.py    (POST /node/details)\n"
            "  src/foundation/router/n_hop_router.py           (n-hop traversal)\n"
            "  src/foundation/router/search_path_router.py     (shortest path)\n"
        ),
    ]

    return story
