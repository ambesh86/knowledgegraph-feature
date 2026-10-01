"""Flow-guide section module for Eugene's pubmed-count route.

GET /count/pmids/{drugs,clinicaltrials,geneproteins} - returns a simple
{search_key, pubmed_count} envelope from a Cypher COUNT over the
research/pubmed subgraph. Mirrors the patent_count guide in shape.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_PUBMED_COUNT_FLOW_GUIDE.pdf"
TITLE = "Eugene PubMed Count - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----- cover -----------------------------------------------------------
    story += [
        h.p("Eugene PubMed Count &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP &rarr; module-load DI &rarr; "
            "Neo4j COUNT Cypher &rarr; {search_key, pubmed_count} JSON",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need a file-referenced trace of the pubmed-count "
            "endpoints. These routes are the cheap companions to the full "
            f"{h.c('/pmids/*')} search endpoints &mdash; clients typically call "
            "the count first to size a result set or compute the maximum page "
            "number, then page through the search. Every reference uses the "
            f"form {h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('GET /count/pmids/drugs?drug_id=DB00683')}",
            f"{h.c('GET /count/pmids/clinicaltrials?nct_id=NCT05648006')}",
            f"{h.c('GET /count/pmids/geneproteins?gene_protein=ABL1')}",
        ]),
        h.p(
            f"All three are declared in "
            f"{h.c('src/foundation/router/pubmed_count_router.py')} and registered "
            f"by {h.c('src/eugene_ws.py:51')} (import) and "
            f"{h.c('src/eugene_ws.py:73')} (the includes list inside "
            f"{h.c('add_routers(app)')}).",
        ),
        h.p("Relationship to the pubmed-search route", h.H2),
        h.p(
            f"The count and search routes are wired through <i>different</i> "
            f"adapters in this codebase: "
            f"{h.c('Neo4jPubmedCountAdapter')} for "
            f"{h.c('/count/pmids/*')} and "
            f"{h.c('Neo4jPubmedQueryAdapter')} for "
            f"{h.c('/pmids/*')}. Both factories live in "
            f"{h.c('src/foundation/conf/conf.py')} (lines 209-216 and 219-226) "
            f"and resolve through the shared {h.c('_neo4j_driver()')} singleton, "
            "so they share a connection pool even though the classes differ.",
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Section 0 &mdash; schema (anchor nodes + the rels into "
            f"{h.c(':Research')}). Read first.",
            "Sections 1-3 &mdash; HTTP, Cypher, response shape, top-down.",
            f"Section 4 &mdash; pointers to the PubMed ETL "
            f"({h.c('src/download_pubmed.py')} + "
            f"{h.c('src/link_pubmed_articles.py')}).",
            "Section 5 &mdash; copy-paste debug walk.",
            "Section 6 &mdash; flat reference index.",
        ]),
        h.PageBreak(),
    ]

    # ----- 0. schema -------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "There is a subtle naming gotcha at the heart of this route. The "
            f"node label written into Neo4j for an ingested PubMed article is "
            f"<b>{h.c(':Research')}</b>, not "
            f"{h.c(':pubmed_document')}. The "
            f"{h.c('FoundationalNodeEnum.PUBMED_DOCUMENT')} symbol exists "
            f"({h.c('foundational_node_enum.py:45')}, label "
            f"{h.c('pubmed_document')}) but the count adapter does <i>not</i> "
            f"use it &mdash; it walks "
            f"{h.c('FoundationalNodeEnum.RESEARCH')} "
            f"({h.c('foundational_node_enum.py:33')}, label "
            f"{h.c('Research')}). Anyone wiring up new pubmed reads should "
            "verify which label their data actually carries before writing "
            "Cypher.",
        ),
        h.code(
            "(:drug          { node_id })       -[:featured_in]-               (:Research { pmid })\n"
            "(:gene_protein  { node_name })     -[:analyzed_in]-               (:Research { pmid })\n"
            "(:ClinicalTrial { nct_id  })       -[r]-(:drug|:gene_protein)-[r2]-(:Research { pmid })\n"
            "    # clinical-trial route is a 2-hop variable-rel walk; see Section 2."
        ),
        *h.bullets([
            f"Anchor labels come from {h.c('FoundationalNodeEnum')} in "
            f"{h.c('src/foundation/model/foundational_node_enum.py')}: "
            f"{h.c('DRUG')} (line 14, label {h.c('drug')}), "
            f"{h.c('CLINICAL_TRIAL')} (line 10, label "
            f"{h.c('ClinicalTrial')}), "
            f"{h.c('GENE_PROTEIN')} (line 18, label {h.c('gene_protein')}), "
            f"and {h.c('RESEARCH')} (line 33, label {h.c('Research')}).",
            f"Relationship types come from "
            f"{h.c('FoundationalRelationshipEnum')} in "
            f"{h.c('src/foundation/model/foundational_relationship_enum.py')}: "
            f"{h.c('FEATURED_IN')} (line 28, drug &harr; research) and "
            f"{h.c('ANALYZED_IN')} (line 29, gene &harr; research). The "
            f"clinical-trial Cypher does <b>not</b> name a relationship type at "
            f"all &mdash; it uses an untyped {h.c('-[r]-')} and an "
            f"{h.c('OPTIONAL MATCH')} second hop.",
            f"Anchor keys differ per route: drug anchors on "
            f"{h.c('n.node_id')}, clinical trial on {h.c('start.nct_id')} "
            f"(not {h.c('node_id')}!), and gene/protein on "
            f"{h.c('n.node_name')} (also not {h.c('node_id')}).",
            f"The {h.c(':Research')} node carries a {h.c('pmid')} property "
            f"&mdash; that is what the clinical-trial Cypher counts "
            f"({h.c('count(end.pmid)')}), whereas the drug and gene Cypher "
            f"count node rows ({h.c('count(n2)')}). The numbers are normally "
            "equal because every ingested article has a pmid, but null pmids "
            "would be silently dropped by the clinical-trial form &mdash; not "
            "by the other two.",
            f"Like the rest of Eugene there are no Neo4j CREATE CONSTRAINTs; "
            f"uniqueness of {h.c('pmid')} is by ETL convention "
            f"({h.c('MERGE')} on the article during ingest), not enforced by "
            "the DB.",
        ]),
        h.PageBreak(),
    ]

    # ----- 1. HTTP entry ---------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:51')} imports the module as "
            f"{h.c('pubmed_count_router')}; "
            f"{h.c('src/eugene_ws.py:73')} adds it to the includes list inside "
            f"{h.c('add_routers(app)')}. The module-level "
            f"{h.c('router = APIRouter(prefix=&quot;/count/pmids&quot;, tags=[&quot;pubmed&quot;])')} "
            f"({h.c('pubmed_count_router.py:23-26')}) means the final paths "
            f"are {h.c('/count/pmids/drugs')}, "
            f"{h.c('/count/pmids/clinicaltrials')}, and "
            f"{h.c('/count/pmids/geneproteins')}.",
        ),
        h.p("Module-load dependency injection", h.H2),
        h.p(f"{h.c('src/foundation/router/pubmed_count_router.py:28')}", h.PATH),
        h.code(
            "count_adapter = neo4j_pubmed_count_adapter()"
        ),
        h.p(
            f"The DI factory at {h.c('src/foundation/conf/conf.py:209-216')} "
            f"resolves to a {h.c('Neo4jPubmedCountAdapter')} bound to the "
            f"shared {h.c('_neo4j_driver()')} singleton. Resolution happens at "
            "<b>module load time</b>, not per request &mdash; one instance is "
            f"reused for the life of the process.",
        ),
        h.p("Endpoint signatures", h.H2),
        h.code(
            '@router.get("/drugs",          response_model_exclude_none=True)   # line 31\n'
            'async def count_related_pubmed_docs_by_drug_id(drug_id):\n'
            '\n'
            '@router.get("/clinicaltrials", response_model_exclude_none=True)   # line 49\n'
            'async def count_related_pubmed_docs_by_clinicaltrial_id(nct_id):\n'
            '\n'
            '@router.get("/geneproteins",   response_model_exclude_none=True)   # line 67\n'
            'async def count_related_pubmed_docs_by_geneprotein_id(gene_protein):'
        ),
        h.p("Query params &amp; validators", h.H2),
        *h.bullets([
            f"{h.c('drug_id')} (lines 33-42) &mdash; "
            f"{h.c('Query(example=&quot;DB00683&quot;, max_length=64, min_length=1)')} "
            f"+ {h.c('AfterValidator(validate_value)')}. "
            f"{h.c('validate_value')} "
            f"({h.c('validate_util.py:35-42')}) rejects any of "
            f"{h.c('% _ $ ; : ^ *')}. Note: it does <i>not</i> enforce the "
            f"{h.c('DB')} prefix &mdash; the stricter "
            f"{h.c('validate_drug_id')} (lines 58-68) is not used here.",
            f"{h.c('nct_id')} (lines 51-60) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_clinical_trail_id)')} "
            f"({h.c('validate_util.py:45-55')}), which delegates to "
            f"{h.c('validate_value')} <i>and</i> additionally requires the "
            f"{h.c('NCT')} prefix (case-insensitive).",
            f"{h.c('gene_protein')} (lines 69-78) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_gene_protein)')} "
            f"({h.c('validate_util.py:71-77')}); same special-char check, no "
            "prefix requirement.",
            "All three routes <b>require</b> their query parameter (no "
            "defaults); Pydantic returns a 422 if missing.",
        ]),
        h.p("Normalization", h.H2),
        h.p(
            f"Each handler calls the matching {h.c('case_helper')} normalizer "
            f"before hitting the adapter: {h.c('normalize_drug_id(drug_id)')} "
            f"(line 44), {h.c('normalize_clinical_trial_id(nct_id)')} "
            f"(line 62), and "
            f"{h.c('normalize_gene_protein(gene_protein)')} (line 80). All "
            f"three live in {h.c('src/foundation/model/case_helper.py')}; they "
            f"exist so casing on the wire (e.g. {h.c('db00683')} vs. "
            f"{h.c('DB00683')}, or {h.c('abl1')} vs. {h.c('ABL1')}) does not "
            "miss the Neo4j anchor.",
        ),
        h.p("<b>First breakpoint:</b> pubmed_count_router.py:45, 63, or 81 (the adapter call)."),
        h.PageBreak(),
    ]

    # ----- 2. adapter Cypher ----------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the COUNT Cypher", h.H1),
        h.p(
            f"{h.c('Neo4jPubmedCountAdapter')} lives at "
            f"{h.c('src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py')}. "
            "Each count entry point opens a session, begins a transaction, "
            "calls the matching private helper, and returns the integer.",
        ),
        h.p("Public entry points", h.H2),
        *h.bullets([
            f"{h.c('count_related_pubmed_by_drug(drug_id) -&gt; int')} "
            f"(lines 25-34).",
            f"{h.c('count_related_pubmed_by_clinicaltrail(nct_id) -&gt; int')} "
            f"(lines 36-47). Note the misspelling &mdash; "
            f"{h.c('clinicaltrail')} not {h.c('clinicaltrial')}. The handler "
            f"({h.c('pubmed_count_router.py:63')}) calls it by that name; do "
            "not silently rename it.",
            f"{h.c('count_related_pubmed_by_gene(gene) -&gt; int')} "
            f"(lines 49-58).",
            f"All three are decorated with {h.c('@log_time')} "
            f"({h.c('annotation.timer_annotation')}) so the elapsed query "
            "time appears in the logs at INFO.",
            f"Each helper does {h.c('ensure_connection(self.driver)')} "
            f"({h.c('graph/util/util.py')}) before opening a session &mdash; a "
            "stale driver surfaces here rather than inside the transaction.",
            f"Each inner helper catches {h.c('(DriverError, Neo4jError)')}, "
            "logs, and re-raises &mdash; Neo4j outages surface as a FastAPI "
            "500.",
        ]),
        h.p("Cypher &mdash; /count/pmids/drugs (lines 83-92)", h.H2),
        h.code(
            "MATCH (n:`drug`)-[r:`featured_in`]-(n2:`Research`)\n"
            "WHERE n.node_id = $drug_id\n"
            "RETURN count(n2) as count"
        ),
        h.p("Cypher &mdash; /count/pmids/clinicaltrials (lines 117-128)", h.H2),
        h.code(
            "MATCH (start:`ClinicalTrial`)-[r]-(target:`drug`|`gene_protein`)\n"
            "WHERE start.nct_id = $nct_id\n"
            "OPTIONAL MATCH (target)-[r2]-(end:`Research`)\n"
            "RETURN count(end.pmid) as count"
        ),
        h.p("Cypher &mdash; /count/pmids/geneproteins (lines 153-162)", h.H2),
        h.code(
            "MATCH (n:`gene_protein`)-[r:`analyzed_in`]-(n2:`Research`)\n"
            "WHERE n.node_name = $gene\n"
            "RETURN count(n2) as count"
        ),
        h.p("COUNT semantics worth noting", h.H2),
        *h.bullets([
            f"The drug and gene Cypher use {h.c('count(n2)')} &mdash; this "
            "counts <i>matched rows</i>, not distinct nodes. In this schema "
            f"every {h.c('(anchor)-[r]-(:Research)')} edge is one row, so the "
            "number equals the number of edges from the anchor, which equals "
            "the number of related articles assuming the ETL writes one edge "
            "per (anchor, pmid) pair. Duplicate edges would inflate the "
            f"count; use {h.c('count(DISTINCT n2)')} if you suspect that.",
            f"The clinical-trial Cypher counts {h.c('end.pmid')}, not "
            f"{h.c('end')}. With {h.c('OPTIONAL MATCH')} a missing second hop "
            f"produces a row whose {h.c('end')} is null and whose "
            f"{h.c('end.pmid')} is null, and {h.c('count(end.pmid)')} skips "
            f"nulls. Net effect: trials that match a drug/gene but whose "
            f"drug/gene has no {h.c(':Research')} neighbour contribute 0, not "
            f"1, to the count. Switching to {h.c('count(end)')} would over-"
            "report.",
            f"None of the three Cypher matches are <i>distinct</i> on the "
            f"final node. The two-hop clinical-trial walk can therefore "
            f"double-count an article that is reachable via both a drug and a "
            f"gene attached to the same trial. If exact distinct-article "
            f"counts ever matter, switch to "
            f"{h.c('count(DISTINCT end.pmid)')}.",
            f"All relationship matches are undirected ({h.c('-[r]-')} not "
            f"{h.c('-[r]-&gt;')}). Direction in the graph does not change the "
            "answer.",
            f"If the anchor node does not exist, {h.c('count(...)')} returns "
            f"{h.c('0')} (not null) &mdash; the route returns "
            f"{h.c('{&quot;drug&quot;: ..., &quot;pubmed_count&quot;: 0}')} "
            f"rather than 404. The {h.c('result is None')} guard in each "
            f"helper (e.g. lines 76-77, 110-111, 146-147) is defensive; it "
            f"would only fire if {h.c('tx.run(...).single()')} returned no "
            f"row at all, which {h.c('count(...)')} does not.",
            f"Labels and relationship strings are interpolated into the "
            f"Cypher via {h.c('%s')} substitution from "
            f"{h.c('FoundationalNodeEnum.value[1]')} / "
            f"{h.c('FoundationalRelationshipEnum.value[1]')} &mdash; the "
            f"<i>only</i> Cypher parameters are the anchor ids "
            f"({h.c('$drug_id')} / {h.c('$nct_id')} / {h.c('$gene')}).",
        ]),
        h.PageBreak(),
    ]

    # ----- 3. response model ----------------------------------------------
    story += [
        h.p("3. Response model &mdash; just a dict", h.H1),
        h.p(
            "Like the patent-count route, this endpoint has no Pydantic "
            f"response model and no mapper. Each handler returns a plain "
            f"Python dict; FastAPI serializes it directly. The decorator uses "
            f"{h.c('response_model_exclude_none=True')} but <b>no</b> "
            f"{h.c('response_model=')} class, so the body shape is whatever "
            "the handler returns.",
        ),
        h.p("Verbatim return statements", h.H2),
        h.code(
            '# pubmed_count_router.py:46\n'
            'return {"drug": drug_id, "pubmed_count": count}\n'
            '\n'
            '# pubmed_count_router.py:64\n'
            'return {"nct_id": nct_id, "pubmed_count": count}\n'
            '\n'
            '# pubmed_count_router.py:82\n'
            'return {"gene_protein": gene_protein, "pubmed_count": count}'
        ),
        h.p("Example JSON", h.H2),
        h.code(
            'GET /count/pmids/drugs?drug_id=DB00683\n'
            '  -> { "drug": "DB00683", "pubmed_count": 128 }\n'
            '\n'
            'GET /count/pmids/clinicaltrials?nct_id=NCT05648006\n'
            '  -> { "nct_id": "NCT05648006", "pubmed_count": 7 }\n'
            '\n'
            'GET /count/pmids/geneproteins?gene_protein=ABL1\n'
            '  -> { "gene_protein": "ABL1", "pubmed_count": 312 }'
        ),
        h.p("Implications", h.H2),
        *h.bullets([
            "The search-key field name differs per route "
            f"({h.c('drug')} vs. {h.c('nct_id')} vs. "
            f"{h.c('gene_protein')}). Clients cannot use a single key name "
            "to read back the echoed anchor &mdash; if you are building a "
            "generic UI, branch on the route.",
            f"There is no Pydantic schema for this response, and the OpenAPI "
            f"doc will show only {h.c('{}')} (unknown object) for the body. "
            f"If this becomes painful, lift the shape into e.g. "
            f"{h.c('PubmedCountResponse(BaseModel)')} and pass "
            f"{h.c('response_model=PubmedCountResponse')}.",
            f"Page-math convention: clients divide {h.c('pubmed_count')} by "
            f"the search route's {h.c('page_size')} (max 100) and ceil to "
            f"get the max page for {h.c('/pmids/*')} requests.",
        ]),
        h.PageBreak(),
    ]

    # ----- 4. ETL pointer --------------------------------------------------
    story += [
        h.p("4. ETL &mdash; how the PubMed nodes get into Neo4j", h.H1),
        h.p(
            "The count routes are read-only; they assume that "
            f"{h.c(':Research')} nodes (with a {h.c('pmid')} property) and "
            f"the {h.c(':featured_in')} / {h.c(':analyzed_in')} edges to "
            f"{h.c(':drug')} and {h.c(':gene_protein')} anchors already "
            "exist. The ingest is a two-stage CLI pipeline that this guide "
            "intentionally <i>references</i> rather than re-derives &mdash; "
            "the full PubMed PDF/LLM extraction pipeline deserves its own "
            "guide.",
        ),
        h.p("Stage 1 &mdash; download", h.H2),
        h.p(f"{h.c('src/download_pubmed.py')}", h.PATH),
        h.p(
            "CLI entry point that pulls PubMed/PMC articles to disk under "
            f"{h.c('resources/data/pubmed/')} (PDFs by default). Wires "
            f"together a downloader and dotenv config. This stage does not "
            "touch Neo4j &mdash; it produces files for the linker stage to "
            "process.",
        ),
        h.p("Stage 2 &mdash; link", h.H2),
        h.p(f"{h.c('src/link_pubmed_articles.py')}", h.PATH),
        h.p(
            "CLI entry point that turns the downloaded articles into Neo4j "
            f"nodes and edges. Two modes:",
        ),
        *h.bullets([
            f"<b>From disk</b> &mdash; default. Reads PDFs from "
            f"{h.c('resources/data/pubmed/')}, runs LLM extraction to find "
            f"drug/gene mentions, and merges {h.c(':Research')} nodes "
            f"linked to existing canonical {h.c(':drug')} / "
            f"{h.c(':gene_protein')} anchors.",
            f"<b>From checkpoints</b> &mdash; "
            f"{h.c('--use-checkpoints')} flag; replays pre-processed JSON "
            f"under {h.c('output/')}. Useful for iterating on the Neo4j "
            "upsert without re-running the LLM.",
            f"Both modes go through "
            f"{h.c('eugene_graph_summary_orchestrator()')} "
            f"(DI in {h.c('graph/conf/conf.py')}); the underlying writes "
            f"use {h.c('MERGE')} on {h.c('Research.pmid')} so re-runs are "
            "idempotent.",
        ]),
        h.p("Quick orientation", h.H2),
        *h.bullets([
            f"If the count for a known drug looks low, the likely cause is "
            f"an upstream LLM extraction miss in {h.c('link_pubmed_articles.py')}, "
            "<i>not</i> a bug in this route. Verify with the Cypher in "
            f"Section 2 run directly in {h.c('cypher-shell')}.",
            f"If the count is zero for <i>every</i> drug, suspect either an "
            f"empty {h.c(':Research')} table or a missing "
            f"{h.c(':featured_in')} edge type. "
            f"{h.c('MATCH (r:`Research`) RETURN count(r);')} is the first "
            "diagnostic; "
            f"{h.c('MATCH ()-[r:`featured_in`]-() RETURN count(r);')} is the "
            "second.",
            f"Clinical-trial counts depend on the trial having at least one "
            f"{h.c(':drug')} or {h.c(':gene_protein')} neighbour with "
            f"{h.c(':Research')} fan-out. Trials with neither will always "
            "report 0 &mdash; this is by design.",
        ]),
        h.PageBreak(),
    ]

    # ----- 5. debugging walk ----------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Start the service locally: "
            f"{h.c('uvicorn src.eugene_ws:app --reload')}. Confirm Neo4j is "
            f"up ({h.c('docker compose ps eugene-neo4j')}) and that the "
            f"pubmed subgraph is loaded "
            f"({h.c('MATCH (r:`Research`) RETURN count(r);')}).",
            f"Hit each endpoint with curl: "
            f"{h.c('curl &quot;http://localhost:8080/count/pmids/drugs?drug_id=DB00683&quot;')}, "
            f"then the {h.c('clinicaltrials')} and {h.c('geneproteins')} "
            f"variants. Expect a JSON dict with {h.c('pubmed_count')} as an "
            "integer.",
            f"Breakpoint at {h.c('pubmed_count_router.py:45')} (the drug "
            "adapter call). Step into "
            f"{h.c('Neo4jPubmedCountAdapter.count_related_pubmed_by_drug')} "
            f"({h.c('neo4j_pubmed_count_adapter.py:26')}). Inspect the "
            f"assembled Cypher string at "
            f"{h.c('neo4j_pubmed_count_adapter.py:83-92')} &mdash; copy it "
            f"into {h.c('cypher-shell')} with "
            f"{h.c(':param drug_id =&gt; &quot;DB00683&quot;')} and the "
            "integer must match the HTTP response.",
            f"Force the validator: "
            f"{h.c('curl &quot;.../count/pmids/drugs?drug_id=DB%24000683&quot;')} "
            f"(URL-encoded {h.c('$')}). Expect a 422 from "
            f"{h.c('validate_value')}. Repeat for the clinicaltrials route "
            f"with a missing {h.c('NCT')} prefix; expect a 422 from "
            f"{h.c('validate_clinical_trail_id')}.",
            f"Cross-check the clinical-trial two-hop count: run the Cypher "
            f"at {h.c('neo4j_pubmed_count_adapter.py:117-128')} directly, "
            f"then re-run it with {h.c('count(end.pmid)')} swapped to "
            f"{h.c('count(DISTINCT end.pmid)')}. A divergence means the "
            f"trial is reachable to the same article through both a "
            f"{h.c(':drug')} and a {h.c(':gene_protein')} &mdash; expected "
            "in a well-populated graph, and worth knowing before clients "
            "compare counts across routes.",
            f"Suspect a label confusion? Confirm the actual labels in your "
            f"Neo4j with "
            f"{h.c('CALL db.labels() YIELD label WHERE label CONTAINS &quot;esearch&quot; OR label CONTAINS &quot;ubmed&quot; RETURN label;')} "
            f"&mdash; you should see {h.c('Research')} and possibly "
            f"{h.c('pubmed_document')} if older ingest data is still "
            "present. The count adapter only reads "
            f"{h.c(':Research')}.",
        ]),
        h.PageBreak(),
    ]

    # ----- 6. reference index ---------------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Route & wiring\n"
            "  src/eugene_ws.py:51,73            (import + add_routers)\n"
            "  src/foundation/router/pubmed_count_router.py\n"
            "  src/foundation/router/validate_util.py:35-42  (validate_value)\n"
            "  src/foundation/router/validate_util.py:45-55  (validate_clinical_trail_id)\n"
            "  src/foundation/router/validate_util.py:71-77  (validate_gene_protein)\n"
            "  src/foundation/model/case_helper.py            (normalize_*)\n"
            "  src/foundation/conf/conf.py:209-216            (neo4j_pubmed_count_adapter)\n"
            "  src/foundation/conf/conf.py:219-226            (neo4j_pubmed_query_adapter - companion)\n"
            "\n"
            "Adapter (Cypher)\n"
            "  src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py\n"
            "    :25-34   count_related_pubmed_by_drug\n"
            "    :36-47   count_related_pubmed_by_clinicaltrail\n"
            "    :49-58   count_related_pubmed_by_gene\n"
            "    :60-82   _count_related_pubmed_by_drug      (executor)\n"
            "    :83-92   _generate_pubmed_count_by_drug_id  (Cypher)\n"
            "    :94-115  _count_related_pubmed_by_clinicaltrail\n"
            "    :117-128 _generate_pubmed_count_by_clinicaltrail\n"
            "    :130-151 _count_related_pubmed_by_gene\n"
            "    :153-162 _generate_pubmed_count_by_gene\n"
            "\n"
            "Response\n"
            "  (no Pydantic model, no mapper - plain dict returned by handlers)\n"
            "  src/foundation/router/pubmed_count_router.py:46,64,82\n"
            "\n"
            "Domain model (labels & rel types)\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "    :10   CLINICAL_TRIAL     = ClinicalTrial\n"
            "    :14   DRUG               = drug\n"
            "    :18   GENE_PROTEIN       = gene_protein\n"
            "    :33   RESEARCH           = Research            <-- the pubmed node\n"
            "    :45   PUBMED_DOCUMENT    = pubmed_document     (defined but unused by this route)\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "    :28   FEATURED_IN        = featured_in         (drug <-> Research)\n"
            "    :29   ANALYZED_IN        = analyzed_in         (gene <-> Research)\n"
            "\n"
            "Companion search route (different adapter, same driver pool)\n"
            "  src/foundation/router/pubmed_search_router.py\n"
            "  src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py\n"
            "  src/foundation/mapper/pubmed_search_result_mapper.py\n"
            "\n"
            "ETL (cross-reference)\n"
            "  src/download_pubmed.py            (stage 1: download PDFs to disk)\n"
            "  src/link_pubmed_articles.py       (stage 2: LLM extract + Neo4j upsert)\n"
            "  graph/conf/conf.py                (eugene_graph_summary_orchestrator factory)\n"
        ),
        h.Spacer(1, 6),
        h.p(
            "<i>End of pubmed-count route flow guide.</i>",
            h.BODY,
        ),
    ]

    return story
