"""Per-route flow guide for Eugene's organization_alias_search_router.

Endpoint:
    GET /list/organization/aliases/{organization_name}

Walks an engineer from the FastAPI boundary, through DI wiring and the
APOC subgraphNodes-style Cypher, into the JSON shape returned to the
caller. Notes the @deprecated marker, the broken read Cypher, and the
fact the router is not currently registered in src/eugene_ws.py.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_ORGANIZATION_ALIAS_SEARCH_FLOW_GUIDE.pdf"
TITLE = "Eugene Organization Alias Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ---------- cover -------------------------------------------------------
    story += [
        h.p("Eugene Organization Alias Search &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP boundary &rarr; deprecated v1 "
            "organization adapter &rarr; APOC subgraph traversal &rarr; "
            "ListResponse",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers spelunking the older organization-alias subgraph ("
            + h.c("subsidiary") + ", "
            + h.c("acquisition") + ", "
            + h.c("merger") + ", "
            + h.c("demerger") + ", "
            + h.c("organization_spelling_variation")
            + "). The lone endpoint "
            + h.c("GET /list/organization/aliases/{organization_name}")
            + " is intended to fan out from a canonical organization node "
            "along " + h.c(":HAS_ALIAS")
            + " edges and return the union of alias display names. As of "
            "this writing the read path has multiple bugs and the router "
            "is <b>not</b> registered in " + h.c("src/eugene_ws.py")
            + ", so the route is effectively dead code in production "
            "&mdash; this guide documents it for the engineer who must "
            "revive or remove it.",
        ),
        h.p("Reference endpoint", h.H2),
        *h.bullets([
            h.c("GET /list/organization/aliases/{organization_name}")
            + " &mdash; e.g. "
            + h.c("GET /list/organization/aliases/CSL%20Behring")
            + ". Returns "
            + h.c("ListResponse{count, results: [alias_name, ...]}")
            + ".",
        ]),
        h.p("Deprecation", h.H2),
        h.p(
            "Both the router (module-level docstring) and the adapter ("
            + h.c("Neo4jOrganizationAdapter")
            + ", class docstring &mdash; "
            + h.c("@deprecated v1 organizations, replaced with v2 eugene load")
            + ") are explicitly marked deprecated. The v2 model lives at "
            + h.c("OrganizationNodeEnum.ORGANIZATION_V2")
            + " (" + h.c("label = organization")
            + ") and is read by the modern "
            + h.c("/organizations/*")
            + " search router; this alias subgraph uses the v1 labels "
            "listed below and predates that migration.",
        ),
        h.PageBreak(),
    ]

    # ---------- 0. schema ---------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "The alias subgraph centres on a single anchor "
            + h.c(":company")
            + " node with one or more typed alias leaves attached via "
            + h.c(":HAS_ALIAS")
            + " edges:",
        ),
        h.code(
            "(:company { node_id, node_name, offical_name, parent, ... })\n"
            "(:subsidiary                       { node_id, node_name })\n"
            "(:acquisition                      { node_id, node_name })\n"
            "(:merger                           { node_id, node_name })\n"
            "(:demerger                         { node_id, node_name })\n"
            "(:organization_spelling_variation  { node_id, node_name })\n"
            "(:organization                     { node_id, node_name })\n"
            "\n"
            "(:company)-[:HAS_ALIAS]-(:subsidiary)\n"
            "(:company)-[:HAS_ALIAS]-(:acquisition)\n"
            "(:company)-[:HAS_ALIAS]-(:merger)\n"
            "(:company)-[:HAS_ALIAS]-(:demerger)\n"
            "(:company)-[:HAS_ALIAS]-(:organization_spelling_variation)"
        ),
        h.p("Enum sources", h.H2),
        *h.bullets([
            h.c("OrganizationNodeEnum") + " &mdash; "
            + h.c("src/organization/model/organization_node_enum.py")
            + ". Note the <b>v1/v2/v3 collision</b>: "
            + h.c('ORGANIZATION_V2 = 8, "organization"')
            + " and "
            + h.c('ORGANIZATION_V3 = 8, "Organization"')
            + " share the ordinal 8 and differ only in label case. The v1 "
            "write path uses "
            + h.c("COMPANY") + " (" + h.c("company")
            + ") as the anchor label, while the v1 query path tries to "
            + h.c("MATCH (:organization)")
            + " &mdash; a label mismatch (see section 2).",
            h.c("OrganizationRelationshipEnum.HAS_ALIAS") + " &mdash; "
            + h.c("src/organization/model/organization_relationship_enum.py")
            + " (value " + h.c('"has_alias"')
            + "). It is the only relationship type in this subgraph; the "
            "write path emits an <b>undirected</b> "
            + h.c("MERGE (organization)-[:HAS_ALIAS]-(alias)")
            + " edge.",
            "Foundational "
            + h.c('FoundationalNodeEnum.ORGANIZATION = 32, "Organization"')
            + " is the modern label used by the v2 search router and the "
            "patent/clinical-trial joins. It deliberately does <b>not</b> "
            "overlap with the v1 alias labels above.",
            "Like the rest of Eugene there are no Neo4j CREATE "
            "CONSTRAINTs; idempotency comes from "
            + h.c("MERGE") + " on "
            + h.c("{ node_name: $name }")
            + " (note: <i>not</i> "
            + h.c("node_id")
            + " &mdash; two orgs with the same alias display name will "
            "collide).",
        ]),
        h.PageBreak(),
    ]

    # ---------- 1. HTTP entry ----------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the router", h.H1),
        h.p("src/organization/router/organization_alias_search_router.py", h.PATH),
        *h.bullets([
            "Router prefix: " + h.c("/list") + ", tags "
            + h.c('["organization"]') + " (lines 15-18).",
            "Module-load DI at line 20: "
            + h.c("org_adapter = organization_adapter()")
            + " &mdash; resolved via "
            + h.c("src/organization/conf/search_conf.py:23")
            + " which returns a "
            + h.c("Neo4jOrganizationAdapter")
            + " bound to "
            + h.c("GraphDbConnectionFactory.remote_neo4j_instance_from_env()")
            + ".",
            "Path parameter "
            + h.c("organization_name") + " is "
            + h.c("Annotated[str, Path(...), AfterValidator(validate_value)]")
            + " (lines 33-43). "
            + h.c("validate_value") + " ("
            + h.c("src/foundation/router/validate_util.py:36")
            + ") rejects values containing any of "
            + h.c("%, _, $, ;, :, ^, *")
            + " &mdash; this is the SQL/Cypher-injection guard.",
            "Path constraints: "
            + h.c("min_length=0, max_length=256")
            + " (note the "
            + h.c("min_length=0")
            + " &mdash; FastAPI will still 404 on an empty segment, so "
            "this is effectively 1-256).",
            "Response wrapper: "
            + h.c("ListResponse{count: int, results: list[str]}")
            + " from "
            + h.c("src/foundation/router/model/list_response.py")
            + ", with "
            + h.c("response_model_exclude_none=True") + ".",
            "Empty-result behaviour: when the adapter returns "
            + h.c("None")
            + ", the handler returns "
            + h.c("ListResponse(count=0, results=[])")
            + " rather than 404 (line 46-47). Otherwise it sorts the "
            "aliases in place before wrapping (line 48).",
        ]),
        h.p("Handler body (lines 33-49)", h.H2),
        h.code(
            "@router.get(\n"
            "    \"/organization/aliases/{organization_name}\",\n"
            "    response_model=ListResponse,\n"
            "    response_model_exclude_none=True,\n"
            ")\n"
            "async def list_organization_aliases(\n"
            "    organization_name: Annotated[\n"
            "        str,\n"
            "        Path(..., max_length=256, min_length=0,\n"
            "             example=\"CSL Behring\"),\n"
            "        AfterValidator(validate_value),\n"
            "    ],\n"
            "):\n"
            "    aliases = org_adapter.find_aliases_by_name(\n"
            "        organization=organization_name)\n"
            "    if aliases is None:\n"
            "        return ListResponse(count=0, results=[])\n"
            "    aliases.sort()\n"
            "    return ListResponse(count=len(aliases), results=aliases)"
        ),
        h.p("Is the router wired in eugene_ws?", h.H2),
        h.p(
            "<b>No.</b> "
            + h.c("src/eugene_ws.py")
            + " imports and includes "
            + h.c("drug_alias_search_router")
            + " (line 47, line 69) but there is no corresponding import "
            "for "
            + h.c("organization_alias_search_router")
            + " and no "
            + h.c("app.include_router(organization_alias_search_router.router)")
            + " call. The route therefore does not appear in OpenAPI and "
            + h.c("curl /list/organization/aliases/CSL%20Behring")
            + " will 404 in any environment running the current "
            + h.c("eugene_ws.py")
            + ". To revive it: add an "
            + h.c("from organization.router import organization_alias_search_router")
            + " in " + h.c("eugene_ws.py:47")
            + " block and append it to the router list at line 69.",
        ),
        h.PageBreak(),
    ]

    # ---------- 2. Query adapter -------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the (broken) read Cypher", h.H1),
        h.p("src/organization/infra/db/neo4j_organization_adapter.py", h.PATH),
        *h.bullets([
            "Entry point: "
            + h.c("find_aliases_by_name(organization)")
            + " (line 29). Opens a session, then a transaction, and "
            "delegates to "
            + h.c("_find_aliases_by_name") + " (line 41).",
            h.c("_find_aliases_by_name")
            + " runs the Cypher returned by "
            + h.c("_generate_search()")
            + " (line 354) with params "
            + h.c('{ "organization_name": organization }')
            + " and pulls "
            + h.c('record["aliases"]')
            + " from the single record (line 56).",
            "Wraps "
            + h.c("DriverError") + " / " + h.c("Neo4jError")
            + " and re-raises &mdash; no per-error mapping to HTTP status.",
        ]),
        h.p("_generate_search() &mdash; verbatim (lines 354-368)", h.H2),
        h.code(
            "MATCH (o:`organization`)\n"
            "WHERE o.organization_id = $organization_name\n"
            "CALL apoc.path.subgraphNodes([n],\n"
            "{ \n"
            "    relationshipFilter: \"has_alias\",\n"
            "    maxLevel: 2\n"
            "}) YIELD org\n"
            "RETURN DISTINCT org.node_name as name,\n"
            "    toStringOrNull(org.node_id) as org_id,\n"
            "    toStringOrNull(org.organization_name) as org_name"
        ),
        h.p("Bugs to flag before you depend on this", h.H2),
        *h.bullets([
            "<b>Anchor label mismatch.</b> The Cypher matches "
            + h.c(":`organization`")
            + " (the v2 label, via "
            + h.c("OrganizationNodeEnum.ORGANIZATION_V2.value[1]")
            + "), but the write path in "
            + h.c("_upsert_organization_resolution")
            + " (line 94-106) creates the anchor as "
            + h.c(":company")
            + " (via "
            + h.c("OrganizationNodeEnum.COMPANY.value[1]")
            + "). Anything written by this adapter is unreachable from "
            "this read.",
            "<b>Wrong anchor property.</b> The WHERE clause filters on "
            + h.c("o.organization_id = $organization_name")
            + ", but the write path stores the human-readable name in "
            + h.c("organization.node_name") + " / "
            + h.c("organization.offical_name")
            + " (sic, typo preserved). No node has "
            + h.c("organization_id")
            + " set by the ingest path.",
            "<b>Undefined Cypher variable.</b> "
            + h.c("apoc.path.subgraphNodes([n], ...)")
            + " references " + h.c("[n]")
            + " but the MATCH binds " + h.c("o")
            + ", not " + h.c("n")
            + " &mdash; Neo4j will reject this with "
            + h.c("Variable `n` not defined") + ".",
            "<b>YIELD column mismatch.</b> "
            + h.c("apoc.path.subgraphNodes")
            + " yields a single column named "
            + h.c("node") + ", not " + h.c("org")
            + ". The " + h.c("YIELD org")
            + " clause will fail with "
            + h.c("Unknown procedure output: `org`") + ".",
            "<b>Missing RETURN column.</b> The read path expects "
            + h.c('record["aliases"]')
            + " (adapter line 56) but the Cypher returns "
            + h.c("name, org_id, org_name")
            + " &mdash; there is no "
            + h.c("aliases")
            + " column. Even if the Cypher parsed, the dict-key lookup "
            "would raise.",
            "<b>Sibling adapter has the same bug pattern.</b> "
            + h.c("Neo4jOrganizationQueryAdapter") + " ("
            + h.c("neo4j_organization_query_adapter.py:56")
            + ") also references undefined "
            + h.c("n") + " in its WHERE / "
            + h.c("org")
            + " in its RETURN, and is similarly unused at runtime. Treat "
            "both as cut-and-paste drafts.",
        ]),
        h.p("What the Cypher <i>should</i> look like", h.H2),
        h.p(
            "For reference, the working drug-alias equivalent (see "
            + h.c("drug_alias_search_router.py:309-319")
            + ") uses the same shape but with consistent bindings:",
        ),
        h.code(
            "MATCH (n:`company`)\n"
            "WHERE n.node_name = $organization_name\n"
            "  AND (n.is_hidden IS NULL OR NOT n.is_hidden)\n"
            "CALL apoc.path.subgraphNodes([n],\n"
            "      { relationshipFilter: \"has_alias\",\n"
            "        maxLevel: 2 }) YIELD node\n"
            "RETURN collect(DISTINCT node.node_name) AS aliases"
        ),
        h.PageBreak(),
    ]

    # ---------- 3. Mapper / response model ---------------------------------
    story += [
        h.p("3. Mapper / response model", h.H1),
        h.p(
            "Unlike the drug-alias route there is no dedicated mapper: the "
            "adapter is contracted to return "
            + h.c("list[str]")
            + " of alias display names directly. The router does the only "
            "post-processing &mdash; sort + wrap.",
        ),
        h.p("ListResponse", h.H2),
        h.p("src/foundation/router/model/list_response.py", h.PATH),
        h.code(
            "class ListResponse(BaseModel):\n"
            "    count: int\n"
            "    results: list[str]"
        ),
        h.p("Sample JSON (what the route would emit if the Cypher worked)", h.H2),
        h.code(
            "{\n"
            "  \"count\": 4,\n"
            "  \"results\": [\n"
            "    \"CSL\",\n"
            "    \"CSL Behring AG\",\n"
            "    \"CSL Behring LLC\",\n"
            "    \"ZLB Behring\"\n"
            "  ]\n"
            "}"
        ),
        h.p(
            "Note the canonical anchor name itself is <b>not</b> filtered "
            "out by the read Cypher &mdash; the working version above "
            "would include the "
            + h.c(":company")
            + " node alongside its aliases, unless the caller "
            "post-filters.",
        ),
        h.PageBreak(),
    ]

    # ---------- 4. ETL ------------------------------------------------------
    story += [
        h.p("4. ETL &mdash; how aliases would be ingested", h.H1),
        h.p("src/organization/provider/organization_ingest_orchestrator.py", h.PATH),
        *h.bullets([
            "Entry CLI: "
            + h.c("OrganizationIngestOrchestrator.ingest(checkpoint_dir)")
            + " (line 38). Loads resolutions from a checkpoint dir, runs "
            "them through the multipass merge orchestrator, then assigns "
            "ids.",
            "<b>Neo4j writes are commented out</b> (lines 51-52): "
            + h.c("# todo: ingest into neo4j") + " / "
            + h.c("# return self.ingest_organizations(...)")
            + ". The CLI currently returns only the list of merged "
            + h.c("official_name")
            + " strings &mdash; nothing is persisted by the default "
            "ingest entry point.",
            "The write helper "
            + h.c("ingest_organizations")
            + " (line 66) does still exist and delegates to "
            + h.c("Neo4jOrganizationAdapter.upsert_organization_resolutions")
            + " (line 61), so a caller could re-enable writes by "
            "uncommenting the orchestrator line or calling the helper "
            "directly.",
            "Per-organization upsert: "
            + h.c("_upsert_organization_resolution")
            + " (line 85) MERGEs a "
            + h.c(":company")
            + " anchor on "
            + h.c("{ node_name: $offical_name }")
            + " (typo preserved from the source), then emits one "
            + h.c("MERGE (alias:`<label>` {...}) MERGE (organization)-[:HAS_ALIAS]-(alias)")
            + " block per alias.",
            "Aliases come from five buckets on "
            + h.c("OrganizationResolution") + ": "
            + h.c("subsidiaries") + ", "
            + h.c("acquisitions") + ", "
            + h.c("spelling_variations") + ", "
            + h.c("mergers") + ", "
            + h.c("demergers")
            + ". <b>Bug:</b> the merger and demerger generators are both "
            "passed "
            + h.c("organization_resolution.spelling_variations")
            + " (lines 236-243), not the merger/demerger sets &mdash; so "
            "those bucket-specific aliases are silently dropped and "
            "spelling variations are written three times under three "
            "different bucket labels.",
            "All five generators delegate to "
            + h.c("_generate_alias_upserts(..., org_node_type=ORGANIZATION)")
            + " (lines 260-303) &mdash; meaning every alias is labelled "
            + h.c(":organization")
            + " regardless of which bucket it came from. The richer "
            + h.c(":subsidiary") + " / " + h.c(":acquisition")
            + " / etc. labels listed in the enum are <b>not</b> applied "
            "by this code path.",
            "Batching: aliases are upserted in chunks of "
            + h.c("step_size = 200")
            + " (line 119), with one chained "
            + h.c("MERGE")
            + " script per chunk and a final "
            + h.c("RETURN organization.node_id") + ".",
        ]),
        h.PageBreak(),
    ]

    # ---------- 5. Debugging walk -----------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "Confirm the route is missing: "
            + h.c("grep -n organization_alias_search_router src/eugene_ws.py")
            + " &mdash; expect zero hits. Add the import + "
            + h.c("include_router")
            + " call before doing anything else.",
            "Stand up the stack: "
            + h.c("docker-compose up eugene_neo4j eugene_ws")
            + ". Confirm "
            + h.c("apoc.path.subgraphNodes")
            + " is available: in cypher-shell run "
            + h.c("RETURN apoc.version()") + ".",
            "Seed at least one anchor: "
            + h.c("CREATE (:company { node_name: 'CSL Behring', offical_name: 'CSL Behring', node_id: 'organization_test' })")
            + " then attach two aliases via "
            + h.c("MERGE (:organization { node_name: 'CSL' })")
            + " and "
            + h.c("MERGE (a)-[:HAS_ALIAS]-(c)") + ".",
            "Hit the endpoint: "
            + h.c('curl -s "http://localhost:8080/list/organization/aliases/CSL%20Behring" | jq .')
            + ". With the current Cypher you will see a 500 with an "
            + h.c("apoc.path.subgraphNodes") + " / "
            + h.c("Variable `n` not defined")
            + " error in the eugene_ws logs &mdash; that confirms you "
            "have actually reached the adapter.",
            "Breakpoint at "
            + h.c("neo4j_organization_adapter.py:42")
            + " (inside "
            + h.c("_find_aliases_by_name")
            + "), inspect the generated "
            + h.c("search")
            + " string, copy it into Neo4j Browser with the "
            + h.c("$organization_name")
            + " parameter, and iterate the fixes from section 2 until it "
            "returns a row with an "
            + h.c("aliases") + " column.",
            "To exercise the write path that currently feeds this read, "
            "uncomment "
            + h.c("organization_ingest_orchestrator.py:52")
            + ", point "
            + h.c("ingest(checkpoint_dir=...)")
            + " at a directory of "
            + h.c("OrganizationResolution")
            + " JSON, and watch "
            + h.c("_generate_alias_upserts")
            + " produce one Cypher block per alias. Worth fixing the "
            "merger/demerger bucket bug (section 4) at the same time.",
        ]),
        h.PageBreak(),
    ]

    # ---------- 6. Reference index ----------------------------------------
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP boundary\n"
            "  src/organization/router/organization_alias_search_router.py\n"
            "  src/foundation/router/model/list_response.py\n"
            "  src/foundation/router/validate_util.py            # validate_value (L36)\n"
            "  src/eugene_ws.py                                  # router NOT included\n"
            "\n"
            "DI\n"
            "  src/organization/conf/search_conf.py              # organization_adapter() (L23)\n"
            "  src/graph/infra/db/graph_db_connection_factory.py # _neo4j_driver()\n"
            "\n"
            "Read path (adapter + buggy Cypher)\n"
            "  src/organization/infra/db/neo4j_organization_adapter.py\n"
            "    find_aliases_by_name           (L29)\n"
            "    _find_aliases_by_name          (L41)\n"
            "    _generate_search               (L354) -- bugs documented in section 2\n"
            "  src/organization/infra/db/neo4j_organization_query_adapter.py\n"
            "    -- sibling adapter, also unused, similar bugs\n"
            "\n"
            "Schema enums\n"
            "  src/organization/model/organization_node_enum.py\n"
            "    COMPANY, ORGANIZATION, ORGANIZATION_V2/V3,\n"
            "    SUBSIDIARY, ACQUISITION, MERGER, DEMERGER, SPELLING_VARIATION\n"
            "  src/organization/model/organization_relationship_enum.py\n"
            "    HAS_ALIAS\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "    ORGANIZATION = 32, \"Organization\"   # v2 modern label\n"
            "\n"
            "ETL / write path\n"
            "  src/organization/provider/organization_ingest_orchestrator.py\n"
            "    ingest                         (L38)  -- Neo4j writes commented out (L51-52)\n"
            "    ingest_organizations           (L66)\n"
            "  src/organization/infra/db/neo4j_organization_adapter.py\n"
            "    upsert_organization_resolutions (L61)\n"
            "    _upsert_organization_resolution (L85)\n"
            "    _generate_organization_alias_upserts (L171)\n"
            "    _generate_alias_upserts         (L305)\n"
            "  src/organization/model/organization_resolution.py\n"
            "  src/organization/load/organization_resolution_loader.py\n"
        ),
    ]

    return story
