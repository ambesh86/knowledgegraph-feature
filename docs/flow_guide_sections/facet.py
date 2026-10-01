"""Per-route flow guide for Eugene's facet_router.

Endpoint: POST /facet/{label}

Walks an engineer from the FastAPI boundary, through DI wiring and the
Cypher generator, into the JSON shape returned to the caller. Every
reference is in path/to/file.py:line form so it can be opened directly
in an IDE.
"""
from __future__ import annotations

from docs.flow_guide_sections._helpers import (
    H_TITLE, H_SUB, H1, H2, BODY, BULLET, CODE, PATH,
    p, code, bullets, rule, c, Spacer, PageBreak,
)


OUT_NAME = "EUGENE_FACET_FLOW_GUIDE.pdf"
TITLE = "Eugene Facet Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---------- cover -------------------------------------------------------
    story += [
        p("Eugene Facet Search &mdash; End-to-End Flow", H_TITLE),
        p(
            "Developer walkthrough: HTTP boundary &rarr; validators &rarr; DI &rarr; "
            "Neo4j facet adapter &rarr; APOC-built JSON",
            H_SUB,
        ),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who need "
            "a single, file-referenced trace of the facet endpoint. Every "
            f"reference uses the form {c('path/to/file.py:line')} so you can open "
            "it directly in your IDE and step through with a debugger.",
        ),
        p("Reference endpoint", H2),
        p(
            f"{c('POST /facet/{{label}}')} where "
            f"{c('label')} is one of {c('drug')}, {c('disease')}. "
            f"The request body is a {c('FacetSearchValues')} JSON object: "
            f"{c('{ &quot;values&quot;: [ &quot;Lupus&quot;, &quot;rituximab&quot; ] }')}.",
        ),
        p("Sample call (Disease facets filtered by name substring)"),
        code(
            "curl -X POST http://localhost:8080/facet/disease \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"values\": [\"Lupus\"]}'\n"
        ),
        p("Sample call (Drug facets, no filter)"),
        code(
            "curl -X POST http://localhost:8080/facet/drug \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"values\": []}'\n"
        ),
        p(
            f"Declared in {c('src/foundation/router/facet_router.py:27-52')}. "
            f"Only {c('drug')} and {c('disease')} are accepted today (the "
            f"adapter raises on any other label).",
        ),
        p("How to read this guide", H2),
        *bullets([
            "Sections follow the request path top-down: HTTP &rarr; validator &rarr; "
            "DI factory &rarr; adapter &rarr; Cypher &rarr; JSON.",
            "Section 0 explains what a &quot;facet&quot; means in Eugene &mdash; "
            f"a per-label aggregate of related node-name frequencies, built with "
            f"{c('apoc.coll.frequenciesAsMap')}.",
            "Section 4 lists a concrete debugging walk (curl, breakpoints, "
            "Cypher verification).",
            "Watch for the SQL-injection FIXME the adapter author left in "
            f"{c('neo4j_foundational_facet_adapter.py:48-50')} &mdash; it is "
            "load-bearing for future hardening.",
        ]),
        PageBreak(),
    ]

    # ---------- 0. schema / context -----------------------------------------
    story += [
        p("0. What a &quot;facet&quot; means in Eugene", H1),
        p(
            "In the UI, a <i>facet</i> is the left-rail filter widget that shows "
            "&quot;Lupus (12), Rheumatoid Arthritis (8), &hellip;&quot; next to a "
            "drug list. The facet router serves the data behind that widget: for "
            f"every node with a given label (e.g. {c(':drug')}), it walks one hop "
            "to chosen sibling labels and returns frequency maps keyed by "
            f"{c('node_name')}.",
        ),
        p("Two flavours, hard-coded in the adapter", H2),
        *bullets([
            f"{c('FoundationalNodeEnum.DRUG')} &rarr; returns frequency maps for "
            f"{c('indications')}, {c('contraindications')}, "
            f"{c('offLabelUses')} (each a disease-name &rarr; count map).",
            f"{c('FoundationalNodeEnum.DISEASE')} &rarr; returns frequency maps "
            f"for {c('drugs')} and {c('geneProteins')}.",
            "Any other label raises "
            f"{c('ValueError(&quot;Found {label} but facet only suppports drug or disease!&quot;)')} "
            f"from {c('neo4j_foundational_facet_adapter.py:52-56')}.",
        ]),
        p("Relevant enum values", H2),
        p(
            f"{c('src/foundation/model/foundational_node_enum.py')}",
            PATH,
        ),
        code(
            "class FoundationalNodeEnum(Enum):\n"
            "    DISEASE = 7, \"DISEASE\".lower()   # graph label :disease\n"
            "    DRUG    = 8, \"DRUG\".lower()      # graph label :drug\n"
            "    GENE_PROTEIN = 12, \"gene_protein\"\n"
        ),
        p(
            f"The enum's second tuple slot is the Neo4j label string. "
            f"{c('str_to_label_enum(value)')} in "
            f"{c('src/foundation/router/validate_util.py:107-111')} reverses that "
            "mapping (string &rarr; enum).",
        ),
        p("Relationship types touched by the Cypher", H2),
        p(
            f"{c('src/foundation/model/foundational_relationship_enum.py')}",
            PATH,
        ),
        *bullets([
            f"{c(':indication')} &mdash; drug treats disease.",
            f"{c(':contraindication')} &mdash; drug should not be used in disease.",
            f"{c(':`off-label use`')} &mdash; note the backticks: the label "
            "contains a hyphen and a space, so Cypher must quote it.",
            "For the disease flavour, the adapter does NOT pin a relationship "
            f"type ({c('[(node)-[]-(x:drug) | properties(x)]')}) &mdash; any "
            f"edge between a {c(':disease')} and a {c(':drug')} contributes.",
        ]),
        p("Implication for debugging", H2),
        p(
            "Keep the two enum files open while reading the adapter; every "
            "Cypher string interpolates label strings from them. Also keep "
            f"{c('src/graph/util/node_util.py')} open &mdash; "
            f"{c('normalize_node_label')} is applied to the label before "
            "interpolation (lowercase, strip dots, spaces &rarr; underscores).",
        ),
        PageBreak(),
    ]

    # ---------- 1. HTTP entry -----------------------------------------------
    story += [
        p("1. HTTP entry &mdash; the FastAPI router", H1),
        p("Wiring", H2),
        p(
            f"{c('src/eugene_ws.py:45')} &mdash; "
            f"{c('from foundation.router import facet_router as foundation_facet_router')}. "
            f"{c('src/eugene_ws.py:67')} appends {c('foundation_facet_router')} to "
            f"the {c('routers')} list, and {c('src/eugene_ws.py:77-78')} loops "
            f"through and calls {c('app.include_router(router.router)')}.",
        ),
        p("Router file", H2),
        p(f"{c('src/foundation/router/facet_router.py')}", PATH),
        p("Imports (lines 1-14):"),
        code(
            "from fastapi import APIRouter, Path\n"
            "from pydantic import AfterValidator\n"
            "from foundation.conf.conf import neo4j_foundational_facet_adapter\n"
            "from foundation.router.validate_util import (\n"
            "    str_to_label_enum,\n"
            "    validate_label,\n"
            ")\n"
            "from foundation.router.model.facet_search_values import FacetSearchValues\n"
            "from foundation.router.model.facet_label import FacetLabel\n"
        ),
        p("Router declaration (lines 19-22):"),
        code(
            "router = APIRouter(\n"
            "    prefix=\"/facet\",\n"
            "    tags=[\"facet\"],\n"
            ")\n"
        ),
        p("Module-load dependency injection (line 24)", H2),
        code("foundational_facet_adapter = neo4j_foundational_facet_adapter()"),
        p(
            "This is Eugene's manual DI pattern: a module-scope call constructs "
            "the adapter once at import-time. The factory lives in "
            f"{c('src/foundation/conf/conf.py:157-164')}:",
        ),
        code(
            "def neo4j_foundational_facet_adapter() -> Neo4jFoundationalFacetAdapter:\n"
            "    return _neo4j_foundational_facet_adapter(driver=_neo4j_driver())\n"
            "\n"
            "def _neo4j_foundational_facet_adapter(\n"
            "    driver: Driver,\n"
            ") -> Neo4jFoundationalFacetAdapter:\n"
            "    return Neo4jFoundationalFacetAdapter(driver=driver)\n"
        ),
        p(
            f"{c('_neo4j_driver()')} elsewhere in {c('conf.py')} returns a singleton "
            f"{c('neo4j.Driver')} configured from env vars "
            f"({c('NEO4J_URI')}, {c('NEO4J_USERNAME')}, {c('NEO4J_PASSWORD')}). "
            "There is no framework, no decorators &mdash; module import order is the DI graph.",
        ),
        p("Endpoint handler (lines 27-52)", H2),
        code(
            "@router.post(\n"
            "    \"/{label}\",\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def collect_facets_by_label_and_values(\n"
            "    label: Annotated[\n"
            "        FacetLabel,\n"
            "        Path(\n"
            "            description=\"The node type to list. e.g. drug, disease\",\n"
            "            max_length=64, min_length=0,\n"
            "            examples=[\"drug, disease\"],\n"
            "        ),\n"
            "        AfterValidator(validate_label),\n"
            "    ],\n"
            "    facet_search_values: FacetSearchValues,\n"
            "):\n"
            "    label_enum = str_to_label_enum(label.value[1])\n"
            "    values = (\n"
            "        facet_search_values.values if facet_search_values.values is not None else []\n"
            "    )\n"
            "    json_blob = foundational_facet_adapter.collect_facet_by_label(\n"
            "        label=label_enum, values=values\n"
            "    )\n"
            "    logger.debug(f\"facet: {json_blob}\")\n"
            "    return json_blob\n"
        ),
        p("Two validation layers", H2),
        *bullets([
            f"<b>Path enum constraint</b> &mdash; {c('FacetLabel')} "
            f"({c('src/foundation/router/model/facet_label.py')}) is a "
            f"{c('str, Enum')} with only {c('disease')} and {c('drug')} members. "
            "FastAPI rejects anything else with HTTP 422 before the handler runs.",
            f"<b>AfterValidator</b> &mdash; {c('validate_label')} in "
            f"{c('src/foundation/router/validate_util.py:13-21')} double-checks "
            f"membership in the broader {c('Label')} enum and returns the "
            f"{c('FoundationalNodeEnum')}. Its return is discarded by the "
            f"handler (it then re-derives the enum via {c('str_to_label_enum')}), "
            "but the side-effect (raise on invalid) is the point.",
            "<b>Body validation</b> &mdash; Pydantic auto-validates "
            f"{c('FacetSearchValues')} ({c('list[str]')}). There is "
            f"<i>no</i> {c('validate_facet_search_values')} call in this router, "
            f"even though {c('validate_util.py:24-32')} defines one that rejects "
            "special characters. <b>This is a known gap</b> &mdash; raw values "
            "flow straight into the Cypher regex (see Section 2 FIXME).",
        ]),
        p("Set your first breakpoint", H2),
        p(
            f"At {c('facet_router.py:48')} "
            f"({c('json_blob = foundational_facet_adapter.collect_facet_by_label(...)')}). "
            "Inspect:",
        ),
        *bullets([
            f"{c('label')} &mdash; the raw {c('FacetLabel')} instance.",
            f"{c('label.value[1])')} &mdash; should be {c('&quot;drug&quot;')} or "
            f"{c('&quot;disease&quot;')}.",
            f"{c('label_enum')} &mdash; the {c('FoundationalNodeEnum')} member.",
            f"{c('values')} &mdash; the list of name fragments to filter by.",
        ]),
        PageBreak(),
    ]

    # ---------- 2. adapter / Cypher -----------------------------------------
    story += [
        p("2. Query adapter &mdash; the Cypher", H1),
        p(f"{c('src/foundation/infra/db/adapter/neo4j_foundational_facet_adapter.py')}", PATH),
        p("Public entry point (lines 23-27)", H2),
        code(
            "def collect_facet_by_label(\n"
            "    self, label: FoundationalNodeEnum, values: list[str] = []\n"
            ") -> str | None:\n"
            "    ensure_connection(self.driver)\n"
            "    return self._collect_facet_by_label(label=label, values=values)\n"
        ),
        p(
            f"{c('ensure_connection')} from {c('src/graph/util/util.py')} pings "
            "the driver before each request &mdash; a defence against stale "
            "connections after Neo4j restarts.",
        ),
        p("Inner execution (lines 29-43)", H2),
        code(
            "def _collect_facet_by_label(self, label, values) -> str | None:\n"
            "    query = self._build_facet_by_label_query(label=label, values=values)\n"
            "    logger.info(f\"facet: {query}\")\n"
            "    try:\n"
            "        records = self.driver.execute_query(\n"
            "            query_=query,\n"
            "            result_transformer_=neo4j.Result.single,\n"
            "        )\n"
            "        return records[\"json\"]\n"
            "    except (DriverError, Neo4jError) as exception:\n"
            "        logging.error(...)\n"
            "        raise exception\n"
        ),
        *bullets([
            f"{c('Result.single')} expects exactly one record &mdash; the Cypher "
            f"ends with {c('RETURN { facets: {...} } as json')}, which always "
            "produces one row.",
            f"The return type is annotated {c('str | None')} but in practice "
            f"the driver returns a Python {c('dict')} &mdash; FastAPI then "
            "serialises it as JSON.",
            "Note the missing parameter binding: no <i>params</i> are passed to "
            f"{c('execute_query')}. The Cypher is built with string "
            "interpolation. See the FIXME at lines 48-50.",
        ]),
        p("Cypher generator (lines 45-122) &mdash; structure", H2),
        p("Built in three concatenated chunks:"),
        code(
            "facet_count_query = \"\\n\".join([\n"
            "    match_clause,             # MATCH (node:`<label>`)\n"
            "    optional_where_clause,    # WHERE node.node_name =~ '(?i).*<v>.*' OR ...\n"
            "    facet_count_clause,       # the APOC frequency aggregation\n"
            "])\n"
        ),
        p("Generated Cypher for /facet/drug with values=[]", H2),
        code(
            "MATCH (node:`drug`)\n"
            "\n"
            "WITH apoc.map.merge(properties(node), {\n"
            "    nodeId: id(node),\n"
            "    indications: [(node)-[:indication]-(x:disease) | properties(x)],\n"
            "    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],\n"
            "    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]\n"
            "}) as node order by node.title\n"
            "WITH collect(node) as nodes,\n"
            "    [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,\n"
            "    [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,\n"
            "    [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses,\n"
            "    [x in apoc.coll.flatten(collect(node.indicationCount)) | x.node_name] as indicationCount,\n"
            "    [x in apoc.coll.flatten(collect(node.contraindicationCount)) | x.node_name] as contraindicationCount,\n"
            "    [x in apoc.coll.flatten(collect(node.offLabelCount)) | x] as offLabelCount\n"
            "WITH nodes,\n"
            "    apoc.coll.frequenciesAsMap(indications) as indications,\n"
            "    apoc.coll.frequenciesAsMap(contraindications) as contraindications,\n"
            "    apoc.coll.frequenciesAsMap(offLabelUses) as offLabelUses\n"
            "RETURN {\n"
            "    facets: {\n"
            "        indications: indications,\n"
            "        contraindications: contraindications,\n"
            "        offLabelUses: offLabelUses\n"
            "    }\n"
            "} as json\n"
        ),
        p("Generated Cypher for /facet/disease with values=[\"Lupus\"]", H2),
        code(
            "MATCH (node:`disease`)\n"
            "where node.node_name =~ '(?i).*Lupus.*'\n"
            "\n"
            "WITH apoc.map.merge(properties(node), {\n"
            "    nodeId: id(node),\n"
            "    drugs: [(node)-[]-(x:drug) | properties(x)],\n"
            "    geneProteins: [(node)-[]-(x:gene_protein) | properties(x)]\n"
            "}) as node order by node.title\n"
            "WITH collect(node) as nodes,\n"
            "    [x in apoc.coll.flatten(collect(node.drugs)) | x.node_name] as drugs,\n"
            "    [x in apoc.coll.flatten(collect(node.geneProteins)) | x.node_name] as geneProteins,\n"
            "    [x in apoc.coll.flatten(collect(node.drugCount)) | x] as drugCount,\n"
            "    [x in apoc.coll.flatten(collect(node.geneProteinCount)) | x.node_name] as geneProteinCount\n"
            "WITH nodes,\n"
            "    apoc.coll.frequenciesAsMap(drugs) as drugs,\n"
            "    apoc.coll.frequenciesAsMap(geneProteins) as geneProteins\n"
            "RETURN {\n"
            "    facets: {\n"
            "        drugs: drugs,\n"
            "        geneProteins: geneProteins\n"
            "    }\n"
            "} as json\n"
        ),
        p("Step-by-step what the Cypher does", H2),
        *bullets([
            f"<b>MATCH</b> all nodes carrying the requested label "
            f"({c(':drug')} or {c(':disease')}). The label string is "
            f"normalized through {c('normalize_node_label')} "
            f"({c('src/graph/util/node_util.py:4-9')}) before backtick-quoting.",
            f"<b>Optional WHERE</b> &mdash; if {c('values')} is non-empty, "
            f"one {c('node.node_name =~ &#39;(?i).*&lt;value&gt;.*&#39;')} "
            f"clause per value, joined with {c('or')}. Case-insensitive "
            "substring match.",
            f"<b>Per-row map merge</b> &mdash; for every matched node, "
            f"{c('apoc.map.merge')} attaches three (drug) or two (disease) "
            "lists of related node properties, gathered by inline "
            f"{c('[(node)-[:rel]-(x:label) | properties(x)]')} pattern comprehensions.",
            f"<b>Flatten &amp; pluck</b> &mdash; "
            f"{c('apoc.coll.flatten(collect(...))')} concatenates all the "
            f"per-node lists into one big list, and {c('| x.node_name')} "
            "extracts just the names.",
            f"<b>Frequency map</b> &mdash; "
            f"{c('apoc.coll.frequenciesAsMap')} converts "
            f"{c('[&quot;Lupus&quot;, &quot;Lupus&quot;, &quot;RA&quot;]')} into "
            f"{c('{ &quot;Lupus&quot;: 2, &quot;RA&quot;: 1 }')}. This is the "
            "facet count the UI renders.",
            f"<b>RETURN</b> &mdash; one Cypher map literal aliased as "
            f"{c('json')}; the row count is always 1 because of the "
            f"surrounding {c('WITH ... collect(...)')} aggregations.",
        ]),
        p("The injection hazard the adapter flags", H2),
        p(f"{c('neo4j_foundational_facet_adapter.py:48-50')}", PATH),
        code(
            "# FIXME: cypher injection issue\n"
            "# WARNING: this is wrong to inject a user query into the cypher\n"
            "# however the api does not let me pass a parameter into a query when\n"
            "# using a regex like this?\n"
        ),
        *bullets([
            f"User input flows raw into {c('node.node_name =~ &#39;(?i).*<value>.*&#39;')} &mdash; "
            f"a {c('&#39;')} or {c('}')} in the value would break out of the "
            "regex literal.",
            f"The router does not call {c('validate_facet_search_values')} from "
            f"{c('validate_util.py:24-32')}, which would reject the special chars "
            f"{c('% _ $ ; : ^ *')}. Until that is wired in, treat the endpoint "
            "as un-sanitised.",
            f"The fix is parameterised regex: "
            f"{c('node.node_name =~ &#39;(?i).*&#39; + $value + &#39;.*&#39;')} &mdash; "
            "Cypher allows string concatenation in regex operands, contrary to "
            "the FIXME's claim.",
        ]),
        PageBreak(),
    ]

    # ---------- 3. response mapping -----------------------------------------
    story += [
        p("3. Response shape &mdash; what the caller sees", H1),
        p(
            "Unlike most Eugene routers (patent, pubmed, etc.) there is "
            "<b>no Pydantic response model and no mapper</b>. The Cypher "
            f"returns a {c('Map')}; the Python driver hands it back as a "
            f"{c('dict')}; FastAPI serialises that {c('dict')} directly. The "
            "absence of a typed response is intentional &mdash; the keys of the "
            "frequency maps are user data (disease names, drug names) and "
            "cannot be enumerated at schema time.",
        ),
        p("Example response &mdash; POST /facet/drug, values=[]", H2),
        code(
            "{\n"
            "  \"facets\": {\n"
            "    \"indications\": {\n"
            "      \"Systemic Lupus Erythematosus\": 12,\n"
            "      \"Rheumatoid Arthritis\": 8,\n"
            "      \"Multiple Sclerosis\": 5\n"
            "    },\n"
            "    \"contraindications\": {\n"
            "      \"Pregnancy\": 21,\n"
            "      \"Hepatic Impairment\": 14\n"
            "    },\n"
            "    \"offLabelUses\": {\n"
            "      \"Idiopathic Thrombocytopenic Purpura\": 3\n"
            "    }\n"
            "  }\n"
            "}\n"
        ),
        p("Example response &mdash; POST /facet/disease, values=[\"Lupus\"]", H2),
        code(
            "{\n"
            "  \"facets\": {\n"
            "    \"drugs\": {\n"
            "      \"rituximab\": 4,\n"
            "      \"hydroxychloroquine\": 7,\n"
            "      \"belimumab\": 2\n"
            "    },\n"
            "    \"geneProteins\": {\n"
            "      \"IFNAR1\": 3,\n"
            "      \"TNFSF13B\": 2\n"
            "    }\n"
            "  }\n"
            "}\n"
        ),
        p("Request models &mdash; the only typed surface", H2),
        p(f"{c('src/foundation/router/model/facet_label.py')}", PATH),
        code(
            "from enum import Enum\n"
            "\n"
            "class FacetLabel(str, Enum):\n"
            "    disease = \"disease\"\n"
            "    drug    = \"drug\"\n"
        ),
        p(f"{c('src/foundation/router/model/facet_search_values.py')}", PATH),
        code(
            "from typing import Annotated\n"
            "from pydantic import BaseModel, Field\n"
            "\n"
            "class FacetSearchValues(BaseModel):\n"
            "    values: list[Annotated[str, Field(None, examples=[\"Lupus\"])]]\n"
        ),
        *bullets([
            f"{c('values')} is a required field (no default). To get unfiltered "
            f"facets, send {c('{ &quot;values&quot;: [] }')}, not "
            f"{c('{}')}.",
            f"The handler defensively guards {c('facet_search_values.values is not None')} "
            f"at {c('facet_router.py:45-47')}, but Pydantic would already have "
            f"rejected a {c('null')} (the type is "
            f"{c('list[str]')}, not {c('list[str] | None')}).",
        ]),
        PageBreak(),
    ]

    # ---------- 4. debug walk -----------------------------------------------
    story += [
        p("4. Suggested debugging walk", H1),
        p("4.1 Start the API", H2),
        code(
            "# from repo root\n"
            "uvicorn src.eugene_ws:app --reload --port 8080\n"
        ),
        p(
            f"On import, {c('src/foundation/router/facet_router.py:24')} runs "
            f"{c('neo4j_foundational_facet_adapter()')}. If Neo4j is not "
            f"reachable, this is where you'll see the connection error &mdash; "
            "not when the first request hits the endpoint.",
        ),
        p("4.2 Issue a request", H2),
        code(
            "curl -s -X POST http://localhost:8080/facet/disease \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"values\": [\"Lupus\"]}' | jq .\n"
        ),
        p("4.3 Recommended breakpoints", H2),
        *bullets([
            f"{c('src/foundation/router/facet_router.py:44')} &mdash; "
            f"inspect {c('label')} and {c('facet_search_values.values')}.",
            f"{c('src/foundation/router/facet_router.py:48')} &mdash; "
            f"about to hand off to the adapter; verify "
            f"{c('label_enum')} is the right {c('FoundationalNodeEnum')} member.",
            f"{c('src/foundation/infra/db/adapter/neo4j_foundational_facet_adapter.py:33')} &mdash; "
            f"a {c('logger.info(f&quot;facet: {query}&quot;)')} prints the "
            "fully interpolated Cypher. Copy this into Neo4j Browser if the "
            "response looks wrong.",
            f"{c('neo4j_foundational_facet_adapter.py:35-38')} &mdash; the actual "
            f"{c('driver.execute_query')} call; step over to see the raw "
            f"{c('records')} dict.",
        ]),
        p("4.4 Tail logs for the generated Cypher", H2),
        code(
            "# In another terminal\n"
            "tail -f logs/eugene_ws.log | grep -E '^facet: |cypher response'\n"
            "\n"
            "# The adapter logs the Cypher at INFO and the response at DEBUG.\n"
            "# Set LOG_LEVEL=DEBUG in your env to see both.\n"
        ),
        p("4.5 Verify directly against Neo4j", H2),
        p(
            "Paste the logged Cypher into Neo4j Browser (or "
            f"{c('cypher-shell')}):",
        ),
        code(
            "cypher-shell -u neo4j -p password \\\n"
            "  \"MATCH (node:\\`disease\\`) WHERE node.node_name =~ '(?i).*Lupus.*' \\\n"
            "   RETURN node.node_name, node.node_id LIMIT 10;\"\n"
        ),
        p(
            "If this returns zero rows, your facet response will be "
            f"{c('{ &quot;facets&quot;: { &quot;drugs&quot;: {}, &quot;geneProteins&quot;: {} } }')} &mdash; "
            "an empty result, not an error.",
        ),
        p("4.6 Sanity-check the relationship coverage", H2),
        code(
            "MATCH (d:drug)-[r:indication|contraindication|`off-label use`]-(:disease)\n"
            "RETURN type(r) AS rel, count(*) AS n\n"
            "ORDER BY n DESC;\n"
        ),
        p(
            "If one of these rel types returns 0 rows, the facet response will "
            "have an empty bucket for that key &mdash; a hint the underlying "
            "ETL never created those edges (check the drug ingest job and the "
            f"{c('foundational_relationship_enum.py')} entries).",
        ),
        p("4.7 Common failure modes", H2),
        *bullets([
            f"<b>422 Unprocessable Entity</b> &mdash; you sent "
            f"{c('/facet/gene_protein')} or any label outside the "
            f"{c('FacetLabel')} enum. The route never reaches the handler.",
            f"<b>500 with &quot;Found ... but facet only suppports drug or "
            f"disease&quot;</b> &mdash; impossible via HTTP today (the path "
            "enum blocks it), but possible from a unit test that calls the "
            f"adapter directly with another {c('FoundationalNodeEnum')} member.",
            f"<b>Neo4j syntax error</b> &mdash; almost always a special char in "
            f"{c('values')} that broke the regex literal. See the FIXME at "
            f"{c('neo4j_foundational_facet_adapter.py:48-50')}. Sanitise on the "
            "client until that's fixed.",
            f"<b>Empty {c('facets')} buckets</b> &mdash; the substring matched "
            "no nodes, or the matched nodes have no neighbouring edges of the "
            "expected type. Run the verification Cyphers in 4.5 / 4.6.",
        ]),
        PageBreak(),
    ]

    # ---------- 5. reference index ------------------------------------------
    story += [
        p("5. Reference index (file paths)", H1),
        code(
            "Router & request models\n"
            "  src/foundation/router/facet_router.py\n"
            "  src/foundation/router/model/facet_label.py\n"
            "  src/foundation/router/model/facet_search_values.py\n"
            "  src/foundation/router/validate_util.py\n"
            "\n"
            "Wiring\n"
            "  src/eugene_ws.py                       (lines 45, 67, 77-78)\n"
            "  src/foundation/conf/conf.py            (lines 157-164)\n"
            "\n"
            "Adapter (Cypher generation + execution)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_facet_adapter.py\n"
            "  src/graph/util/util.py                 (ensure_connection)\n"
            "  src/graph/util/node_util.py            (normalize_node_label)\n"
            "\n"
            "Schema enums\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "\n"
            "Related routes that share the validator helpers\n"
            "  src/foundation/router/count_router.py\n"
            "  src/foundation/router/node_details_router.py\n"
            "  src/foundation/router/label_router.py\n"
        ),
        p("Key takeaways", H2),
        *bullets([
            f"The facet endpoint is intentionally narrow: only "
            f"{c('drug')} and {c('disease')} labels, two hard-coded "
            "aggregation shapes.",
            f"There is no mapper, no Pydantic response model &mdash; the "
            f"Cypher's {c('RETURN { facets: {...} } as json')} is the "
            "schema, and the dict travels straight from Neo4j to the wire.",
            f"The {c('=~')} regex filter is the only injection-prone surface in "
            "this route. Validate values on the client until the FIXME at "
            f"{c('neo4j_foundational_facet_adapter.py:48-50')} is resolved.",
            f"APOC procedures ({c('apoc.coll.frequenciesAsMap')}, "
            f"{c('apoc.coll.flatten')}, {c('apoc.map.merge')}) are required "
            "&mdash; ensure your Neo4j image includes the APOC jar (see "
            f"{c('containers/eugene_neo4j_ce/conf/apoc.conf')}).",
        ]),
    ]

    return story
