"""Per-route flow guide for Eugene's label_router.

Endpoint: GET /labels/{label}?page=&page_size=

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


OUT_NAME = "EUGENE_LABEL_FLOW_GUIDE.pdf"
TITLE = "Eugene Label Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---------- cover -------------------------------------------------------
    story += [
        p("Eugene Label Route &mdash; End-to-End Flow", H_TITLE),
        p(
            "Developer walkthrough: HTTP boundary &rarr; validators &rarr; DI &rarr; "
            "paginated Neo4j label scan &rarr; NameAndIdListResponse",
            H_SUB,
        ),
        rule(),
        Spacer(1, 12),
        p("Audience", H2),
        p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who "
            f"need a single, file-referenced trace of the {c('GET /labels/{label}')} "
            f"endpoint. This is the simplest read route in Eugene &mdash; it lists "
            f"the {c('node_id')} / {c('node_name')} pairs of every node carrying "
            "a given Neo4j label, paginated. Every reference uses the form "
            f"{c('path/to/file.py:line')} so you can open it directly in your IDE "
            "and step through with a debugger.",
        ),
        p("Reference endpoint", H2),
        p(
            f"{c('GET /labels/{{label}}?page=&lt;n&gt;&amp;page_size=&lt;m&gt;')} &mdash; "
            f"{c('label')} is one of nine string values exposed by the "
            f"{c('Label')} enum (Section 0). The response is a "
            f"{c('NameAndIdListResponse')}: a count and a list of "
            f"{c('{name, id}')} objects.",
        ),
        p("Sample call"),
        code(
            "curl -s 'http://localhost:8080/labels/drug?page=1&page_size=25' | jq .\n"
        ),
        p(
            f"Declared in {c('src/foundation/router/label_router.py:30-62')}. "
            f"Router prefix {c('/labels')}, tag {c('foundation')}.",
        ),
        p("How to read this guide", H2),
        *bullets([
            "Sections follow the request path top-down: schema &rarr; HTTP &rarr; "
            "validator &rarr; DI factory &rarr; adapter &rarr; Cypher &rarr; "
            "mapper &rarr; JSON.",
            f"Section 0 maps the {c('Label')} enum values onto the "
            f"{c('FoundationalNodeEnum')} tuples that hold the actual Neo4j "
            "label strings.",
            "Section 5 lists a concrete debugging walk (curl, breakpoints, "
            "Cypher verification).",
            f"Note: the route is paginated via {c('page')} and {c('page_size')} "
            f"query params; the adapter does {c('SKIP/LIMIT')} arithmetic via "
            f"the {c('Pagination')} helper.",
        ]),
        PageBreak(),
    ]

    # ---------- 0. schema ---------------------------------------------------
    story += [
        p("0. Schema (read this first)", H1),
        p(
            f"Two enums collaborate here. {c('Label')} is the public, "
            f"FastAPI-facing surface &mdash; the set of label strings a client "
            f"is allowed to send. {c('FoundationalNodeEnum')} is the internal "
            f"surface &mdash; a numeric id plus the actual Neo4j label string "
            f"used in Cypher. The validator translates from one to the other.",
        ),
        p("Public Label enum", H2),
        p(f"{c('src/foundation/router/model/label.py')}", PATH),
        code(
            "from enum import Enum\n"
            "\n"
            "class Label(str, Enum):\n"
            "    anatomy            = \"anatomy\"\n"
            "    biological_process = \"biological_process\"\n"
            "    disease            = \"disease\"\n"
            "    drug               = \"drug\"\n"
            "    effect_phenotype   = \"effect_phenotype\"\n"
            "    exposure           = \"exposure\"\n"
            "    gene_protein       = \"gene_protein\"\n"
            "    molecular_function = \"molecular_function\"\n"
            "    pathway            = \"pathway\"\n"
        ),
        p(
            f"Anything outside this nine-value set is rejected with HTTP 422 "
            f"by FastAPI before the handler runs &mdash; the path parameter is "
            f"typed {c('Label')} and FastAPI enforces enum membership "
            "automatically.",
        ),
        p("Internal FoundationalNodeEnum", H2),
        p(f"{c('src/foundation/model/foundational_node_enum.py')}", PATH),
        code(
            "class FoundationalNodeEnum(Enum):\n"
            "    ANATOMY            = 1,  \"anatomy\"\n"
            "    BIOLOGICAL_PROCESS = 2,  \"biological_process\"\n"
            "    CELLULAR_COMPONENT = 3,  \"cellular_component\"\n"
            "    CLINICAL_TRIAL     = 4,  \"ClinicalTrial\"\n"
            "    COLLABORATOR       = 5,  \"collaborator\"\n"
            "    CONDITION          = 6,  \"condition\"\n"
            "    DISEASE            = 7,  \"disease\"\n"
            "    DRUG               = 8,  \"drug\"\n"
            "    EFFECT_PHENOTYPE   = 9,  \"effect_phenotype\"\n"
            "    EXPOSURE           = 10, \"exposure\"\n"
            "    GENE_PROTEIN       = 12, \"gene_protein\"\n"
            "    MOLECULAR_FUNCTION = 14, \"molecular_function\"\n"
            "    PATHWAY            = 15, \"pathway\"\n"
            "    # ... and many more (PATENT, PHASE, SPONSOR, DRUG_PRODUCT, ...)\n"
        ),
        p("Label &harr; Neo4j label string mapping", H2),
        *bullets([
            f"Each {c('FoundationalNodeEnum')} member is a "
            f"{c('(int_id, label_string)')} tuple. The second slot is the "
            "Neo4j label that appears verbatim in Cypher.",
            f"Most labels are lowercased Python names: "
            f"{c('DRUG.value == (8, &quot;drug&quot;)')}, "
            f"{c('GENE_PROTEIN.value == (12, &quot;gene_protein&quot;)')}.",
            f"A few are CamelCase to match historical seed data &mdash; e.g. "
            f"{c('CLINICAL_TRIAL.value == (4, &quot;ClinicalTrial&quot;)')}, "
            f"{c('ORGANIZATION.value == (32, &quot;Organization&quot;)')}. "
            "These are <b>not</b> exposed via the public Label enum, so the "
            "label route cannot list them today.",
            f"The {c('Label')} enum is a deliberate subset &mdash; nine "
            f"biomedical labels. {c('Patent')}, {c('Sponsor')}, "
            f"{c('Organization')}, {c('Investigators')}, GraphRAG and PubMed "
            "labels are not listable through this route.",
        ]),
        p("How the two enums meet", H2),
        p(
            f"{c('validate_label')} in "
            f"{c('src/foundation/router/validate_util.py:13-21')} converts the "
            f"path-parameter {c('Label')} into a {c('FoundationalNodeEnum')} via "
            f"{c('str_to_label_enum(label.value)')} "
            f"({c('validate_util.py:107-111')}):",
        ),
        code(
            "def str_to_label_enum(value: str):\n"
            "    for el in list(FoundationalNodeEnum):\n"
            "        if el.value[1] == value:\n"
            "            return el\n"
            "    raise ValueError(f\"'{value}' is not a valid FoundationalNode\")\n"
        ),
        p(
            f"The handler then pulls {c('label.value[1]')} out of the returned "
            f"enum and hands the raw label string to the adapter. "
            f"{c('normalize_node_label')} (in "
            f"{c('src/graph/util/node_util.py:4')}) is applied inside the adapter "
            "before backtick-quoting in Cypher.",
        ),
        PageBreak(),
    ]

    # ---------- 1. HTTP entry -----------------------------------------------
    story += [
        p("1. HTTP entry &mdash; the FastAPI router", H1),
        p("Wiring", H2),
        p(
            f"{c('src/eugene_ws.py:35')} &mdash; "
            f"{c('from foundation.router import label_router as foundation_label_router')}. "
            f"{c('src/eugene_ws.py:62')} appends "
            f"{c('foundation_label_router')} to the {c('routers')} list, and "
            f"{c('src/eugene_ws.py:77-78')} loops through and calls "
            f"{c('app.include_router(router.router)')}.",
        ),
        p("Router file", H2),
        p(f"{c('src/foundation/router/label_router.py')}", PATH),
        p("Imports (lines 1-17):"),
        code(
            "import logging\n"
            "from typing import Annotated\n"
            "\n"
            "from fastapi import APIRouter, Path, Query\n"
            "from pydantic import AfterValidator\n"
            "\n"
            "from foundation.conf.conf import (\n"
            "    neo4j_foundational_node_adapter,\n"
            ")\n"
            "from foundation.router.model.name_id_list_response import NameAndIdListResponse\n"
            "from foundation.router.response_util import (\n"
            "    to_id_list_response,\n"
            ")\n"
            "from foundation.router.validate_util import (\n"
            "    validate_label,\n"
            ")\n"
            "from foundation.router.model.label import Label\n"
        ),
        p("Router declaration (lines 22-25)"),
        code(
            "router = APIRouter(\n"
            "    prefix=\"/labels\",\n"
            "    tags=[\"foundation\"],\n"
            ")\n"
        ),
        p("Module-load dependency injection (line 27)", H2),
        code("foundational_node_adapter = neo4j_foundational_node_adapter()"),
        p(
            f"Eugene's manual DI pattern: a module-scope call constructs the "
            f"adapter once at import-time. The factory lives in "
            f"{c('src/foundation/conf/conf.py:109-114')}:",
        ),
        code(
            "def neo4j_foundational_node_adapter() -> Neo4jFoundationalNodeAdapter:\n"
            "    return _neo4j_foundational_node_adapter(driver=_neo4j_driver())\n"
            "\n"
            "def _neo4j_foundational_node_adapter(\n"
            "    driver: Driver,\n"
            ") -> Neo4jFoundationalNodeAdapter:\n"
            "    return Neo4jFoundationalNodeAdapter(driver=driver)\n"
        ),
        p(
            f"{c('_neo4j_driver()')} ({c('conf.py:95-96')}) returns a singleton "
            f"{c('neo4j.Driver')} via "
            f"{c('GraphDbConnectionFactory.remote_neo4j_instance_from_env()')} &mdash; "
            f"configured from {c('NEO4J_URI')}, {c('NEO4J_USERNAME')}, "
            f"{c('NEO4J_PASSWORD')}. No framework, no decorators &mdash; module "
            "import order is the DI graph.",
        ),
        p("Endpoint handler (lines 30-62)", H2),
        code(
            "@router.get(\n"
            "    \"/{label}\", response_model=NameAndIdListResponse, response_model_exclude_none=True\n"
            ")\n"
            "async def list_by_label(\n"
            "    label: Annotated[\n"
            "        Label,\n"
            "        Path(\n"
            "            description=\"The node type to list. e.g. drug, disease\",\n"
            "            max_length=64,\n"
            "            min_length=1,\n"
            "        ),\n"
            "        AfterValidator(validate_label),\n"
            "    ],\n"
            "    page: Annotated[\n"
            "        int,\n"
            "        Query(\n"
            "            description=\"Page number. See the count endpoint to calculate max page number.\",\n"
            "            example=1,\n"
            "            gt=0,\n"
            "        ),\n"
            "    ],\n"
            "    page_size: Annotated[\n"
            "        int,\n"
            "        Query(\n"
            "            description=\"Page size.\",\n"
            "            example=25,\n"
            "            gt=0,\n"
            "            le=50,\n"
            "        ),\n"
            "    ],\n"
            "):\n"
            "    dataframe = foundational_node_adapter.find_by_label(label.value[1], page, page_size)\n"
            "    return to_id_list_response(dataframe)\n"
        ),
        p("Three validation layers", H2),
        *bullets([
            f"<b>Path enum constraint</b> &mdash; {c('Label')} "
            f"({c('src/foundation/router/model/label.py')}) is a "
            f"{c('str, Enum')} with nine members. FastAPI rejects anything "
            "else with HTTP 422 before the handler runs.",
            f"<b>Path length</b> &mdash; {c('min_length=1, max_length=64')} "
            "on the path parameter (defensive; the enum is already shorter).",
            f"<b>AfterValidator</b> &mdash; {c('validate_label')} "
            f"({c('validate_util.py:13-21')}) re-checks membership in "
            f"{c('Label')} and returns the corresponding "
            f"{c('FoundationalNodeEnum')} member. <b>The handler discards "
            f"this return</b> &mdash; it then re-derives the label string from "
            f"{c('label.value[1]')} on the original {c('Label')} instance "
            "(the AfterValidator's return is never bound to anything).",
            f"<b>Query bounds</b> &mdash; {c('page')} must be "
            f"{c('&gt; 0')}; {c('page_size')} must be {c('&gt; 0 and &lt;= 50')}. "
            f"FastAPI rejects out-of-range values with 422. <b>Pages are not "
            f"server-capped</b> &mdash; a caller can request {c('page=10000')} "
            "and get an empty result rather than an error.",
        ]),
        p("Watch-out: redundant validator", H2),
        p(
            f"Because {c('label: Annotated[Label, ...]')} already constrains "
            f"the input to a {c('Label')} member, {c('validate_label')} can "
            f"never actually fail here &mdash; FastAPI has already coerced or "
            f"rejected the value. The AfterValidator's real value is its "
            f"side-effect-free conversion to {c('FoundationalNodeEnum')}, "
            "which (as noted) the handler ignores. Treat this as historical "
            "shape that other routes (count, similarity) still depend on.",
        ),
        p("Set your first breakpoint", H2),
        p(
            f"At {c('label_router.py:61')} (the "
            f"{c('foundational_node_adapter.find_by_label(...)')} call). Inspect:",
        ),
        *bullets([
            f"{c('label')} &mdash; the raw {c('Label')} enum instance.",
            f"{c('label.value')} &mdash; the underlying string (e.g. "
            f"{c('&quot;drug&quot;')}).",
            f"{c('page')}, {c('page_size')} &mdash; the pagination ints.",
        ]),
        PageBreak(),
    ]

    # ---------- 2. adapter / Cypher -----------------------------------------
    story += [
        p("2. Query adapter &mdash; the Cypher", H1),
        p(f"{c('src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py')}", PATH),
        p("Public entry point (lines 40-44)", H2),
        code(
            "def find_by_label(\n"
            "    self, label: str, page: int, page_size: int\n"
            ") -> pd.DataFrame | None:\n"
            "    ensure_connection(self.driver)\n"
            "    return self._find_by_label(label, page, page_size)\n"
        ),
        p(
            f"{c('ensure_connection')} from {c('src/graph/util/util.py')} pings "
            "the driver before each request &mdash; defends against stale "
            "connections after Neo4j restarts.",
        ),
        p("Inner execution (lines 105-119)", H2),
        code(
            "def _find_by_label(\n"
            "    self, label: str, page: int, page_size: int\n"
            ") -> pd.DataFrame | None:\n"
            "    query = self._build_find_by_label(label, page, page_size)\n"
            "    logger.debug(f\"find all: {query}\")\n"
            "    try:\n"
            "        records = self.driver.execute_query(\n"
            "            query_=query,\n"
            "            result_transformer_=neo4j.Result.to_df,\n"
            "        )\n"
            "        logger.debug(f\"cypher response: {records}\")\n"
            "        return records\n"
            "    except (DriverError, Neo4jError) as exception:\n"
            "        logging.error(\"%s raised an error: \\n%s\", query, exception)\n"
            "        raise exception\n"
        ),
        *bullets([
            f"{c('Result.to_df')} hands back a pandas {c('DataFrame')} &mdash; "
            f"two columns, {c('node_id')} and {c('node_name')}.",
            f"<b>No parameter binding</b> &mdash; label, offset, and limit are "
            f"all string-interpolated into the Cypher (see the FIXME comment "
            f"in {c('neo4j_foundational_facet_adapter.py')} for prior art on "
            f"why this happens). For this route the risk is mitigated by the "
            f"enum constraint on {c('label')} and the integer types on "
            "page / page_size &mdash; nothing user-typed reaches the Cypher.",
        ]),
        p("Cypher generator (lines 130-142)", H2),
        code(
            "def _build_find_by_label(self, label: str, page: int, page_size: int) -> str:\n"
            "    limit, offset = Pagination.calculate_limit_and_offset(page, page_size)\n"
            "    lookup_node_query = \"\"\"MATCH (n:`%s`)\n"
            "            RETURN n.node_id as node_id, n.node_name as node_name\n"
            "            ORDER BY node_name\n"
            "            SKIP %s\n"
            "            LIMIT %s\n"
            "        \"\"\" % (\n"
            "        normalize_node_label(label),\n"
            "        offset,\n"
            "        limit,\n"
            "    )\n"
            "    return lookup_node_query\n"
        ),
        p("Pagination math", H2),
        p(f"{c('src/foundation/infra/db/util/pagination.py')}", PATH),
        code(
            "class Pagination:\n"
            "    @staticmethod\n"
            "    def calculate_limit_and_offset(\n"
            "        page: int = 1, page_size: int = 25\n"
            "    ) -> Tuple[int, int]:\n"
            "        if page &lt; 1 or page_size &lt; 1:\n"
            "            raise ValueError(...)\n"
            "        limit  = page_size\n"
            "        offset = (page - 1) * page_size\n"
            "        return limit, offset\n"
        ),
        p(
            f"So {c('page=2, page_size=25')} &rarr; "
            f"{c('SKIP 25 LIMIT 25')} (rows 26..50 in name order). The "
            f"FastAPI handler has already enforced {c('page &gt; 0')} and "
            f"{c('0 &lt; page_size &lt;= 50')}, so the {c('ValueError')} branch "
            "is unreachable from HTTP.",
        ),
        p("Generated Cypher for /labels/drug?page=1&page_size=25", H2),
        code(
            "MATCH (n:`drug`)\n"
            "        RETURN n.node_id as node_id, n.node_name as node_name\n"
            "        ORDER BY node_name\n"
            "        SKIP 0\n"
            "        LIMIT 25\n"
        ),
        p("Generated Cypher for /labels/gene_protein?page=3&page_size=10", H2),
        code(
            "MATCH (n:`gene_protein`)\n"
            "        RETURN n.node_id as node_id, n.node_name as node_name\n"
            "        ORDER BY node_name\n"
            "        SKIP 20\n"
            "        LIMIT 10\n"
        ),
        p("Step-by-step what the Cypher does", H2),
        *bullets([
            f"<b>MATCH</b> &mdash; scans every node carrying the requested "
            f"label. The label string is normalised via "
            f"{c('normalize_node_label(label)')} "
            f"({c('src/graph/util/node_util.py:4')}) before backtick-quoting. "
            "Backticks are required because some labels (e.g. ClinicalTrial, "
            "off-label use) contain mixed case or punctuation.",
            f"<b>RETURN</b> &mdash; only the two columns the mapper needs: "
            f"{c('node_id')} and {c('node_name')}. There is no "
            f"{c('is_hidden')} filter here (unlike the drug-alias route) &mdash; "
            f"hidden nodes appear in label listings.",
            f"<b>ORDER BY node_name</b> &mdash; alphabetical so pagination is "
            f"stable. Note: the order is by the {c('node_name')} alias defined "
            f"in {c('RETURN')}, not the property directly &mdash; equivalent "
            "but worth knowing if you adapt the query.",
            f"<b>SKIP / LIMIT</b> &mdash; interpolated ints, never bound "
            f"params. Safe because the handler types them as {c('int')}.",
            f"<b>No index hint</b> &mdash; relies on Neo4j's label index for "
            f"the {c('MATCH')} and an in-memory sort for the "
            f"{c('ORDER BY')}. At &gt;10k nodes per label this can get slow; "
            "consider a property index on node_name if you see latency.",
        ]),
        PageBreak(),
    ]

    # ---------- 3. mapper / response model ----------------------------------
    story += [
        p("3. Mapper &amp; response model", H1),
        p(
            f"The adapter returns a pandas {c('DataFrame')}; "
            f"{c('to_id_list_response')} in "
            f"{c('src/foundation/router/response_util.py:24-39')} converts it "
            f"into the typed {c('NameAndIdListResponse')} that FastAPI then "
            "serialises.",
        ),
        p("Mapper function", H2),
        p(f"{c('src/foundation/router/response_util.py')}", PATH),
        code(
            "def to_id_list_response(\n"
            "    dataframe: pd.DataFrame | None,\n"
            ") -> NameAndIdListResponse:\n"
            "    if dataframe is None or len(dataframe) == 0:\n"
            "        return NameAndIdListResponse(count=0, results=[])\n"
            "\n"
            "    results = [el for el in dataframe.apply(_to_name_and_id, axis=1) if el is not None]\n"
            "    return NameAndIdListResponse(count=len(results), results=results)\n"
            "\n"
            "def _to_name_and_id(row: pd.Series) -> NameAndId | None:\n"
            "    name_key = \"node_name\"\n"
            "    id_key   = \"node_id\"\n"
            "    if row is None or name_key not in row or row[name_key] is None:\n"
            "        return None\n"
            "    return NameAndId(name=row[name_key], id=row[id_key])\n"
        ),
        *bullets([
            f"Empty / null DataFrame &rarr; "
            f"{c('NameAndIdListResponse(count=0, results=[])')} &mdash; the route "
            "never returns 404 for an empty label.",
            f"Rows with a missing {c('node_name')} are dropped silently. Rows "
            f"with {c('node_name')} present but {c('node_id')} missing are "
            f"<b>not</b> dropped &mdash; the resulting {c('NameAndId(id=None)')} "
            f"will fail Pydantic validation (id is typed {c('str')}). In "
            f"practice every node has both, but if you see a 500 from this "
            "route, check for orphan nodes missing node_id.",
            f"{c('count')} is the length of the returned page, <b>not</b> the "
            f"total number of nodes with that label. Use "
            f"{c('GET /count/{{label}}')} (the count router) to get the "
            "grand total for pagination math.",
        ]),
        p("Response models", H2),
        p(f"{c('src/foundation/router/model/name_id_list_response.py')}", PATH),
        code(
            "from pydantic import BaseModel\n"
            "from foundation.router.model.name_and_id import NameAndId\n"
            "\n"
            "class NameAndIdListResponse(BaseModel):\n"
            "    count: int\n"
            "    results: list[NameAndId]\n"
        ),
        p(f"{c('src/foundation/router/model/name_and_id.py')}", PATH),
        code(
            "from pydantic import BaseModel\n"
            "\n"
            "class NameAndId(BaseModel):\n"
            "    name: str\n"
            "    id: str\n"
        ),
        p("Example response &mdash; GET /labels/drug?page=1&page_size=5", H2),
        code(
            "{\n"
            "  \"count\": 5,\n"
            "  \"results\": [\n"
            "    { \"name\": \"abatacept\",        \"id\": \"DB01281\" },\n"
            "    { \"name\": \"abciximab\",        \"id\": \"DB00054\" },\n"
            "    { \"name\": \"acetaminophen\",    \"id\": \"DB00316\" },\n"
            "    { \"name\": \"acetylsalicylic acid\", \"id\": \"DB00945\" },\n"
            "    { \"name\": \"adalimumab\",       \"id\": \"DB00051\" }\n"
            "  ]\n"
            "}\n"
        ),
        p("Example response &mdash; GET /labels/exposure?page=99&page_size=25", H2),
        code(
            "{\n"
            "  \"count\": 0,\n"
            "  \"results\": []\n"
            "}\n"
        ),
        p(
            f"Empty page = past the end of the data, not an error. The HTTP "
            f"status is still 200. The {c('response_model_exclude_none=True')} "
            f"flag on the decorator strips any {c('None')} fields from "
            "individual NameAndId entries (defensive; both fields are required).",
        ),
        PageBreak(),
    ]

    # ---------- 4. data source ----------------------------------------------
    story += [
        p("4. Data source &mdash; where do label data come from?", H1),
        p(
            "The label route is read-only. It never writes. The nodes it "
            "enumerates are seeded by a mixture of ETL jobs and Cypher seed "
            "files; the route just trusts that the labels are present in Neo4j.",
        ),
        p("ETL inputs (the biomedical core)", H2),
        *bullets([
            f"{c(':drug')}, {c(':disease')}, {c(':gene_protein')}, "
            f"{c(':anatomy')}, {c(':biological_process')}, "
            f"{c(':effect_phenotype')}, {c(':exposure')}, "
            f"{c(':molecular_function')}, {c(':pathway')} &mdash; all originate "
            f"from the PrimeKG-style TSV ingest under "
            f"{c('src/foundation/load/')}. Each loader writes one "
            f"{c('MERGE')} per row keyed by {c('node_id')} (DrugBank id, MONDO "
            "id, etc.).",
            f"Seed Cypher under {c('bin/seed/')} (e.g. "
            f"{c('csl_behring_assets.cypher')}) adds CSL-specific drug nodes "
            f"on top of the PrimeKG core. Both paths use {c('MERGE')} on "
            f"{c('node_id')} so re-runs are idempotent.",
            f"Aliases (the {c(':drug_product')} / {c(':drug_synonym')} labels) "
            f"are <b>not</b> exposed via this route &mdash; they live outside "
            f"the {c('Label')} enum. To list them you'd add an enum value and "
            "re-seed.",
        ]),
        p("Property contract the mapper depends on", H2),
        *bullets([
            f"Every node returned must carry both {c('node_id')} and "
            f"{c('node_name')}. The seed scripts enforce this; if an ad-hoc "
            "import skips node_id, that row will surface as a 500 from this "
            "route (Pydantic validation failure on NameAndId.id).",
            f"<b>No constraints, no uniqueness</b> &mdash; Eugene's Neo4j has no "
            f"{c('CREATE CONSTRAINT')} statements. De-duplication is achieved "
            f"purely by {c('MERGE')} on {c('node_id')}. If two ETL paths use "
            "different node_ids for the same biological entity, you will see "
            "the same name twice with different ids in the response.",
            f"The {c('is_hidden')} property is honoured by some routes "
            "(drug-alias search, node-id lookup) but <b>not</b> by this one. "
            "Hidden nodes are listed.",
        ]),
        p("How to confirm what's in your database", H2),
        code(
            "// Total nodes per label exposed by /labels:\n"
            "CALL db.labels() YIELD label\n"
            "WHERE label IN ['anatomy','biological_process','disease','drug',\n"
            "                'effect_phenotype','exposure','gene_protein',\n"
            "                'molecular_function','pathway']\n"
            "CALL apoc.cypher.run('MATCH (n:`'+label+'`) RETURN count(n) AS n', {})\n"
            "  YIELD value\n"
            "RETURN label, value.n AS count\n"
            "ORDER BY count DESC;\n"
        ),
        p(
            f"If a label returns {c('0')} here, every page of "
            f"{c('GET /labels/<that label>')} will be empty. That is a data "
            "problem, not a route bug.",
        ),
        PageBreak(),
    ]

    # ---------- 5. debug walk -----------------------------------------------
    story += [
        p("5. Suggested debugging walk", H1),
        *bullets([
            f"Bring the stack up: "
            f"{c('docker-compose up eugene_neo4j eugene_ws')}. Confirm "
            f"{c('NEO4J_URI')}, {c('NEO4J_USERNAME')}, {c('NEO4J_PASSWORD')} "
            f"are set; module-import DI at "
            f"{c('label_router.py:27')} will fail loudly otherwise.",
            f"Issue a request: "
            f"{c('curl -s &#39;http://localhost:8080/labels/drug?page=1&amp;page_size=5&#39; | jq .')} &mdash; "
            f"expect a 200 with five rows. Now try "
            f"{c('/labels/patent')} &mdash; expect a 422 because "
            f"{c('patent')} is not in the {c('Label')} enum.",
            f"Set a breakpoint at {c('label_router.py:61')} "
            f"({c('dataframe = foundational_node_adapter.find_by_label(...)')}). "
            f"Inspect {c('label.value')} (the raw string) and confirm "
            "page/page_size came through as ints.",
            f"Step into {c('neo4j_foundational_node_adapter.py:130')} "
            f"({c('_build_find_by_label')}). The fully interpolated Cypher is "
            f"logged at DEBUG &mdash; set {c('LOG_LEVEL=DEBUG')} to see it. "
            "Copy/paste into Neo4j Browser to verify the row count matches "
            f"{c('count')} in the response.",
            f"Force the empty path: request "
            f"{c('/labels/exposure?page=10000&amp;page_size=50')}. Confirm a "
            f"200 with {c('count=0')} &mdash; the response is "
            f"{c('NameAndIdListResponse(count=0, results=[])')} from the "
            f"mapper&#39;s null-DataFrame guard at "
            f"{c('response_util.py:27-28')}.",
            f"Cross-check pagination: hit "
            f"{c('/labels/drug?page=1&amp;page_size=50')} then "
            f"{c('/labels/drug?page=2&amp;page_size=50')} and verify the "
            f"first id of page 2 is alphabetically just after the last id of "
            f"page 1. If they overlap or skip, look for non-deterministic "
            f"{c('node_name')} values (whitespace, casing).",
        ]),
        PageBreak(),
    ]

    # ---------- 6. reference index ------------------------------------------
    story += [
        p("6. Reference index (file paths)", H1),
        code(
            "Router & request models\n"
            "  src/foundation/router/label_router.py\n"
            "  src/foundation/router/model/label.py\n"
            "  src/foundation/router/validate_util.py            (validate_label, str_to_label_enum)\n"
            "\n"
            "Wiring\n"
            "  src/eugene_ws.py                                  (lines 35, 62, 77-78)\n"
            "  src/foundation/conf/conf.py                       (lines 95-96, 109-114)\n"
            "\n"
            "Adapter (Cypher generation + execution)\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_adapter.py\n"
            "  src/foundation/infra/db/util/pagination.py\n"
            "  src/graph/util/util.py                            (ensure_connection)\n"
            "  src/graph/util/node_util.py                       (normalize_node_label)\n"
            "\n"
            "Mapper & response models\n"
            "  src/foundation/router/response_util.py            (to_id_list_response)\n"
            "  src/foundation/router/model/name_id_list_response.py\n"
            "  src/foundation/router/model/name_and_id.py\n"
            "\n"
            "Schema enums\n"
            "  src/foundation/model/foundational_node_enum.py    (label tuples)\n"
            "\n"
            "Related routes that share the validator / adapter\n"
            "  src/foundation/router/count_router.py             (grand totals per label)\n"
            "  src/foundation/router/node_id_lookup_router.py\n"
            "  src/foundation/router/facet_router.py\n"
            "\n"
            "Seed data (where the listed nodes come from)\n"
            "  bin/seed/csl_behring_assets.cypher\n"
            "  bin/seed/biogen_assets.cypher\n"
            "  src/foundation/load/*\n"
        ),
        p("Key takeaways", H2),
        *bullets([
            f"{c('GET /labels/{{label}}')} is the thinnest read path in "
            "Eugene: enum-validated path, paginated label scan, two-column "
            "DataFrame, typed list response.",
            f"The {c('Label')} enum is a deliberate nine-value subset of "
            f"{c('FoundationalNodeEnum')}. Patents, sponsors, organizations "
            "and clinical trials are <b>not</b> listable through this route.",
            f"All Cypher is string-interpolated &mdash; safe here because the "
            f"label is enum-bounded and pagination args are typed {c('int')}. "
            "Don't copy this pattern into routes that accept free-form input.",
            f"The route never returns 404 and never filters {c('is_hidden')}. "
            f"For pagination math, pair with {c('GET /count/{{label}}')}; "
            "this route does not return the grand total.",
        ]),
    ]

    return story
