"""Per-route flow guide for Eugene's organization_search_router.

Endpoints:
    GET /organizations/{organization_name}?page=&page_size=
    GET /organizations/assets/{organization_id}?page=&page_size=

Walks an engineer from the FastAPI boundary, through DI wiring and the
two Cypher queries, into the JSON shape returned to the caller. Every
reference is in path/to/file.py:line form so it can be opened directly
in an IDE.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_ORGANIZATION_SEARCH_FLOW_GUIDE.pdf"
TITLE = "Eugene Organization Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---------- cover -------------------------------------------------------
    story += [
        h.p("Eugene Organization Search &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP boundary &rarr; regex sanitiser &rarr; "
            "Neo4j organization scan &rarr; clinical-trial fan-out &rarr; "
            "GenericListResponse",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers onboarding to the Eugene biomedical knowledge graph who "
            f"need a single, file-referenced trace of the {h.c('/organizations/*')} "
            f"endpoints. The route exposes two reads: a wildcard search over "
            f"{h.c(':Organization')} nodes and a fan-out from one organization "
            f"through its {h.c(':ClinicalTrial')} edges to the drugs / diseases "
            "the org is associated with. Every reference uses the form "
            f"{h.c('path/to/file.py:line')} so you can open it directly in your "
            "IDE and step through with a debugger.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('GET /organizations/{{organization_name}}?page=&amp;page_size=')} "
            f"&mdash; wildcard ({h.c('*')}, {h.c('?')}) search over "
            f"{h.c('organization_canonical_name')}. Returns "
            f"{h.c('[{org_id, org_name, org_type}, ...]')}.",
            f"{h.c('GET /organizations/assets/{{organization_id}}?page=&amp;page_size=')} "
            f"&mdash; given an org id (e.g. {h.c('H003644')}), walks "
            f"{h.c(':Organization)-[*]-(:ClinicalTrial)-[*]-(:drug|:disease)')} "
            "and returns one row per trial / asset edge.",
        ]),
        h.p("Sample calls"),
        h.code(
            "curl -s 'http://localhost:8080/organizations/csl*?page=1&page_size=10' | jq .\n"
            "curl -s 'http://localhost:8080/organizations/assets/H003644?page=1&page_size=25' | jq ."
        ),
        h.p(
            f"Declared in {h.c('src/organization/router/organization_search_router.py:23-101')}. "
            f"Router prefix {h.c('/organizations')}, tag {h.c('organizations')}.",
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Sections follow the request path top-down: schema &rarr; HTTP &rarr; "
            "adapter / Cypher &rarr; mapper &rarr; ETL provenance &rarr; debug "
            "walk &rarr; reference index.",
            f"Section 0 untangles the two organization enum members "
            f"({h.c('ORGANIZATION_V2')} vs. {h.c('ORGANIZATION_V3')}) and the "
            f"separate {h.c('FoundationalNodeEnum.ORGANIZATION')} tuple.",
            "Section 5 lists a concrete debugging walk (curl, breakpoints, "
            "Cypher verification).",
            f"Note: pagination uses 1-based {h.c('page')} (gt=0) and "
            f"{h.c('page_size')} (gt=0, le=500); arithmetic is handled by the "
            f"shared {h.c('Pagination')} helper.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 0. schema ---------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            f"The organization subgraph is anchored by a single Neo4j label, "
            f"{h.c(':Organization')} (capital O). Three enums collaborate to "
            "produce that label string in Cypher &mdash; this is the one place "
            "where Eugene's mixed-case label conventions matter."
        ),
        h.p("Node label &mdash; OrganizationNodeEnum", h.H2),
        h.p(f"{h.c('src/organization/model/organization_node_enum.py')}", h.PATH),
        h.code(
            "class OrganizationNodeEnum(Enum):\n"
            "    UNKNOWN                = 0,  \"unknown\"\n"
            "    COMPANY                = 1,  \"company\"\n"
            "    UNIVERSITY             = 2,  \"university\"\n"
            "    NONPROFIT              = 3,  \"nonprofit\"\n"
            "    FOUNDATION             = 4,  \"foundation\"\n"
            "    GOVERNMENT             = 5,  \"government\"\n"
            "    ORGANIZATION           = 6,  \"organization\"\n"
            "    HOSPITAL               = 7,  \"hospital\"\n"
            "    ORGANIZATION_V2        = 8,  \"organization\"\n"
            "    ORGANIZATION_V3        = 8,  \"Organization\"   # &lt;-- used in Cypher\n"
            "    SUBSIDIARY             = 10, \"subsidiary\"\n"
            "    ACQUISITION            = 11, \"acquisition\"\n"
            "    MERGER                 = 12, \"merger\"\n"
            "    DEMERGER               = 13, \"demerger\"\n"
            "    SPELLING_VARIATION     = 14, \"organization_spelling_variation\"\n"
        ),
        *h.bullets([
            f"The adapter only ever reads {h.c('ORGANIZATION_V3.value[1]')} &mdash; "
            f"i.e. the literal label string {h.c('Organization')} (capital O). "
            f"All the lowercased members are historical / for ETL-side use.",
            f"{h.c('ORGANIZATION_V2')} and {h.c('ORGANIZATION_V3')} share the "
            f"same id ({h.c('8')}) but differ in label case &mdash; only V3 "
            "matches what is actually written into Neo4j by the seed scripts.",
            f"The aliases / spelling variations enum members are write-side only; "
            "the search adapter does not traverse them.",
        ]),
        h.p("FoundationalNodeEnum.ORGANIZATION", h.H2),
        h.p(f"{h.c('src/foundation/model/foundational_node_enum.py:32')}", h.PATH),
        h.code(
            "class FoundationalNodeEnum(Enum):\n"
            "    ...\n"
            "    CLINICAL_TRIAL = 4,  \"ClinicalTrial\"\n"
            "    DISEASE        = 7,  \"disease\"\n"
            "    DRUG           = 8,  \"drug\"\n"
            "    ...\n"
            "    ORGANIZATION   = 32, \"Organization\"\n"
        ),
        h.p(
            f"This is the foundation-side mirror of "
            f"{h.c('OrganizationNodeEnum.ORGANIZATION_V3')} &mdash; same label "
            f"string ({h.c('Organization')}), independent id space ({h.c('32')}). "
            f"It is deliberately <b>not</b> exposed through the public "
            f"{h.c('Label')} enum, so the generic "
            f"{h.c('/labels/{{label}}')} route cannot list organizations; this "
            "router is the only HTTP path that can.",
        ),
        h.p("Relationship shape", h.H2),
        h.code(
            "(:`Organization` { org_id, organization_canonical_name, organization_type, ... })\n"
            "(:`Organization`)-[*]-(:`ClinicalTrial` { nct_id, ... })\n"
            "(:`ClinicalTrial`)-[*]-(:`drug` | :`disease` { node_name, ... })"
        ),
        *h.bullets([
            f"There is no fixed relationship type wired into the router &mdash; "
            f"the assets query uses an unnamed {h.c('-[rel1]-')} and reports "
            f"{h.c('type(rel1)')} back in the response (see Section 2). The "
            "actual edge types depend on what the ClinicalTrials.gov ingest "
            "wrote (sponsor, collaborator, intervention, condition, etc.).",
            f"The organization side has a sibling enum "
            f"{h.c('OrganizationRelationshipEnum.HAS_ALIAS')} "
            f"({h.c('src/organization/model/organization_relationship_enum.py')}) "
            "but it is reserved for the alias subgraph &mdash; the search "
            "router does not use it.",
            f"Like the rest of Eugene there are no Neo4j {h.c('CREATE CONSTRAINT')} "
            f"statements &mdash; idempotency comes from {h.c('MERGE')} on "
            f"{h.c('org_id')} at write time.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 1. HTTP entry -----------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:53')} &mdash; "
            f"{h.c('from organization.router import organization_search_router')}. "
            f"{h.c('src/eugene_ws.py:75')} appends "
            f"{h.c('organization_search_router')} to the {h.c('routers')} list, "
            f"and the boot loop later calls "
            f"{h.c('app.include_router(router.router)')}.",
        ),
        h.p("Router file", h.H2),
        h.p(f"{h.c('src/organization/router/organization_search_router.py')}", h.PATH),
        h.p("Imports (lines 1-11)"),
        h.code(
            "import logging\n"
            "from typing import Annotated\n"
            "\n"
            "from fastapi import APIRouter, Path, Query\n"
            "from pydantic import AfterValidator\n"
            "\n"
            "from foundation.router.validate_util import (\n"
            "    validate_id,\n"
            ")\n"
            "from foundation.router.model.generic_list_response import GenericListResponse\n"
            "from organization.conf.search_conf import organization_search_adapter\n"
        ),
        h.p("Router declaration (lines 15-18)"),
        h.code(
            "router = APIRouter(\n"
            "    prefix=\"/organizations\",\n"
            "    tags=[\"organizations\"],\n"
            ")\n"
        ),
        h.p("Module-load dependency injection (line 20)", h.H2),
        h.code("org_search_adapter = organization_search_adapter()"),
        h.p(
            f"Eugene's manual DI pattern: a module-scope call constructs the "
            f"adapter once at import-time. The factory lives in "
            f"{h.c('src/organization/conf/search_conf.py:27-32')}:",
        ),
        h.code(
            "def _neo4j_driver() -> Driver:\n"
            "    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()\n"
            "\n"
            "def _organization_search_adapter(driver: Driver) -> Neo4jOrganizationSearchAdapter:\n"
            "    return Neo4jOrganizationSearchAdapter(driver=driver)\n"
            "\n"
            "def organization_search_adapter() -> Neo4jOrganizationSearchAdapter:\n"
            "    return _organization_search_adapter(driver=_neo4j_driver())\n"
        ),
        h.p(
            f"The driver is constructed from "
            f"{h.c('GraphDbConnectionFactory.remote_neo4j_instance_from_env()')} &mdash; "
            f"configured from {h.c('NEO4J_URI')}, {h.c('NEO4J_USERNAME')}, "
            f"{h.c('NEO4J_PASSWORD')}. No framework, no decorators &mdash; module "
            "import order is the DI graph. If env vars are missing the router "
            "module fails to import and the whole service refuses to start.",
        ),
        h.p("Endpoint 1 &mdash; name search (lines 23-60)", h.H2),
        h.code(
            "@router.get(\n"
            "    \"/{organization_name}\",\n"
            "    response_model=GenericListResponse,\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def list_organization_names(\n"
            "    organization_name: Annotated[\n"
            "        str,\n"
            "        Path(\n"
            "            description=\"Limited regex ... Accepts ['*' or '?'] only,\"\n"
            "                        \" others are escaped\",\n"
            "            max_length=256,\n"
            "            min_length=0,\n"
            "            example=\"csl*\",\n"
            "        ),\n"
            "    ],\n"
            "    page: Annotated[int, Query(..., example=1, gt=0)],\n"
            "    page_size: Annotated[int, Query(..., example=10, gt=0, le=500)],\n"
            "):\n"
            "    results = org_search_adapter.find_companies_by_name_pattern(\n"
            "        name_pattern=organization_name, page=page, page_size=page_size\n"
            "    )\n"
            "    count = len(results) if results else 0\n"
            "    return GenericListResponse(count=count, results=results)\n"
        ),
        h.p("Endpoint 2 &mdash; asset fan-out (lines 63-101)", h.H2),
        h.code(
            "@router.get(\n"
            "    \"/assets/{organization_id}\",\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def list_organization_assets(\n"
            "    organization_id: Annotated[\n"
            "        str,\n"
            "        Path(..., max_length=256, min_length=0, example=\"H003644\"),\n"
            "        AfterValidator(validate_id),\n"
            "    ],\n"
            "    page: Annotated[int, Query(..., example=1, gt=0)],\n"
            "    page_size: Annotated[int, Query(..., example=10, gt=0, le=500)],\n"
            "):\n"
            "    results = org_search_adapter.find_assets_by_org_id(\n"
            "        org_id=organization_id, page=page, page_size=page_size\n"
            "    )\n"
            "    count = len(results) if results else 0\n"
            "    return GenericListResponse(count=count, results=results)\n"
        ),
        h.p("Validation layers", h.H2),
        *h.bullets([
            f"<b>Path bounds</b> &mdash; both endpoints cap path params at "
            f"{h.c('max_length=256, min_length=0')}. Note that {h.c('min_length=0')} "
            f"means an empty string is accepted at the type level &mdash; the "
            f"route matcher requires <i>some</i> path segment, but a "
            "single-character or whitespace-only segment will pass.",
            f"<b>Query bounds</b> &mdash; {h.c('page &gt; 0')} and "
            f"{h.c('0 &lt; page_size &lt;= 500')}. FastAPI returns 422 for "
            f"out-of-range values. {h.c('page_size')} is generous (500) compared "
            f"to other Eugene routes ({h.c('le=50')}) &mdash; reflects the lower "
            "cardinality of organizations vs. genes/drugs.",
            f"<b>AfterValidator(validate_id)</b> &mdash; only the assets "
            f"endpoint runs {h.c('validate_id')} "
            f"({h.c('src/foundation/router/validate_util.py:98-104')}), which "
            f"rejects ids containing {h.c('%')}, {h.c('$')}, {h.c(';')}, "
            f"{h.c(':')}, {h.c('^')}, or {h.c('*')}. The name-search endpoint "
            "deliberately allows * (it's a wildcard).",
            f"<b>No regex validation at the FastAPI layer</b> for "
            f"{h.c('organization_name')} &mdash; sanitisation happens in the "
            "adapter via sanitize_regex_pattern (Section 2).",
        ]),
        h.p("Set your first breakpoint", h.H2),
        h.p(
            f"At {h.c('organization_search_router.py:56')} (the "
            f"{h.c('org_search_adapter.find_companies_by_name_pattern(...)')} call) "
            f"or {h.c('organization_search_router.py:96')} (the assets call). "
            "Inspect the raw path param, page, and page_size before the adapter "
            "transforms anything.",
        ),
        h.PageBreak(),
    ]

    # ---------- 2. adapter / Cypher -----------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the two Cyphers", h.H1),
        h.p(f"{h.c('src/organization/infra/db/neo4j_organization_search_adapter.py')}", h.PATH),
        h.p("Class &amp; entry points (lines 16-23)", h.H2),
        h.code(
            "class Neo4jOrganizationSearchAdapter:\n"
            "    def __init__(self, driver: Driver, database: str = \"neo4j\"):\n"
            "        self.driver = driver\n"
            "        self.database = database\n"
        ),
        h.p(
            f"Two public methods, one per endpoint: "
            f"{h.c('find_companies_by_name_pattern')} (line 25) and "
            f"{h.c('find_assets_by_org_id')} (line 93). Both call "
            f"{h.c('ensure_connection(self.driver)')} "
            f"({h.c('src/graph/util/util.py')}) before opening a session &mdash; "
            "defends against stale connections after a Neo4j restart.",
        ),
        h.p("Pattern sanitisation (line 60)", h.H2),
        h.p(f"{h.c('src/util/regex_validation.py')}", h.PATH),
        h.code(
            "def sanitize_regex_pattern(pattern: str) -> str:\n"
            "    \"\"\"Escapes all regex special characters except * and ?\n"
            "    for basic wildcard support.\"\"\"\n"
            "    escaped = re.escape(pattern)\n"
            "    # Allow * and ? as wildcards by converting them back\n"
            "    # \\* becomes .* (match any characters)\n"
            "    # \\? becomes . (match single character)\n"
            "    escaped = escaped.replace(r\"\\*\", \".*\").replace(r\"\\?\", \".\")\n"
            "    return escaped\n"
        ),
        *h.bullets([
            f"Inputs like {h.c('csl*')} become {h.c('csl.*')}; "
            f"{h.c('a?bott')} becomes {h.c('a.bott')}.",
            f"All other regex metacharacters ({h.c('.')}, {h.c('+')}, "
            f"{h.c('(')}, {h.c('|')}, {h.c('$')}, &hellip;) are passed through "
            f"{h.c('re.escape')} so a malicious payload like "
            f"{h.c('.*(.*)+.*$')} cannot trigger a catastrophic backtrack on "
            "the Neo4j regex engine.",
            f"The Neo4j adapter then prepends {h.c('(?i)')} to make the regex "
            "case-insensitive &mdash; the canonical name is stored mixed-case "
            "(e.g. \"CSL Behring\") but users search in lowercase.",
        ]),
        h.p("Cypher 1 &mdash; name pattern search (lines 56-91)", h.H2),
        h.code(
            "MATCH (o:`Organization`)\n"
            "WHERE o.organization_canonical_name =~ $pattern\n"
            "RETURN o.org_id                       as org_id,\n"
            "       o.organization_canonical_name  as org_name,\n"
            "       o.organization_type            as org_type\n"
            "SKIP  $skip\n"
            "LIMIT $limit\n"
            "\n"
            "# params:\n"
            "#   pattern = \"(?i)\" + sanitize_regex_pattern(organization_name)\n"
            "#   skip    = (page - 1) * page_size\n"
            "#   limit   = page_size\n"
        ),
        *h.bullets([
            f"Label {h.c(':`Organization`')} is interpolated from "
            f"{h.c('OrganizationNodeEnum.ORGANIZATION_V3.value[1]')} "
            f"(line 70). The {h.c('%s')} substitution is safe because the "
            "enum is hard-coded &mdash; no user input reaches the label slot.",
            f"{h.c('pattern')}, {h.c('skip')}, and {h.c('limit')} are bound "
            f"parameters (line 73): the only string-interpolated value is the "
            "label itself. Compare to the label/count routers, which "
            "interpolate everything.",
            f"<b>No ORDER BY</b> &mdash; pagination is by Neo4j's default scan "
            f"order. Two requests at the same {h.c('(page, page_size)')} will "
            f"return the same rows in the same order in practice, but the "
            f"Cypher does not formally guarantee it. If you see pagination "
            f"weirdness here, add {h.c('ORDER BY org_name')}.",
            f"{h.c('is_hidden')} is <b>not</b> checked &mdash; soft-deleted "
            "orgs (if any) are still returned.",
        ]),
        h.p("Cypher 2 &mdash; assets fan-out (lines 120-141)", h.H2),
        h.code(
            "MATCH (start:`Organization`)-[rel1]-(ct:`ClinicalTrial`)-[rel2]-(end:`disease`|`drug`)\n"
            "WHERE start.org_id = $org_id\n"
            "RETURN start.organization_type             as org_type,\n"
            "       start.organization_canonical_name   as org_name,\n"
            "       type(rel1)                          as org_to_ct_rel,\n"
            "       ct.nct_id                           as trial,\n"
            "       type(rel2)                          as ct_to_asset_rel,\n"
            "       labels(end)                         as entity_labels,\n"
            "       end.node_name                       as entity_name\n"
            "ORDER BY start.organization_canonical_name, trial desc\n"
            "SKIP  $skip\n"
            "LIMIT $limit\n"
            "\n"
            "# params: org_id, skip, limit\n"
        ),
        *h.bullets([
            f"Three labels interpolated: "
            f"{h.c('OrganizationNodeEnum.ORGANIZATION_V3.value[1]')} = "
            f"{h.c('Organization')}, "
            f"{h.c('FoundationalNodeEnum.CLINICAL_TRIAL.value[1]')} = "
            f"{h.c('ClinicalTrial')}, and the "
            f"{h.c('_join_labels([DISEASE, DRUG])')} helper produces "
            f"{h.c('`disease`|`drug`')} (lines 169-174).",
            f"{h.c('-[rel1]-')} / {h.c('-[rel2]-')} are <b>unnamed</b> &mdash; "
            f"any edge type between {h.c(':Organization')} and "
            f"{h.c(':ClinicalTrial')} (and between trial and asset) is walked. "
            f"The actual type is reported back via {h.c('type(rel1)')} so the "
            "caller can introspect it.",
            f"{h.c('end.node_name')} relies on every drug/disease node carrying "
            f"a {h.c('node_name')} property &mdash; same contract as the "
            "drug-alias route. A missing node_name surfaces as null in the "
            "response (not a 500 here because the response model is untyped).",
            f"<b>TODO marker</b> at line 123: the docstring explicitly notes "
            "patents and pubmed docs are not yet walked. If you extend this, "
            f"add labels to {h.c('_join_labels(...)')} on line 135.",
            f"{h.c('ORDER BY ... trial desc')} stabilises pagination &mdash; "
            "rows are stable across requests at the same page.",
        ]),
        h.p("Pagination helper", h.H2),
        h.p(f"{h.c('src/foundation/infra/db/util/pagination.py')}", h.PATH),
        h.code(
            "(limit, skip) = Pagination.calculate_limit_and_offset(page, page_size)\n"
            "# page=1, page_size=10  -> limit=10, skip=0\n"
            "# page=3, page_size=25  -> limit=25, skip=50\n"
        ),
        h.PageBreak(),
    ]

    # ---------- 3. mapper / response model ----------------------------------
    story += [
        h.p("3. Mapper &amp; response model", h.H1),
        h.p(
            f"There is no separate mapper class for this route &mdash; the "
            f"adapter already produces plain Python {h.c('dict')}s "
            f"(lines 79-86 for names, lines 151-160 for assets). The router "
            f"wraps them in {h.c('GenericListResponse')} and returns.",
        ),
        h.p("Response model", h.H2),
        h.p(f"{h.c('src/foundation/router/model/generic_list_response.py')}", h.PATH),
        h.code(
            "from pydantic import BaseModel\n"
            "\n"
            "class GenericListResponse(BaseModel):\n"
            "    count:   int\n"
            "    results: list[dict]\n"
        ),
        *h.bullets([
            f"Deliberately untyped: {h.c('results: list[dict]')}. This is the "
            f"same envelope used by patent / pubmed search; each row's keys "
            "vary per endpoint.",
            f"{h.c('count')} is the length of the returned page, <b>not</b> the "
            "grand total. There is no dedicated count endpoint for "
            "organizations today &mdash; pagination math is the caller's "
            "responsibility.",
            f"{h.c('response_model=GenericListResponse')} is declared only on "
            f"the name-search endpoint (line 25). The assets endpoint uses "
            f"{h.c('response_model_exclude_none=True')} without an explicit "
            "model &mdash; FastAPI infers from the returned object at runtime.",
            f"Empty results &rarr; {h.c('GenericListResponse(count=0, results=[])')}; "
            "the route never returns 404.",
        ]),
        h.p("Row shape &mdash; name search", h.H2),
        h.code(
            "{\n"
            "  \"org_id\":   \"H003644\",\n"
            "  \"org_name\": \"CSL Behring\",\n"
            "  \"org_type\": \"COMPANY\"\n"
            "}\n"
        ),
        h.p("Row shape &mdash; assets fan-out", h.H2),
        h.code(
            "{\n"
            "  \"org_type\":        \"COMPANY\",\n"
            "  \"org_name\":        \"CSL Behring\",\n"
            "  \"org_to_ct_rel\":   \"sponsor\",\n"
            "  \"trial\":           \"NCT04354805\",\n"
            "  \"ct_to_asset_rel\": \"has_intervention\",\n"
            "  \"entity_labels\":   \"drug\",\n"
            "  \"entity_name\":     \"garadacimab\"\n"
            "}\n"
        ),
        h.p(
            f"Note {h.c('entity_labels')} is a comma-joined string, not an "
            f"array &mdash; the adapter joins the {h.c('labels(end)')} list "
            f"with {h.c('&quot;, &quot;')} (line 158). A drug-only node is "
            f"{h.c('&quot;drug&quot;')}; a node tagged both "
            f"{h.c(':drug')} and {h.c(':approved_drug')} would appear as "
            f"{h.c('&quot;drug, approved_drug&quot;')}.",
        ),
        h.p("Example responses", h.H2),
        h.code(
            "GET /organizations/csl*?page=1&page_size=3\n"
            "{\n"
            "  \"count\": 3,\n"
            "  \"results\": [\n"
            "    {\"org_id\": \"H003644\", \"org_name\": \"CSL Behring\",     \"org_type\": \"COMPANY\"},\n"
            "    {\"org_id\": \"H001288\", \"org_name\": \"CSL Limited\",     \"org_type\": \"COMPANY\"},\n"
            "    {\"org_id\": \"H009922\", \"org_name\": \"CSL Plasma Inc.\", \"org_type\": \"COMPANY\"}\n"
            "  ]\n"
            "}\n"
            "\n"
            "GET /organizations/assets/H003644?page=1&page_size=2\n"
            "{\n"
            "  \"count\": 2,\n"
            "  \"results\": [\n"
            "    {\"org_type\": \"COMPANY\", \"org_name\": \"CSL Behring\",\n"
            "     \"org_to_ct_rel\":   \"sponsor\",\n"
            "     \"trial\":           \"NCT04354805\",\n"
            "     \"ct_to_asset_rel\": \"has_condition\",\n"
            "     \"entity_labels\":   \"disease\",\n"
            "     \"entity_name\":     \"hereditary angioedema\"},\n"
            "    {\"org_type\": \"COMPANY\", \"org_name\": \"CSL Behring\",\n"
            "     \"org_to_ct_rel\":   \"sponsor\",\n"
            "     \"trial\":           \"NCT04354805\",\n"
            "     \"ct_to_asset_rel\": \"has_intervention\",\n"
            "     \"entity_labels\":   \"drug\",\n"
            "     \"entity_name\":     \"garadacimab\"}\n"
            "  ]\n"
            "}\n"
        ),
        h.PageBreak(),
    ]

    # ---------- 4. ETL ------------------------------------------------------
    story += [
        h.p("4. ETL &mdash; where the :Organization nodes come from", h.H1),
        h.p(
            f"The search route is read-only. The {h.c(':Organization')} nodes "
            f"it scans are produced by a separate resolution pipeline driven "
            "from JSON checkpoint files."
        ),
        h.p("CLI entry point", h.H2),
        h.p(f"{h.c('src/ingest_organizations.py')}", h.PATH),
        h.code(
            "def main():\n"
            "    load_dotenv()\n"
            "    args = build_args()\n"
            "    checkpoint_dir = Path(args.checkpoint_basedir)\n"
            "    _ingest_resolution_checkpoint_dir(checkpoint_dir=checkpoint_dir)\n"
            "\n"
            "def _ingest_resolution_checkpoint_dir(checkpoint_dir: Path) -> None:\n"
            "    orchestrator = organization_ingest_orchestrator()\n"
            "    ids = orchestrator.ingest(checkpoint_dir=checkpoint_dir)\n"
            "    logger.info(f\"Loaded and ingested {len(ids)} unique organization(s)\")\n"
        ),
        h.p(
            f"Default checkpoint dir is "
            f"{h.c('./output/checkpoint/organization')} (a tree of JSON files "
            f"produced by the upstream resolver under "
            f"{h.c('src/organization/analyzer/')} / "
            f"{h.c('src/organization/provider/')}). Override with "
            f"{h.c('--checkpoint-basedir')}.",
        ),
        h.p("Orchestrator", h.H2),
        h.p(f"{h.c('src/organization/provider/organization_ingest_orchestrator.py')}", h.PATH),
        h.code(
            "class OrganizationIngestOrchestrator:\n"
            "    def ingest(self, checkpoint_dir: Path | None) -> list[str]:\n"
            "        resolutions = self._load_resolution_checkpoint_dir(checkpoint_dir)\n"
            "        merged = self.organization_resolution_multipass_merge_orchestrator.merge(\n"
            "            resolutions=resolutions\n"
            "        )\n"
            "        self._assign_ids(resolutions=merged)\n"
            "        # todo: ingest into neo4j\n"
            "        # return self.ingest_organizations(organizations_resolutions=merged)\n"
            "        return [el.official_name for el in merged]\n"
        ),
        *h.bullets([
            f"<b>Heads-up</b>: the Neo4j upsert call is commented out (line 52). "
            "Today the CLI <i>resolves &amp; merges</i> organization records "
            "and assigns ids, but does <b>not</b> actually write to the graph. "
            f"The {h.c(':Organization')} nodes the search route reads today "
            "were seeded by other paths (Cypher seed scripts under "
            f"{h.c('bin/seed/')} and the ClinicalTrials.gov ingest, which "
            "creates org nodes as a side-effect of trial sponsor/collaborator "
            "edges).",
            f"When the TODO is unblocked, the writer is "
            f"{h.c('Neo4jOrganizationAdapter.upsert_organization_resolutions')} "
            f"({h.c('src/organization/infra/db/neo4j_organization_adapter.py')}). "
            "It is wired but not invoked.",
            f"The resolution loader is "
            f"{h.c('OrganizationResolutionLoader')} "
            f"({h.c('src/organization/load/organization_resolution_loader.py')}); "
            f"the data class is {h.c('OrganizationResolution')} "
            f"({h.c('src/organization/model/organization_resolution.py')}) and "
            f"holds {h.c('official_name')}, {h.c('parent')}, "
            f"{h.c('subsidiaries')}, {h.c('acquisitions')}, "
            f"{h.c('spelling_variations')}, {h.c('mergers')}, "
            f"{h.c('demergers')}, {h.c('organization_type')}, "
            f"{h.c('query_term')}, {h.c('id')}.",
        ]),
        h.p("Property contract the search Cypher depends on", h.H2),
        *h.bullets([
            f"Every {h.c(':Organization')} node must carry "
            f"{h.c('org_id')}, {h.c('organization_canonical_name')}, "
            f"{h.c('organization_type')}. The first is the bound id in "
            f"the assets endpoint; the second is the {h.c('=~')} target in "
            "the name endpoint; the third populates org_type in the response.",
            f"No {h.c('CREATE CONSTRAINT')} statements &mdash; uniqueness "
            f"comes from {h.c('MERGE')} on {h.c('org_id')} at write time. "
            "Two write paths with disagreeing ids will produce duplicate orgs "
            "with the same canonical name (visible in the search response).",
            f"For asset fan-out: nodes must additionally have edges to "
            f"{h.c(':ClinicalTrial')} nodes (any rel type) and those trials "
            f"must in turn link to {h.c(':drug')} / {h.c(':disease')} "
            f"nodes with {h.c('node_name')} set.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 5. debug walk ----------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Bring the stack up: "
            f"{h.c('docker-compose up eugene_neo4j eugene_ws')}. Confirm "
            f"{h.c('NEO4J_URI')}, {h.c('NEO4J_USERNAME')}, {h.c('NEO4J_PASSWORD')} "
            f"are set; module-import DI at "
            f"{h.c('organization_search_router.py:20')} will fail loudly otherwise.",
            f"Smoke test: "
            f"{h.c('curl -s &#39;http://localhost:8080/organizations/csl*?page=1&amp;page_size=5&#39; | jq .')}. "
            f"Expect a 200 with up to five CSL-* orgs. Then "
            f"{h.c('/organizations/assets/H003644?page=1&amp;page_size=10')} "
            "for the fan-out.",
            f"Set a breakpoint at "
            f"{h.c('neo4j_organization_search_adapter.py:60')} "
            f"({h.c('safe_pattern = sanitize_regex_pattern(name_pattern)')}). "
            f"Try inputs like {h.c('csl*')}, {h.c('?bbott')}, "
            f"{h.c('.*(.*)+$')} &mdash; the first two should yield meaningful "
            f"Neo4j regexes ({h.c('csl.*')}, {h.c('.bbott')}), the third "
            "should be fully escaped and match nothing.",
            f"Step into {h.c('neo4j_organization_search_adapter.py:78')} and "
            f"watch {h.c('tx.run(query, params)')} execute. The query plus "
            f"params is logged at INFO; copy/paste both into Neo4j Browser "
            "to verify the row count matches the response's count.",
            f"Force the empty path: request "
            f"{h.c('/organizations/zzzzzzzz?page=1&amp;page_size=10')}. Expect "
            f"a 200 with {h.c('count=0')} &mdash; no 404, no exception.",
            f"For the assets endpoint, breakpoint at "
            f"{h.c('neo4j_organization_search_adapter.py:150')} and inspect "
            f"{h.c('record[&quot;entity_labels&quot;]')} before the "
            f"{h.c('&quot;, &quot;.join(...)')} call &mdash; the raw value is "
            "a Python list; remember the response collapses it to a string.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 6. reference index -----------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Router\n"
            "  src/organization/router/organization_search_router.py\n"
            "  src/foundation/router/validate_util.py            (validate_id)\n"
            "  src/foundation/router/model/generic_list_response.py\n"
            "\n"
            "Wiring\n"
            "  src/eugene_ws.py                                  (lines 53, 75)\n"
            "  src/organization/conf/search_conf.py              (factories L15-32)\n"
            "  src/graph/infra/db/graph_db_connection_factory.py\n"
            "\n"
            "Adapter (Cypher generation + execution)\n"
            "  src/organization/infra/db/neo4j_organization_search_adapter.py\n"
            "  src/util/regex_validation.py                      (sanitize_regex_pattern)\n"
            "  src/foundation/infra/db/util/pagination.py        (Pagination)\n"
            "  src/graph/util/util.py                            (ensure_connection)\n"
            "\n"
            "Schema enums\n"
            "  src/organization/model/organization_node_enum.py  (ORGANIZATION_V3 -> 'Organization')\n"
            "  src/organization/model/organization_relationship_enum.py\n"
            "  src/foundation/model/foundational_node_enum.py    (CLINICAL_TRIAL, DRUG, DISEASE, ORGANIZATION)\n"
            "\n"
            "ETL (write side -- currently TODO into Neo4j)\n"
            "  src/ingest_organizations.py\n"
            "  src/organization/conf/conf.py\n"
            "  src/organization/provider/organization_ingest_orchestrator.py\n"
            "  src/organization/provider/organization_resolution_multipass_merge_orchestrator.py\n"
            "  src/organization/provider/organization_id_generator.py\n"
            "  src/organization/load/organization_resolution_loader.py\n"
            "  src/organization/mapper/organization_resolution_mapper.py\n"
            "  src/organization/model/organization_resolution.py\n"
            "  src/organization/model/canonical_organization_key.py\n"
            "  src/organization/infra/db/neo4j_organization_adapter.py    (writer, not yet called)\n"
            "\n"
            "Sibling read route\n"
            "  src/organization/router/organization_alias_search_router.py\n"
        ),
        h.p("Key takeaways", h.H2),
        *h.bullets([
            f"{h.c('/organizations/{{organization_name}}')} accepts only "
            f"{h.c('*')} and {h.c('?')} wildcards &mdash; everything else is "
            f"regex-escaped by {h.c('sanitize_regex_pattern')} before reaching "
            "Neo4j. Catastrophic-backtrack payloads are neutralised.",
            f"The label string in Cypher is hard-coded via "
            f"{h.c('OrganizationNodeEnum.ORGANIZATION_V3.value[1]')} = "
            f"{h.c('Organization')} (capital O). Do not confuse it with the "
            f"lowercased {h.c('ORGANIZATION_V2')} or with "
            f"{h.c('FoundationalNodeEnum.ORGANIZATION')} (same string, "
            "different enum, id 32).",
            f"The assets endpoint walks any relationship type between "
            f"{h.c(':Organization')}, {h.c(':ClinicalTrial')}, and "
            f"{h.c(':drug')} / {h.c(':disease')} &mdash; the edge type is "
            f"reported back via {h.c('type(rel1)')}, "
            f"{h.c('type(rel2)')}. Patents and pubmed are not yet included "
            "(TODO at adapter line 123).",
            f"The Neo4j writer for the resolution pipeline is wired but "
            f"commented out in the orchestrator &mdash; current "
            f"{h.c(':Organization')} data comes from seed Cypher and the "
            "ClinicalTrials.gov ingest, not from the JSON checkpoint pipeline.",
        ]),
    ]

    return story
