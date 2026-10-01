"""Flow-guide section module for Eugene's patent-count route.

GET /count/patents/{drugs,clinicaltrials,geneproteins} - returns a simple
{search_key, patent_count} envelope from a Cypher COUNT over the patent
subgraph the patent_search_router walks. This guide intentionally cross-
references EUGENE_PATENT_FLOW_GUIDE.pdf for the upstream ETL chain instead
of re-deriving it.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_PATENT_COUNT_FLOW_GUIDE.pdf"
TITLE = "Eugene Patent Count - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----- cover -----------------------------------------------------------
    story += [
        h.p("Eugene Patent Count &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP &rarr; module-load DI &rarr; "
            "Neo4j COUNT Cypher &rarr; {search_key, patent_count} JSON",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need a file-referenced trace of the patent-count "
            "endpoints. These routes are the cheap companions to the full "
            f"{h.c('/patents/*')} search endpoints &mdash; clients call the count "
            "first to compute the maximum page number, then page through the "
            f"search. Every reference uses the form {h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('GET /count/patents/drugs?drug_id=DB00993')}",
            f"{h.c('GET /count/patents/clinicaltrials?nct_id=NCT05648006')}",
            f"{h.c('GET /count/patents/geneproteins?gene_protein=ABL1')}",
        ]),
        h.p(
            f"All three are declared in "
            f"{h.c('src/foundation/router/patent_count_router.py')} and registered "
            f"by {h.c('src/eugene_ws.py:49')} / {h.c('src/eugene_ws.py:71')} "
            f"inside {h.c('add_routers(app)')}.",
        ),
        h.p("Relationship to the patent-search route", h.H2),
        h.p(
            f"The count routes share the {h.c('Neo4jPatentQueryAdapter')} "
            f"singleton with {h.c('patent_search_router.py')} (both call "
            f"{h.c('neo4j_patent_query_adapter()')} at module load &mdash; "
            f"{h.c('patent_count_router.py:28')} and "
            f"{h.c('patent_search_router.py:34')}). They walk the same edges "
            "with the same anchors and just substitute "
            f"{h.c('count(n2) AS count')} for the paginated projection. If a "
            "drug returns 17 patents from the count route, the search route "
            "with page_size=50 will return exactly those 17 rows on page 1.",
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Section 0 &mdash; schema (the three edge types the count walks). Read first.",
            "Sections 1-3 &mdash; HTTP, Cypher, response shape, top-down.",
            f"Section 4 &mdash; pointer to {h.c('EUGENE_PATENT_FLOW_GUIDE.pdf')} for ETL.",
            "Section 5 &mdash; copy-paste debug walk.",
            "Section 6 &mdash; flat reference index.",
        ]),
        h.PageBreak(),
    ]

    # ----- 0. schema -------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "The patent-count routes anchor on one of three node types and "
            f"traverse a single hop to a {h.c(':Patent_Application')} node. "
            "There is no APOC traversal, no variable-length match &mdash; just "
            "one labeled edge.",
        ),
        h.code(
            "(:drug          { node_id })       -[:disclosed_in]-              (:Patent_Application)\n"
            "(:ClinicalTrial { nct_id  })       -[:supports_patent_application]-(:Patent_Application)\n"
            "(:gene_protein  { node_name })     -[:patent_app_target]-          (:Patent_Application)"
        ),
        *h.bullets([
            f"Node labels come from {h.c('FoundationalNodeEnum')} in "
            f"{h.c('src/foundation/model/foundational_node_enum.py')}: "
            f"{h.c('DRUG')} (line 14, label {h.c('drug')}), "
            f"{h.c('CLINICAL_TRIAL')} (line 10, label {h.c('ClinicalTrial')}), "
            f"{h.c('GENE_PROTEIN')} (line 18, label {h.c('gene_protein')}), and "
            f"{h.c('PATENT_APPLICATION')} (line 31, label "
            f"{h.c('Patent_Application')}). Note the mixed case &mdash; "
            f"{h.c('Patent_Application')} and {h.c('ClinicalTrial')} keep their "
            "PascalCase in Neo4j, the rest are lowercase.",
            f"Relationship types come from {h.c('FoundationalRelationshipEnum')} "
            f"in {h.c('src/foundation/model/foundational_relationship_enum.py')}: "
            f"{h.c('DISCLOSED_IN')} (line 25), "
            f"{h.c('SUPPORTS_PATENT_APPLICATION')} (line 26), "
            f"{h.c('PATENT_APP_TARGET')} (line 27). The drug shape "
            f"({h.c(':drug)-[:disclosed_in]-(:Patent_Application')}) is the "
            "same one the patent_search_router walks for paginated results.",
            f"The {h.c(':disclosed_in')} edge is <b>undirected</b> in the Cypher "
            f"({h.c('-[r:`disclosed_in`]-')} not "
            f"{h.c('-[r:`disclosed_in`]-&gt;')}). The count is symmetric &mdash; "
            "direction in the graph does not change the answer.",
            f"Anchor keys differ per route: drug anchors on {h.c('n.node_id')}, "
            f"clinical trial on {h.c('n.nct_id')} (not {h.c('node_id')}!), and "
            f"gene/protein on {h.c('n.node_name')} (also not {h.c('node_id')}).",
            "Like the rest of Eugene there are no Neo4j CREATE CONSTRAINTs; "
            "uniqueness is by ETL convention, not enforced at the DB layer.",
        ]),
        h.PageBreak(),
    ]

    # ----- 1. HTTP entry ---------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:49')} imports the module as "
            f"{h.c('patent_count_router')}; "
            f"{h.c('src/eugene_ws.py:71')} adds it to the includes list inside "
            f"{h.c('add_routers(app)')}. The module-level "
            f"{h.c('router = APIRouter(prefix=&quot;/count/patents&quot;, tags=[&quot;patents&quot;])')} "
            f"({h.c('patent_count_router.py:23-26')}) means the final paths are "
            f"{h.c('/count/patents/drugs')}, "
            f"{h.c('/count/patents/clinicaltrials')}, and "
            f"{h.c('/count/patents/geneproteins')}.",
        ),
        h.p("Module-load dependency injection", h.H2),
        h.p(f"{h.c('src/foundation/router/patent_count_router.py:28')}", h.PATH),
        h.code(
            "patent_query_adapter = neo4j_patent_query_adapter()"
        ),
        h.p(
            f"The DI factory at {h.c('src/foundation/conf/conf.py:199-211')} "
            f"resolves to a single {h.c('Neo4jPatentQueryAdapter')} bound to the "
            f"shared {h.c('_neo4j_driver()')} singleton. The same instance is "
            f"reused by {h.c('patent_search_router.py:34')} &mdash; both routers "
            "share one adapter, one driver, and one connection pool.",
        ),
        h.p("Endpoint signatures", h.H2),
        h.code(
            '@router.get("/drugs",          response_model_exclude_none=True)   # line 31\n'
            'async def count_related_patents_by_drug_id(drug_id):\n'
            '\n'
            '@router.get("/clinicaltrials", response_model_exclude_none=True)   # line 49\n'
            'async def count_related_patents_by_clinicaltrail_id(nct_id):\n'
            '\n'
            '@router.get("/geneproteins",   response_model_exclude_none=True)   # line 67\n'
            'async def count_related_patents_by_geneprotein_id(gene_protein):'
        ),
        h.p("Query params &amp; validators", h.H2),
        *h.bullets([
            f"{h.c('drug_id')} (line 33-42) &mdash; "
            f"{h.c('Query(example=&quot;DB00993&quot;, max_length=64, min_length=1)')} "
            f"+ {h.c('AfterValidator(validate_value)')}. "
            f"{h.c('validate_value')} ({h.c('validate_util.py:35-42')}) rejects any "
            f"of {h.c('% _ $ ; : ^ *')}. Note: it does <i>not</i> enforce the "
            f"{h.c('DB')} prefix &mdash; that stricter check lives in "
            f"{h.c('validate_drug_id')} (lines 58-68) which this route does not use.",
            f"{h.c('nct_id')} (line 51-60) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_clinical_trail_id)')} "
            f"({h.c('validate_util.py:45-55')}), which delegates to "
            f"{h.c('validate_value')} <i>and</i> additionally requires the "
            f"{h.c('NCT')} prefix (case-insensitive).",
            f"{h.c('gene_protein')} (line 69-78) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_gene_protein)')} "
            f"({h.c('validate_util.py:71-77')}); same special-char check, no "
            "prefix requirement.",
            "All three routes <b>require</b> their query parameter (no defaults); "
            "Pydantic returns a 422 if missing.",
        ]),
        h.p("Normalization", h.H2),
        h.p(
            f"Each handler calls the matching {h.c('case_helper')} normalizer "
            f"before hitting the adapter: {h.c('normalize_drug_id(drug_id)')} "
            f"(line 44), {h.c('normalize_clinical_trial_id(nct_id)')} (line 62), "
            f"and {h.c('normalize_gene_protein(gene_protein)')} (line 80). All "
            f"three live in {h.c('src/foundation/model/case_helper.py')}; they "
            "exist so casing on the wire (e.g. "
            f"{h.c('db00993')} vs. {h.c('DB00993')}) does not miss the Neo4j "
            "anchor.",
        ),
        h.p("<b>First breakpoint:</b> patent_count_router.py:45, 63, or 81 (the adapter call)."),
        h.PageBreak(),
    ]

    # ----- 2. adapter Cypher ----------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the COUNT Cypher", h.H1),
        h.p(
            f"{h.c('Neo4jPatentQueryAdapter')} lives at "
            f"{h.c('src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py')}. "
            "Each count entry point opens a session, begins a transaction, "
            "calls the matching private helper, and returns the integer.",
        ),
        h.p("Public entry points", h.H2),
        *h.bullets([
            f"{h.c('count_related_patents_by_drug(drug_id) -&gt; int')} "
            f"(lines 43-52).",
            f"{h.c('count_related_patents_by_clinicaltrail(nct_id) -&gt; int')} "
            f"(lines 69-80).",
            f"{h.c('count_related_patents_by_gene(gene) -&gt; int')} (lines 97-108).",
            "Each opens a session, runs a single read transaction "
            f"({h.c('session.begin_transaction()')}), and the inner helper does "
            f"{h.c('tx.run(search, params).single()')}.",
        ]),
        h.p("Cypher &mdash; /count/patents/drugs (lines 248-257)", h.H2),
        h.code(
            "MATCH (n:`drug`)-[r:`disclosed_in`]-(n2:`Patent_Application`)\n"
            "WHERE n.node_id = $drug_id\n"
            "RETURN count(n2) as count"
        ),
        h.p("Cypher &mdash; /count/patents/clinicaltrials (lines 282-291)", h.H2),
        h.code(
            "MATCH (n:`ClinicalTrial`)-[r:`supports_patent_application`]-(n2:`Patent_Application`)\n"
            "WHERE n.nct_id = $nct_id\n"
            "RETURN count(n2) as count"
        ),
        h.p("Cypher &mdash; /count/patents/geneproteins (lines 316-325)", h.H2),
        h.code(
            "MATCH (n:`gene_protein`)-[r:`patent_app_target`]-(n2:`Patent_Application`)\n"
            "WHERE n.node_name = $gene\n"
            "RETURN count(n2) as count"
        ),
        h.p("COUNT semantics worth noting", h.H2),
        *h.bullets([
            f"{h.c('count(n2)')} counts <i>matched rows</i>, not distinct "
            f"{h.c('n2')} nodes. In this schema every "
            f"{h.c('(anchor)-[r]-(Patent_Application)')} edge is one row, so the "
            "number equals the number of edges from the anchor &mdash; which in "
            "practice is the number of distinct patents because the ETL writes "
            "one edge per (anchor, patent) pair. If you ever load duplicate "
            f"edges, the count will be inflated &mdash; use {h.c('count(DISTINCT n2)')} "
            "if you suspect that has happened.",
            f"The relationship is undirected ({h.c('-[r]-')} not "
            f"{h.c('-[r]-&gt;')}); the count is symmetric with respect to edge "
            "direction in Neo4j.",
            f"If the anchor node does not exist, {h.c('count(n2)')} returns "
            f"{h.c('0')} (not null) &mdash; the route returns "
            f"{h.c('{&quot;drug&quot;: ..., &quot;patent_count&quot;: 0}')} "
            "rather than 404. The "
            f"{h.c('result is None')} guard in the helper (e.g. line 241-242) is "
            "defensive; it would only fire if the driver returned no rows at "
            f"all, which {h.c('count(...)')} does not.",
            f"Each helper catches {h.c('(DriverError, Neo4jError)')}, logs, and "
            "re-raises &mdash; Neo4j outages surface as a FastAPI 500.",
            f"Labels and relationship strings are interpolated into the Cypher "
            f"via {h.c('%s')} substitution from "
            f"{h.c('FoundationalNodeEnum.value[1]')} / "
            f"{h.c('FoundationalRelationshipEnum.value[1]')} &mdash; the "
            f"<i>only</i> Cypher parameter is the anchor id "
            f"({h.c('$drug_id')} / {h.c('$nct_id')} / {h.c('$gene')}).",
        ]),
        h.PageBreak(),
    ]

    # ----- 3. response model ----------------------------------------------
    story += [
        h.p("3. Response model &mdash; just a dict", h.H1),
        h.p(
            "Unlike the patent <i>search</i> route (which has a typed "
            f"{h.c('PatentSearchResult')} Pydantic model and a "
            f"{h.c('PatentSearchResultMapper')}) the count route has neither. "
            "Each handler returns a plain Python dict; FastAPI serializes it "
            f"directly. The decorator uses {h.c('response_model_exclude_none=True')} "
            f"but <b>no</b> {h.c('response_model=')} class, so the body shape is "
            "whatever the handler returns.",
        ),
        h.p("Verbatim return statements", h.H2),
        h.code(
            '# patent_count_router.py:46\n'
            'return {"drug": drug_id, "patent_count": count}\n'
            '\n'
            '# patent_count_router.py:64\n'
            'return {"nct_id": nct_id, "patent_count": count}\n'
            '\n'
            '# patent_count_router.py:82\n'
            'return {"gene_protein": gene_protein, "patent_count": count}'
        ),
        h.p("Example JSON", h.H2),
        h.code(
            'GET /count/patents/drugs?drug_id=DB00993\n'
            '  -> { "drug": "DB00993", "patent_count": 17 }\n'
            '\n'
            'GET /count/patents/clinicaltrials?nct_id=NCT05648006\n'
            '  -> { "nct_id": "NCT05648006", "patent_count": 3 }\n'
            '\n'
            'GET /count/patents/geneproteins?gene_protein=ABL1\n'
            '  -> { "gene_protein": "ABL1", "patent_count": 42 }'
        ),
        h.p("Implications", h.H2),
        *h.bullets([
            "The search-key field name differs per route "
            f"({h.c('drug')} vs. {h.c('nct_id')} vs. {h.c('gene_protein')}). "
            "Clients cannot use a single key name to read the echo &mdash; if you "
            "are building a generic UI, branch on the route.",
            f"There is no Pydantic schema in {h.c('src/foundation/model/patent/')} "
            "for this response, and the OpenAPI doc will show only "
            f"{h.c('{}')} (unknown object) for the body. If this becomes "
            f"painful, lift the shape into e.g. "
            f"{h.c('PatentCountResponse(BaseModel)')} and pass "
            f"{h.c('response_model=PatentCountResponse')}.",
            f"Page-math convention: clients divide "
            f"{h.c('patent_count')} by the search route's "
            f"{h.c('page_size')} (max 100) and ceil to get the max page. The "
            f"docstring on {h.c('patent_search_router.py')} page param "
            "calls this endpoint out by reference for exactly that purpose.",
        ]),
        h.PageBreak(),
    ]

    # ----- 4. ETL pointer --------------------------------------------------
    story += [
        h.p("4. ETL pointer &mdash; how the patents get into Neo4j", h.H1),
        h.p(
            "The count routes are read-only; they assume the "
            f"{h.c(':Patent_Application')} nodes and their "
            f"{h.c(':disclosed_in')} / {h.c(':supports_patent_application')} / "
            f"{h.c(':patent_app_target')} edges already exist. The ingest chain "
            "is the USPTO + LLM pipeline already documented in a separate guide.",
        ),
        h.p("Cross-reference", h.H2),
        h.p(
            f"See {h.c('docs/EUGENE_PATENT_FLOW_GUIDE.pdf')} (generated by "
            f"{h.c('generate_patent_flow_guide.py')}) for the full end-to-end "
            "ETL: USPTO bulk-data download, per-application LLM extraction of "
            f"drug/disease/gene mentions, deduplication, and the upsert into "
            f"Neo4j that builds the very subgraph this count route reads. That "
            f"guide also covers seed data and how organizational ownership "
            f"({h.c(':OWNS')} / assignee edges) is layered on after the patents "
            "are loaded.",
        ),
        h.p("Quick orientation", h.H2),
        *h.bullets([
            f"Upstream input: USPTO bulk JSON dumps in "
            f"{h.c('resources/data/patent/')}.",
            f"LLM extraction step produces per-patent assertions linking "
            f"each {h.c(':Patent_Application')} to anchor nodes "
            f"({h.c(':drug')}, {h.c(':ClinicalTrial')}, "
            f"{h.c(':gene_protein')}) by their already-canonical "
            f"{h.c('node_id')}/{h.c('nct_id')}/{h.c('node_name')}.",
            f"Upsert is idempotent via {h.c('MERGE')} on patent number; "
            "re-running the ingest does not double-count.",
            "If the count for a known drug looks low, the likely cause is an "
            "upstream LLM extraction miss, <i>not</i> a bug in this route. "
            "Verify with the Cypher in Section 2 run directly in "
            f"{h.c('cypher-shell')}.",
        ]),
        h.PageBreak(),
    ]

    # ----- 5. debugging walk ----------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Start the service locally: "
            f"{h.c('uvicorn src.eugene_ws:app --reload')}. Confirm Neo4j is up "
            f"({h.c('docker compose ps eugene-neo4j')}) and that the patent "
            f"subgraph is loaded ({h.c('MATCH (p:`Patent_Application`) RETURN count(p);')}).",
            f"Hit each endpoint with curl: "
            f"{h.c('curl &quot;http://localhost:8080/count/patents/drugs?drug_id=DB00993&quot;')}, "
            f"then the {h.c('clinicaltrials')} and {h.c('geneproteins')} variants. "
            f"Expect a JSON dict with {h.c('patent_count')} as an integer.",
            f"Breakpoint at {h.c('patent_count_router.py:45')} (the adapter call). "
            f"Step into "
            f"{h.c('Neo4jPatentQueryAdapter.count_related_patents_by_drug')} "
            f"({h.c('neo4j_patent_query_adapter.py:43')}). Inspect the assembled "
            f"Cypher string at {h.c('neo4j_patent_query_adapter.py:230-247')}.",
            f"Copy that Cypher into {h.c('cypher-shell')} and run with "
            f"{h.c(':param drug_id => &quot;DB00993&quot;')}. The integer must match "
            "the HTTP response. If it does not, the only candidate explanations "
            f"are (a) normalization in "
            f"{h.c('normalize_drug_id')} mutated the id, or (b) you are running "
            "against a different Neo4j instance than the API is.",
            f"Force the validator: "
            f"{h.c('curl &quot;.../count/patents/drugs?drug_id=DB%24000993&quot;')} "
            f"(URL-encoded {h.c('$')}). Expect a 422 from "
            f"{h.c('validate_value')}. Repeat for the clinicaltrials route with "
            f"a missing {h.c('NCT')} prefix; expect a 422 from "
            f"{h.c('validate_clinical_trail_id')}.",
            f"Cross-check with the search route: "
            f"{h.c('curl &quot;.../patents/drugs?drug_id=DB00993&amp;page=1&amp;page_size=100&quot;')} "
            f"and confirm "
            f"{h.c('len(results) == patent_count')} (assuming "
            f"{h.c('patent_count &lt;= 100')}). Divergence indicates a duplicate "
            f"edge or a {h.c('DISTINCT')} mismatch worth investigating.",
        ]),
        h.PageBreak(),
    ]

    # ----- 6. reference index ---------------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Route & wiring\n"
            "  src/eugene_ws.py:49,71            (import + add_routers)\n"
            "  src/foundation/router/patent_count_router.py\n"
            "  src/foundation/router/validate_util.py:35-42  (validate_value)\n"
            "  src/foundation/router/validate_util.py:45-55  (validate_clinical_trail_id)\n"
            "  src/foundation/router/validate_util.py:71-77  (validate_gene_protein)\n"
            "  src/foundation/model/case_helper.py            (normalize_*)\n"
            "  src/foundation/conf/conf.py:199-211            (neo4j_patent_query_adapter)\n"
            "\n"
            "Adapter (Cypher)\n"
            "  src/foundation/infra/db/adapter/neo4j_patent_query_adapter.py\n"
            "    :43-52   count_related_patents_by_drug\n"
            "    :69-80   count_related_patents_by_clinicaltrail\n"
            "    :97-108  count_related_patents_by_gene\n"
            "    :225-257 _count_related_patents_by_drug + Cypher generator\n"
            "    :259-291 _count_related_patents_by_clinicaltrail + Cypher generator\n"
            "    :293-325 _count_related_patents_by_gene + Cypher generator\n"
            "\n"
            "Domain model (labels & rel types)\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "    :10   CLINICAL_TRIAL     = ClinicalTrial\n"
            "    :14   DRUG               = drug\n"
            "    :18   GENE_PROTEIN       = gene_protein\n"
            "    :31   PATENT_APPLICATION = Patent_Application\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "    :25   DISCLOSED_IN                = disclosed_in\n"
            "    :26   SUPPORTS_PATENT_APPLICATION = supports_patent_application\n"
            "    :27   PATENT_APP_TARGET           = patent_app_target\n"
            "\n"
            "Companion search route (same adapter, shares Cypher anchors)\n"
            "  src/foundation/router/patent_search_router.py\n"
            "  src/foundation/mapper/patent_search_result_mapper.py\n"
            "  src/foundation/model/patent/patent_search_result.py\n"
            "  src/foundation/model/patent/patent_and_gene_search_result.py\n"
            "\n"
            "ETL (cross-reference)\n"
            "  docs/EUGENE_PATENT_FLOW_GUIDE.pdf\n"
            "  generate_patent_flow_guide.py\n"
        ),
        h.Spacer(1, 6),
        h.p(
            "<i>End of patent-count route flow guide.</i>",
            h.BODY,
        ),
    ]

    return story
