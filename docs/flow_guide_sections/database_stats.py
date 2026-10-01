"""ReportLab section: Eugene Database Stats end-to-end flow."""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_DATABASE_STATS_FLOW_GUIDE.pdf"
TITLE = "Eugene Database Stats - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----- Cover -----------------------------------------------------------
    story += [
        h.p("Eugene Database Stats &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: FastAPI router &rarr; DI factory &rarr; "
            "Neo4j adapter &rarr; per-label COUNT Cypher &rarr; DatabaseStats response",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene reports its top-level "
            "graph health numbers (total nodes, total relationships, per-label "
            f"counts for {h.c('drug')}, {h.c('disease')}, {h.c('gene_protein')}, "
            f"{h.c('Patent_Application')}, {h.c('ClinicalTrial')}, "
            f"{h.c('Research')}, {h.c('Investigators')}, {h.c('Organization')}) "
            "via the single read-only "
            f"{h.c('GET /stats')} endpoint. Every reference uses the form "
            f"{h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoint", h.H2),
        *h.bullets([
            f"{h.c('GET /stats')} &mdash; returns a single "
            f"{h.c('DatabaseStats')} JSON payload. No query parameters, no "
            "path parameters, no body.",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "The router carries a "
            f"{h.c('# todo: add daily caching')} comment &mdash; every call "
            "today fans out to ~12 Cypher queries that scan the entire graph "
            f"({h.c('MATCH (n)')}, {h.c('MATCH (n)-[r]-(n2)')}, and one "
            f"{h.c('MATCH (n:`Label`)')} per foundational label). On a large "
            "graph this can be slow; treat the endpoint as a coarse health "
            "probe, not a hot path. The DI is also resolved at module load "
            f"({h.c('stats_adapter = neo4j_database_stats_adapter()')}), so "
            "the Neo4j driver is created once at import time.",
        ),
        h.PageBreak(),
    ]

    # ----- 0. Schema -------------------------------------------------------
    story += [
        h.p("0. Schema &mdash; what the endpoint exposes", h.H1),
        h.p(
            "The response is a flat dataclass of pre-formatted count strings "
            f"({h.c('123 -> &quot;123&quot;')}, {h.c('1500 -> &quot;1.5k&quot;')}, "
            f"{h.c('2300000 -> &quot;2.3m&quot;')}). It mixes three kinds of "
            "metric:",
        ),
        *h.bullets([
            "<b>Global graph totals</b> &mdash; "
            f"{h.c('node_count')}, {h.c('relationship_count')}.",
            "<b>Per-label node counts</b> &mdash; one "
            f"{h.c('MATCH (n:`Label`) RETURN count(n)')} per foundational "
            f"label: {h.c('drug')}, {h.c('disease')}, {h.c('gene_protein')}, "
            f"{h.c('Patent_Application')}, {h.c('ClinicalTrial')}, "
            f"{h.c('Research')}, {h.c('Investigators')}, "
            f"{h.c('Organization')}.",
            "<b>Domain rollups</b> &mdash; distinct count of "
            f"{h.c('organization_id')} on {h.c(':Organization')} "
            f"(disambiguated orgs), distinct {h.c('therapeutic_area')} and "
            f"{h.c('therapeutic_subgroup')} on {h.c(':ClinicalTrial')}, plus "
            f"min/max {h.c('filing_date')} on {h.c(':Patent_Application')}.",
            f"{h.c('drug_synonym_count')} is wired in the model but the "
            f"adapter hard-codes it to {h.c('0')} &mdash; the route does NOT "
            f"actually count {h.c(':drug_synonym')} nodes (see "
            f"{h.c('neo4j_database_stats_adapter.py:62')}).",
            "There are no Neo4j CREATE CONSTRAINTs in Eugene; these COUNTs "
            "are full label scans, no index assist.",
        ]),
        h.code(
            "DatabaseStats(\n"
            "    node_count, relationship_count,\n"
            "    drug_count, drug_synonym_count,           # synonym always 0\n"
            "    disease_count, gene_protein_count,\n"
            "    uspto_count, uspto_filing_date_min, uspto_filting_date_max,\n"
            "    clinical_trial_count,\n"
            "    therapeutic_area_count, therapeutic_area_subgroup_count,\n"
            "    pubmed_count, pubmed_researcher_count,\n"
            "    organization_count, disambiguated_organization_count,\n"
            ")"
        ),
        h.PageBreak(),
    ]

    # ----- 1. HTTP entry ---------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; router, params, DI", h.H1),
        h.p("<font face='Courier'>src/stats/router/database_stats_router.py</font>", h.PATH),
        *h.bullets([
            f"Router prefix {h.c('/stats')}, tag {h.c('stats')}.",
            f"Single handler {h.c('fetch_database_stats')} (line 20) bound to "
            f"{h.c('GET &quot;&quot;')} &mdash; the full path is "
            f"{h.c('GET /stats')}.",
            f"{h.c('response_model=DatabaseStats')} with "
            f"{h.c('response_model_exclude_none=True')}.",
            "No query, path, or body params; no validators; no auth "
            "dependency at the route level.",
            f"DI at module load (line 16): "
            f"{h.c('stats_adapter = neo4j_database_stats_adapter()')} &mdash; "
            "the adapter (and its Neo4j driver) is constructed once at import "
            "time, not per request.",
            f"Registered in {h.c('src/eugene_ws.py:34,60')} via "
            f"{h.c('app.include_router(database_stats_router.router)')}.",
        ]),
        h.code(
            "router = APIRouter(prefix=\"/stats\", tags=[\"stats\"])\n"
            "stats_adapter = neo4j_database_stats_adapter()\n\n"
            "@router.get(\"\", response_model=DatabaseStats,\n"
            "            response_model_exclude_none=True)\n"
            "async def fetch_database_stats():\n"
            "    # todo: add daily caching\n"
            "    return stats_adapter.query_system_stats()"
        ),
        h.p("Factory", h.H2),
        h.p("<font face='Courier'>src/stats/conf/conf.py</font>", h.PATH),
        h.code(
            "def _neo4j_driver() -> Driver:\n"
            "    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()\n\n"
            "def neo4j_database_stats_adapter() -> Neo4jDatabaseStatsAdapter:\n"
            "    return Neo4jDatabaseStatsAdapter(driver=_neo4j_driver())"
        ),
        h.p(
            f"The driver comes from {h.c('GraphDbConnectionFactory')} in "
            f"{h.c('src/graph/infra/db/graph_db_connection_factory.py')}, "
            "which reads Neo4j URI / user / password from the environment. "
            f"The adapter pins {h.c('database=&quot;neo4j&quot;')}.",
        ),
        h.PageBreak(),
    ]

    # ----- 2. Query adapter ------------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; verbatim Cypher", h.H1),
        h.p("<font face='Courier'>src/stats/infra/db/adapter/neo4j_database_stats_adapter.py</font>", h.PATH),
        *h.bullets([
            f"{h.c('query_system_stats()')} (line 26) is the only public "
            f"method. It calls {h.c('ensure_connection(self.driver)')} once, "
            "then runs each Cypher below in sequence and assembles "
            f"{h.c('DatabaseStats')}.",
            f"Each helper uses {h.c('driver.execute_query(query_=..., result_transformer_=neo4j.Result.single)')} "
            f"and catches {h.c('DriverError')} / {h.c('Neo4jError')} (re-raises after logging).",
            f"Each helper is wrapped with {h.c('@log_time')} "
            f"({h.c('annotation/timer_annotation.py')}) &mdash; expect one "
            "timing log line per query in the response trace.",
        ]),
        h.p("Total node count (line 137)", h.H2),
        h.code(
            "MATCH (n)\n"
            "RETURN count(n) as node_count"
        ),
        h.p("Total relationship count (line 117)", h.H2),
        h.code(
            "MATCH (n)-[r]-(n2)\n"
            "RETURN count(r) as relationship_count"
        ),
        h.p(
            f"Note the undirected {h.c('-[r]-')} pattern: it returns "
            "<b>twice</b> the stored edge count because each relationship is "
            "traversed in both directions. The number reported in "
            f"{h.c('relationship_count')} is therefore 2x the underlying "
            "edge count &mdash; this is a known artifact of the current "
            "query, not a bug in the count formatter.",
        ),
        h.p("Per-label COUNT template (line 94)", h.H2),
        h.code(
            "MATCH (n:`%s`)\n"
            "RETURN count(n) as count"
        ),
        h.p(
            f"Invoked once per label via {h.c('_count_all_by_label(label)')} "
            "with these label strings (from "
            f"{h.c('FoundationalNodeEnum')}, "
            f"{h.c('src/foundation/model/foundational_node_enum.py')}): "
            f"{h.c('drug')}, {h.c('disease')}, {h.c('gene_protein')}, "
            f"{h.c('Patent_Application')}, {h.c('ClinicalTrial')}, "
            f"{h.c('Research')}, {h.c('Investigators')}, "
            f"{h.c('Organization')}.",
        ),
        h.PageBreak(),
    ]

    # ----- 2b. More Cypher -------------------------------------------------
    story += [
        h.p("2 (cont.) &mdash; rollup Cypher", h.H1),
        h.p("Disambiguated organizations (line 157)", h.H2),
        h.code(
            "MATCH (n:`Organization`)\n"
            "RETURN count(distinct(n.organization_id)) as disambiguated_org_count"
        ),
        h.p(
            "Counts distinct values of the "
            f"{h.c('organization_id')} property &mdash; one canonical entity "
            f"may have several {h.c(':Organization')} nodes sharing an id, so "
            f"this number is &lt;= {h.c('organization_count')}.",
        ),
        h.p("Therapeutic areas (line 182)", h.H2),
        h.code(
            "MATCH (n:`ClinicalTrial`)\n"
            "RETURN COUNT(DISTINCT(n.therapeutic_area))      as theraputic_area_count,\n"
            "       COUNT(DISTINCT(n.therapeutic_subgroup))  as theraputic_area_group_count"
        ),
        h.p(
            "One query returns both numbers. Property keys "
            f"{h.c('therapeutic_area')} and {h.c('therapeutic_subgroup')} "
            f"live on {h.c(':ClinicalTrial')} nodes. (The Cypher aliases "
            f"misspell &lsquo;therapeutic&rsquo; as "
            f"{h.c('theraputic_*')} &mdash; this only matters if you copy "
            "the query into Neo4j Browser.)",
        ),
        h.p("USPTO filing-date range (line 208)", h.H2),
        h.code(
            "MATCH (n:`Patent_Application`)\n"
            "RETURN toStringOrNull(min(n.filing_date)) as min_uspto_filing_date,\n"
            "       toStringOrNull(max(n.filing_date)) as max_uspto_filing_date"
        ),
        h.p(
            f"{h.c('toStringOrNull')} guarantees JSON-safe strings (or "
            f"{h.c('null')}) even when the property is a Neo4j temporal type "
            "or absent.",
        ),
        h.p("Drug synonyms &mdash; not queried", h.H2),
        h.p(
            f"{h.c('drug_synonym_count')} is hard-coded to {h.c('0')} on "
            f"line 62 of the adapter. There is no Cypher for it. If you need "
            f"the real number, add a {h.c('_count_all_by_label(FoundationalNodeEnum.DRUG_SYNONYM.value[1])')} "
            "call.",
        ),
        h.PageBreak(),
    ]

    # ----- 3. Mapper / response -------------------------------------------
    story += [
        h.p("3. Response model &mdash; DatabaseStats", h.H1),
        h.p("<font face='Courier'>src/stats/model/system_stats.py</font>", h.PATH),
        *h.bullets([
            f"Plain {h.c('@dataclass(frozen=True, unsafe_hash=True)')} "
            "&mdash; no Pydantic, but FastAPI is happy because the dataclass "
            "is JSON-serializable and used as "
            f"{h.c('response_model')}.",
            "There is no separate mapper class; the adapter builds the "
            "dataclass inline.",
            f"Every count field is typed {h.c('str')} because the static "
            f"{h.c('DatabaseStats.format_count(num: int)')} helper "
            "(line 28) converts integers to human-friendly suffixes "
            f"({h.c('&lt;1k -&gt; raw int')}, "
            f"{h.c('&gt;=1k -&gt; &quot;1.2k&quot;')}, "
            f"{h.c('&gt;=1m -&gt; &quot;3.4m&quot;')}, "
            f"{h.c('&gt;=1b -&gt; &quot;1.0b&quot;')}). The two date fields "
            f"are passed through verbatim from {h.c('toStringOrNull')}.",
            f"{h.c('response_model_exclude_none=True')} drops any "
            f"{h.c('null')} field from the wire payload (e.g. an empty USPTO "
            "date range).",
        ]),
        h.p("JSON sample", h.H2),
        h.code(
            "{\n"
            "  \"node_count\":                       \"4.2m\",\n"
            "  \"relationship_count\":               \"18.7m\",\n"
            "  \"drug_count\":                       \"14.3k\",\n"
            "  \"drug_synonym_count\":               \"0\",\n"
            "  \"disease_count\":                    \"31.5k\",\n"
            "  \"gene_protein_count\":               \"22.1k\",\n"
            "  \"uspto_count\":                      \"612.4k\",\n"
            "  \"uspto_filing_date_min\":            \"1976-01-06\",\n"
            "  \"uspto_filting_date_max\":           \"2026-03-21\",\n"
            "  \"clinical_trial_count\":             \"487.2k\",\n"
            "  \"therapeutic_area_count\":           \"412\",\n"
            "  \"therapeutic_area_subgroup_count\":  \"1.8k\",\n"
            "  \"pubmed_count\":                     \"2.1m\",\n"
            "  \"pubmed_researcher_count\":          \"948.0k\",\n"
            "  \"organization_count\":               \"126.7k\",\n"
            "  \"disambiguated_organization_count\": \"58.4k\"\n"
            "}"
        ),
        h.p(
            f"Note the field name {h.c('uspto_filting_date_max')} &mdash; "
            "a typo (&lsquo;filting&rsquo;) baked into the public contract. "
            "UI clients (Next.js dashboard, agent UI) depend on this exact "
            "spelling; do not silently rename.",
        ),
        h.PageBreak(),
    ]

    # ----- 4. Data source --------------------------------------------------
    story += [
        h.p("4. Data source &mdash; whole-graph dependency", h.H1),
        h.p(
            "Unlike per-entity routes (drug alias, patent search, etc.) this "
            "endpoint has no narrow data dependency &mdash; every Cypher "
            f"query above is an unfiltered label or graph scan. The answers "
            "reflect the current state of the <b>entire</b> Neo4j graph at "
            "call time.",
        ),
        *h.bullets([
            f"<b>Nodes by label</b> come from whichever ingest populated that "
            f"label: e.g. {h.c(':drug')} from "
            f"{h.c('bin/seed/*.cypher')} + "
            f"{h.c('src/ingest_drug_aliases.py')}; "
            f"{h.c(':Patent_Application')} from the USPTO ingest under "
            f"{h.c('src/foundation/load/')}; {h.c(':ClinicalTrial')} from "
            f"the CT.gov ingest; {h.c(':Research')} + "
            f"{h.c(':Investigators')} from the PubMed ingest; "
            f"{h.c(':Organization')} from the organization "
            "disambiguation pipeline.",
            f"<b>{h.c('relationship_count')}</b> sums <i>all</i> edges of "
            f"every type (HAS_DRUG_ALIAS, MENTIONS, CITES, "
            "ASSIGNED_TO, &hellip;), counted in both directions.",
            f"<b>Therapeutic-area rollups</b> depend on the "
            f"{h.c('therapeutic_area')} / "
            f"{h.c('therapeutic_subgroup')} properties being set on "
            f"{h.c(':ClinicalTrial')} nodes by the CT.gov ingest. Missing "
            "properties simply do not contribute to the distinct count.",
            f"<b>USPTO date range</b> depends on the "
            f"{h.c('filing_date')} property on "
            f"{h.c(':Patent_Application')} &mdash; if no patents exist, "
            f"both bounds come back as {h.c('null')} and are dropped from "
            f"the response by {h.c('exclude_none')}.",
            f"<b>{h.c('drug_synonym_count')}</b> is independent of the "
            "graph &mdash; always 0 (see Section 2b).",
            "Because there is no caching, each call materializes the "
            f"latest numbers. Expect &gt;100ms on a non-trivial graph "
            f"(twelve full scans / aggregations).",
        ]),
        h.PageBreak(),
    ]

    # ----- 5. Debugging walk ----------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Spin Neo4j + the API: {h.c('docker-compose up eugene_neo4j eugene_ws')} "
            f"and wait for {h.c('GET /health')} to return 200.",
            f"Smoke-test the route: {h.c('curl -s http://localhost:8000/stats | jq')}. "
            f"Confirm all sixteen fields are present and formatted with "
            f"{h.c('k')}/{h.c('m')}/{h.c('b')} suffixes.",
            f"Breakpoint at "
            f"{h.c('src/stats/router/database_stats_router.py:22')}; step "
            f"into {h.c('stats_adapter.query_system_stats()')} and watch "
            f"each {h.c('_count_*')} helper fire its Cypher in order.",
            f"Tail the server log: each helper is wrapped with "
            f"{h.c('@log_time')} and also emits "
            f"{h.c('logger.info(f&quot;count all: {{query}}&quot;)')} &mdash; "
            f"you should see ~12 timing lines plus their Cypher payloads "
            "per request.",
            f"Sanity-check a single label by hand in Neo4j Browser: paste "
            f"{h.c('MATCH (n:`drug`) RETURN count(n) AS count')} and "
            f"compare with {h.c('drug_count')} (un-format the suffix to "
            "compare).",
            f"To verify the relationship double-count: run "
            f"{h.c('MATCH (n)-[r]->(n2) RETURN count(r)')} (directed) and "
            f"compare with the route&rsquo;s undirected "
            f"{h.c('MATCH (n)-[r]-(n2)')} &mdash; you should see exactly 2x.",
            f"To investigate slowness, time the helpers individually via "
            f"the {h.c('@log_time')} output; the per-label COUNTs scale "
            "linearly with label cardinality (no index).",
        ]),
        h.PageBreak(),
    ]

    # ----- 6. Reference index ---------------------------------------------
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "Schema\n"
            "  src/stats/model/system_stats.py                      # DatabaseStats dataclass + format_count\n"
            "  src/foundation/model/foundational_node_enum.py       # label strings consumed by the adapter\n\n"
            "HTTP entry\n"
            "  src/stats/router/database_stats_router.py            # GET /stats, module-load DI\n"
            "  src/eugene_ws.py                                     # import L34, register L60\n\n"
            "DI / factory\n"
            "  src/stats/conf/conf.py                               # neo4j_database_stats_adapter()\n"
            "  src/graph/infra/db/graph_db_connection_factory.py    # remote_neo4j_instance_from_env()\n\n"
            "Query adapter\n"
            "  src/stats/infra/db/adapter/neo4j_database_stats_adapter.py\n"
            "    L26   query_system_stats              # orchestrates all counts\n"
            "    L80   _count_all_by_label             # per-label COUNT\n"
            "    L94   _build_count_all_by_label       # MATCH (n:`%s`) RETURN count(n)\n"
            "    L103  _count_all_relationships        # MATCH (n)-[r]-(n2) (undirected, 2x)\n"
            "    L123  _count_all_nodes                # MATCH (n) RETURN count(n)\n"
            "    L143  _count_disambiguated_orgs       # DISTINCT n.organization_id\n"
            "    L165  _count_theraputic_areas         # DISTINCT therapeutic_area + _subgroup\n"
            "    L191  _fetch_min_max_uspto_dates      # min/max n.filing_date\n\n"
            "Cross-cutting\n"
            "  src/graph/util/util.py                               # ensure_connection\n"
            "  src/annotation/timer_annotation.py                   # @log_time decorator\n"
        ),
    ]

    return story
