"""Flow-guide section module for Eugene's pubmed-search route.

GET /pmids/{drugs,clinicaltrials,geneproteins} - returns a paginated
list of related PMIDs from a Cypher MATCH over the Research subgraph
the link_pubmed_articles ETL builds. This guide mirrors the patent
search guide in shape since both are paginated search routes built on
the same module-load DI + Neo4j adapter + Pydantic-mapper template.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_PUBMED_SEARCH_FLOW_GUIDE.pdf"
TITLE = "Eugene PubMed Search - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----- cover -----------------------------------------------------------
    story += [
        h.p("Eugene PubMed Search &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP &rarr; module-load DI &rarr; "
            "Neo4j paginated Cypher &rarr; PubmedSearchResult JSON "
            "&rarr; upstream NCBI download + LLM extraction ETL",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need a file-referenced trace of the PubMed "
            "search endpoints. These routes are the paginated companions "
            f"to {h.c('/count/pmids/*')} &mdash; clients call the count "
            "endpoint first to compute the maximum page number, then page "
            "through this endpoint. Every reference uses the form "
            f"{h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            f"{h.c('GET /pmids/drugs?drug_id=DB00683&amp;page=1&amp;page_size=50')}",
            f"{h.c('GET /pmids/clinicaltrials?nct_id=NCT00000122&amp;page=1&amp;page_size=50')}",
            f"{h.c('GET /pmids/geneproteins?gene_protein=PDE3A&amp;page=1&amp;page_size=50')}",
        ]),
        h.p(
            f"All three are declared in "
            f"{h.c('src/foundation/router/pubmed_search_router.py')} and "
            f"registered by {h.c('src/eugene_ws.py:50')} / "
            f"{h.c('src/eugene_ws.py:72')} inside "
            f"{h.c('add_routers(app)')}.",
        ),
        h.p("Relationship to the pubmed-count route", h.H2),
        h.p(
            f"The search routes share the {h.c('Neo4jPubmedQueryAdapter')} "
            f"singleton only conceptually with the count route &mdash; the "
            f"count route uses a separate {h.c('Neo4jPubmedCountAdapter')} "
            f"({h.c('conf.py:209-216')}) while this route uses "
            f"{h.c('Neo4jPubmedQueryAdapter')} ({h.c('conf.py:219-226')}). "
            "Both adapters walk the same edges with the same anchors; the "
            f"search route adds {h.c('SKIP/LIMIT')} pagination and projects "
            f"{h.c('pmid')} instead of {h.c('count(*)')}. If the count "
            "returns 137 PMIDs for a drug, paging this route with "
            f"{h.c('page_size=50')} yields 50 / 50 / 37 across three pages.",
        ),
        h.p("How to read this guide", h.H2),
        *h.bullets([
            "Section 0 &mdash; schema (node labels + edge types the Cypher uses). Read first.",
            "Sections 1-3 &mdash; HTTP, Cypher, response shape, top-down.",
            "Section 4 &mdash; ETL: NCBI fetch + PDF download + LLM-driven graph link step.",
            "Section 5 &mdash; copy-paste debug walk.",
            "Section 6 &mdash; flat reference index.",
        ]),
        h.PageBreak(),
    ]

    # ----- 0. schema -------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "The pubmed-search routes anchor on one of three node types "
            f"and traverse to a {h.c(':Research')} node carrying a "
            f"{h.c('pmid')} property. The drug + gene_protein variants are "
            "a single labeled hop; the clinical trial variant is a "
            "two-hop traversal because the graph does not store a direct "
            "ClinicalTrial -&gt; Research edge.",
        ),
        h.code(
            "(:drug         { node_id })   -[:featured_in]-              (:Research { pmid })\n"
            "(:gene_protein { node_name }) -[:analyzed_in]-              (:Research { pmid })\n"
            "\n"
            "(:ClinicalTrial { nct_id })   -[ANY]-(:drug | :gene_protein) -[ANY]- (:Research { pmid })"
        ),
        *h.bullets([
            f"Node labels come from {h.c('FoundationalNodeEnum')} in "
            f"{h.c('src/foundation/model/foundational_node_enum.py')}: "
            f"{h.c('DRUG')} (line 14, label {h.c('drug')}), "
            f"{h.c('CLINICAL_TRIAL')} (line 10, label "
            f"{h.c('ClinicalTrial')}), "
            f"{h.c('GENE_PROTEIN')} (line 18, label "
            f"{h.c('gene_protein')}), and {h.c('RESEARCH')} (line 33, "
            f"label {h.c('Research')}). Note the mixed case &mdash; "
            f"{h.c('Research')} and {h.c('ClinicalTrial')} keep PascalCase "
            "in Neo4j, the rest are lowercase.",
            f"Relationship types come from "
            f"{h.c('FoundationalRelationshipEnum')} in "
            f"{h.c('src/foundation/model/foundational_relationship_enum.py')}: "
            f"{h.c('FEATURED_IN')} (line 28, type {h.c('featured_in')}) "
            f"and {h.c('ANALYZED_IN')} (line 29, type "
            f"{h.c('analyzed_in')}). The clinical-trial Cypher uses an "
            f"<i>unlabeled</i> relationship pattern ({h.c('-[r]-')}) on "
            "both hops &mdash; any edge type is accepted.",
            f"Anchor keys differ per route: drug anchors on "
            f"{h.c('n.node_id')}, clinical trial on {h.c('start.nct_id')} "
            f"(not {h.c('node_id')}!), and gene/protein on "
            f"{h.c('n.node_name')} (also not {h.c('node_id')}).",
            f"The pmid property lives on {h.c(':Research')} as "
            f"{h.c('n2.pmid')} / {h.c('end.pmid')}; the drug + gene routes "
            f"project it directly, the clinical-trial route projects it "
            f"as {h.c('end.pmid')} after the second hop.",
            f"Edges are all <b>undirected</b> in the Cypher "
            f"({h.c('-[r:`featured_in`]-')} not "
            f"{h.c('-[r:`featured_in`]-&gt;')}); the search is symmetric "
            "with respect to direction in the graph.",
            "Like the rest of Eugene there are no Neo4j CREATE "
            "CONSTRAINTs; uniqueness of pmid is by ETL convention, not "
            "enforced at the DB layer.",
        ]),
        h.PageBreak(),
    ]

    # ----- 1. HTTP entry ---------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; the FastAPI router", h.H1),
        h.p("Wiring", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:50')} imports the module as "
            f"{h.c('pubmed_search_router')}; "
            f"{h.c('src/eugene_ws.py:72')} adds it to the includes list "
            f"inside {h.c('add_routers(app)')}. The module-level "
            f"{h.c('router = APIRouter(prefix=&quot;/pmids&quot;, tags=[&quot;pubmed&quot;])')} "
            f"({h.c('pubmed_search_router.py:29-32')}) means the final "
            f"paths are {h.c('/pmids/drugs')}, "
            f"{h.c('/pmids/clinicaltrials')}, and "
            f"{h.c('/pmids/geneproteins')}.",
        ),
        h.p("Module-load dependency injection", h.H2),
        h.p(f"{h.c('src/foundation/router/pubmed_search_router.py:34-35')}", h.PATH),
        h.code(
            "query_adapter         = neo4j_pubmed_query_adapter()\n"
            "search_result_mapper  = pubmed_search_result_mapper()"
        ),
        h.p(
            f"The DI factories at "
            f"{h.c('src/foundation/conf/conf.py:219-226')} "
            f"({h.c('neo4j_pubmed_query_adapter')}) and "
            f"{h.c('src/foundation/conf/conf.py:271-272')} "
            f"({h.c('pubmed_search_result_mapper')}) resolve to fresh "
            f"instances bound to the shared {h.c('_neo4j_driver()')} "
            "singleton. There is no caching layer between FastAPI and the "
            "adapter &mdash; every HTTP request goes to Neo4j.",
        ),
        h.p("Endpoint signatures", h.H2),
        h.code(
            '@router.get("/drugs",          response_model=PubmedSearchResult)         # line 38\n'
            'async def find_related_pubmed_docs_by_drug_id(drug_id, page, page_size):\n'
            '\n'
            '@router.get("/clinicaltrials", response_model=PubmedSearchResult)         # line 79\n'
            'async def find_related_pubmed_docs_by_clinicaltrial_id(nct_id, page, page_size):\n'
            '\n'
            '@router.get("/geneproteins",   response_model=PubmedAndGeneSearchResult)  # line 122\n'
            'async def find_related_pubmed_docs_by_geneprotein_id(gene_protein, page, page_size):'
        ),
        h.p("Query params &amp; validators", h.H2),
        *h.bullets([
            f"{h.c('drug_id')} (lines 44-53) &mdash; "
            f"{h.c('Query(example=&quot;DB00683&quot;, max_length=64, min_length=1)')} "
            f"+ {h.c('AfterValidator(validate_value)')}. "
            f"{h.c('validate_value')} ({h.c('validate_util.py:35-42')}) "
            f"rejects any of {h.c('% _ $ ; : ^ *')}. Note: it does "
            f"<i>not</i> enforce the {h.c('DB')} prefix &mdash; that "
            f"stricter check lives in {h.c('validate_drug_id')} "
            "(lines 58-68) which this route does not use.",
            f"{h.c('nct_id')} (lines 85-94) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_clinical_trail_id)')} "
            f"({h.c('validate_util.py:45-55')}), which delegates to "
            f"{h.c('validate_value')} <i>and</i> additionally requires "
            f"the {h.c('NCT')} prefix (case-insensitive via "
            f"{h.c('id.upper().startswith(&quot;NCT&quot;)')}).",
            f"{h.c('gene_protein')} (lines 128-137) &mdash; "
            f"{h.c('max_length=24, min_length=1')} + "
            f"{h.c('AfterValidator(validate_gene_protein)')} "
            f"({h.c('validate_util.py:71-77')}); same special-char check, "
            "no prefix requirement.",
            f"{h.c('page')} &mdash; required, {h.c('gt=0')}. "
            f"{h.c('page_size')} &mdash; required, {h.c('gt=0, le=100')}. "
            f"Pydantic returns a 422 if missing or out of range; clients "
            f"are expected to read the max page from the "
            f"{h.c('/count/pmids/*')} endpoints.",
        ]),
        h.p("Normalization", h.H2),
        h.p(
            f"Each handler calls the matching {h.c('case_helper')} "
            f"normalizer before hitting the adapter: "
            f"{h.c('normalize_drug_id(drug_id)')} (line 72), "
            f"{h.c('normalize_clinical_trial_id(nct_id)')} (line 113), "
            f"and {h.c('normalize_gene_protein(gene_protein)')} "
            f"(line 156). All three live in "
            f"{h.c('src/foundation/model/case_helper.py')} and are "
            f"identical &mdash; each delegates to "
            f"{h.c('_normalize_upper')} which uppercases the value. "
            f"Casing on the wire (e.g. {h.c('db00683')} vs. "
            f"{h.c('DB00683')}, {h.c('pde3a')} vs. {h.c('PDE3A')}) does "
            "not miss the Neo4j anchor.",
        ),
        h.p("<b>First breakpoint:</b> pubmed_search_router.py:73, 114, or 157 (the adapter call)."),
        h.PageBreak(),
    ]

    # ----- 2. adapter Cypher ----------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the paginated Cypher", h.H1),
        h.p(
            f"{h.c('Neo4jPubmedQueryAdapter')} lives at "
            f"{h.c('src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py')}. "
            "Each search entry point opens a session, begins a "
            "transaction, calls the matching private helper, and returns "
            f"a pandas {h.c('DataFrame')} (via "
            f"{h.c('tx.run(...).to_df()')}).",
        ),
        h.p("Public entry points", h.H2),
        *h.bullets([
            f"{h.c('find_related_pubmed_by_drug(drug_id, page, page_size)')} "
            "(lines 27-40).",
            f"{h.c('find_related_pubmed_by_clinicaltrail(nct_id, page, page_size)')} "
            "(lines 42-55).",
            f"{h.c('find_related_pubmed_by_gene(gene, page, page_size)')} "
            "(lines 57-70).",
            f"All three call {h.c('ensure_connection(self.driver)')} "
            "(reconnect-on-failure helper from graph.util.util), open a "
            f"session, run a single transaction "
            f"({h.c('session.begin_transaction()')}), and the inner "
            f"helper does {h.c('tx.run(search, params).to_df()')}.",
            f"Pagination is computed by "
            f"{h.c('Pagination.calculate_limit_and_offset(page, page_size)')} "
            f"from {h.c('foundation/infra/db/util/pagination.py')}; the "
            f"resulting integers are interpolated into the Cypher via "
            f"{h.c('%s')} (not bound parameters).",
        ]),
        h.p("Cypher &mdash; /pmids/drugs (lines 95-108)", h.H2),
        h.code(
            "MATCH (n:`drug`)-[r:`featured_in`]-(n2:`Research`)\n"
            "WHERE n.node_id = $drug_id\n"
            "RETURN n.node_id as drug_id, n.node_name as drug_name, n2.pmid as pmid\n"
            "ORDER BY pmid DESC\n"
            "SKIP {offset}\n"
            "LIMIT {limit}"
        ),
        h.p("Cypher &mdash; /pmids/clinicaltrials (lines 137-152)", h.H2),
        h.code(
            "MATCH (start:`ClinicalTrial`)-[r]-(target:`drug`|`gene_protein`)\n"
            "WHERE start.nct_id = $nct_id\n"
            "OPTIONAL MATCH (target)-[r2]-(end:`Research`)\n"
            "RETURN start.nct_id as nct_id, target.node_id as target_id, end.pmid as pmid\n"
            "ORDER BY nct_id, target_id, pmid DESC\n"
            "SKIP {offset}\n"
            "LIMIT {limit}"
        ),
        h.p("Cypher &mdash; /pmids/geneproteins (lines 177-190)", h.H2),
        h.code(
            "MATCH (n:`gene_protein`)-[r:`analyzed_in`]-(n2:`Research`)\n"
            "WHERE n.node_name = $gene\n"
            "RETURN n.node_name as node_name, n2.pmid as pmid\n"
            "ORDER BY pmid DESC\n"
            "SKIP {offset}\n"
            "LIMIT {limit}"
        ),
        h.p("Pagination and ordering semantics worth noting", h.H2),
        *h.bullets([
            f"Ordering is by {h.c('pmid DESC')} (a lexicographic string "
            "sort, not numeric) for the drug and gene routes. PMIDs "
            "happen to be numeric strings of similar length so the "
            "ordering looks newest-first in practice, but a 7-digit pmid "
            "will sort before an 8-digit one of higher numeric value. If "
            f"ordering correctness matters, cast: "
            f"{h.c('ORDER BY toInteger(n2.pmid) DESC')}.",
            f"The clinical-trial route additionally orders by "
            f"{h.c('nct_id, target_id')} before {h.c('pmid DESC')} "
            "&mdash; this groups results by intermediate target before "
            "pmid, which means paginating a single nct_id can interleave "
            "PMIDs from different drugs/genes within the same page.",
            f"The clinical-trial route uses {h.c('OPTIONAL MATCH')} on "
            f"the second hop and projects {h.c('end.pmid')}; if a "
            f"matched {h.c('target')} has no linked "
            f"{h.c(':Research')} node the row still appears with "
            f"{h.c('pmid = null')}. The mapper filters those out (see "
            f"Section 3, {h.c('_to_row')}).",
            f"{h.c('SKIP')} and {h.c('LIMIT')} are <b>integers "
            f"interpolated into the Cypher string</b> &mdash; the only "
            f"bound parameter is the anchor id "
            f"({h.c('$drug_id')} / {h.c('$nct_id')} / {h.c('$gene')}). "
            "FastAPI's range constraints "
            f"({h.c('gt=0, le=100')}) plus Pagination's integer math "
            "make this safe.",
            f"Each helper catches {h.c('(DriverError, Neo4jError)')}, "
            "logs, and re-raises &mdash; Neo4j outages surface as a "
            "FastAPI 500.",
            f"Labels and relationship strings are interpolated via "
            f"{h.c('%s')} substitution from "
            f"{h.c('FoundationalNodeEnum.value[1]')} / "
            f"{h.c('FoundationalRelationshipEnum.value[1]')}.",
        ]),
        h.PageBreak(),
    ]

    # ----- 3. mapper / response model -------------------------------------
    story += [
        h.p("3. Mapper / response model", h.H1),
        h.p(
            f"{h.c('PubmedSearchResultMapper')} "
            f"({h.c('src/foundation/mapper/pubmed_search_result_mapper.py')}) "
            f"converts the adapter's {h.c('DataFrame')} into a typed "
            f"frozen dataclass declared in "
            f"{h.c('src/foundation/model/pubmed/')}. The drug and "
            f"clinical-trial routes return "
            f"{h.c('PubmedSearchResult')}; the gene/protein route "
            f"returns {h.c('PubmedAndGeneSearchResult')} (same shape but "
            f"echoes {h.c('gene_protein')} instead of "
            f"{h.c('search_id')}).",
        ),
        h.p("Models (verbatim)", h.H2),
        h.code(
            "# src/foundation/model/pubmed/pubmed_search_result.py\n"
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class PubmedSearchResult:\n"
            "    search_id: str\n"
            "    count: int\n"
            "    results: list[PubmedSearchResultRow]\n"
            "\n"
            "# src/foundation/model/pubmed/pubmed_and_gene_search_result.py\n"
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class PubmedAndGeneSearchResult:\n"
            "    gene_protein: str\n"
            "    count: int\n"
            "    results: list[PubmedSearchResultRow]\n"
            "\n"
            "# src/foundation/model/pubmed/pubmed_search_result_row.py\n"
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class PubmedSearchResultRow:\n"
            "    pmid: str"
        ),
        h.p("Mapper behaviour", h.H2),
        *h.bullets([
            f"{h.c('map_drug_response')} (lines 17-30) and "
            f"{h.c('map_clinicaltrail_response')} (lines 32-45) both "
            f"return {h.c('PubmedSearchResult(search_id=..., count=..., results=[])')} "
            f"when the {h.c('DataFrame')} is None or empty.",
            f"{h.c('map_gene_response')} (lines 47-62) returns "
            f"{h.c('PubmedAndGeneSearchResult(gene_protein=..., count=0, results=[])')} "
            "for the empty case.",
            f"Row conversion is {h.c('_to_row')} (lines 64-69): it "
            f"reads the {h.c('pmid')} column, skips rows where "
            f"{h.c('pmid')} is None (this is what filters out the "
            f"{h.c('OPTIONAL MATCH')} no-Research rows from the clinical "
            f"trial route), and stringifies the value into "
            f"{h.c('PubmedSearchResultRow(pmid=str(row[&quot;pmid&quot;]))')}.",
            f"All three map methods call {h.c('_check_id_and_log')} "
            "(lines 71-76) which compares the request id to the first "
            "row's echo column and logs a WARNING if they differ &mdash; "
            "the response still ships, so any mismatch surfaces in logs "
            "rather than as a 5xx.",
            f"{h.c('count')} in the response is "
            f"{h.c('len(results)')} <i>after</i> the None-pmid filter; "
            f"it is the size of the returned page, <b>not</b> the total "
            f"matching across all pages. The total-across-all-pages "
            f"number comes from {h.c('/count/pmids/*')}.",
            f"{h.c('response_model_exclude_none=True')} on every route "
            f"means absent/None fields are stripped from the JSON, but "
            "for this schema every field is required so the output is "
            "stable.",
        ]),
        h.p("Example JSON &mdash; /pmids/drugs", h.H2),
        h.code(
            'GET /pmids/drugs?drug_id=DB00683&amp;page=1&amp;page_size=3\n'
            '\n'
            '{\n'
            '  "search_id": "DB00683",\n'
            '  "count": 3,\n'
            '  "results": [\n'
            '    { "pmid": "39912345" },\n'
            '    { "pmid": "39812003" },\n'
            '    { "pmid": "39711842" }\n'
            '  ]\n'
            '}'
        ),
        h.p("Example JSON &mdash; /pmids/geneproteins", h.H2),
        h.code(
            'GET /pmids/geneproteins?gene_protein=PDE3A&amp;page=1&amp;page_size=2\n'
            '\n'
            '{\n'
            '  "gene_protein": "PDE3A",\n'
            '  "count": 2,\n'
            '  "results": [\n'
            '    { "pmid": "39801122" },\n'
            '    { "pmid": "39600711" }\n'
            '  ]\n'
            '}'
        ),
        h.PageBreak(),
    ]

    # ----- 4. ETL pipeline -------------------------------------------------
    story += [
        h.p("4. ETL pipeline &mdash; how PMIDs get into Neo4j", h.H1),
        h.p(
            "The search route is read-only; it assumes the "
            f"{h.c(':Research')} nodes and their "
            f"{h.c(':featured_in')} / {h.c(':analyzed_in')} edges already "
            "exist. The pipeline has two top-level entry points, both "
            "shell scripts that boot the venv and run a Python module.",
        ),
        h.p("Stage 1 &mdash; NCBI download", h.H2),
        h.p(f"{h.c('src/download_pubmed.py')}", h.PATH),
        *h.bullets([
            f"CLI: {h.c('--search-terms')} (a list of disease/drug "
            f"strings) or {h.c('--download-by-pmcids')} (an explicit list "
            "of PMC ids). The two are mutually exclusive "
            f"({h.c('add_mutually_exclusive_group')}, line 50).",
            f"Wiring: {h.c('pubmed_orchestrator()')} from "
            f"{h.c('pubmed.conf.conf')} returns a "
            f"{h.c('PubmedOrchestrator')} "
            f"({h.c('src/pubmed/provider/pubmed_orchestrator.py')}) "
            "composed of a search provider, a fetch provider, a "
            "download provider, and a Neo4j article adapter.",
            f"For each pmc id, {h.c('orchestrator.fetch_and_download')} "
            f"sleeps {h.c('FETCH_THROTTLE_SECS = 10')} (line 13) to "
            f"respect NCBI rate limits, calls "
            f"{h.c('PubmedFetchProvider.fetch_by_id(pmcid)')} for "
            f"metadata, picks a {h.c('pdf_uri')} or falls back to the "
            f"{h.c('doi')} ({h.c('_pick_pdf_name')}, lines 61-65), "
            f"downloads the PDF via "
            f"{h.c('PubmedDownloadProvider.download(...)')}, and upserts "
            f"the {h.c(':Research')} node via "
            f"{h.c('Neo4jArticleAdapter.upsert_article(article)')}.",
            f"On any exception per pmc id the orchestrator counts a "
            f"failure and continues; nothing is retried inside the "
            "process (re-run the CLI to retry).",
        ]),
        h.p("Stage 2 &mdash; link articles into the graph", h.H2),
        h.p(f"{h.c('src/link_pubmed_articles.py')}", h.PATH),
        *h.bullets([
            f"CLI flag: {h.c('--use-checkpoints')}. When set, "
            f"{h.c('process_checkpoints')} (lines 58-93) reads a "
            f"hard-coded list of PDF file names "
            f"({h.c('generate_files_to_load()')}), maps each to a "
            f"checkpoint directory under {h.c('output/&lt;file_hash&gt;')}, "
            f"loads pre-extracted triples via "
            f"{h.c('stored_triples_loader().load([checkpoint])')}, then "
            f"feeds them into "
            f"{h.c('EugeneGraphSummaryOrchestrator.load_from_entities(pmcid, entities)')} "
            f"and {h.c('summarize_communities(...)')}.",
            f"When the flag is omitted, "
            f"{h.c('build_knowledge_graph')} (lines 96-108) drives a "
            f"{h.c('KnowledgeGraphDirAnalyzer')} over "
            f"{h.c('./resources/data/pubmed')} (PDFs only) which runs "
            "the per-document LLM extraction live &mdash; expensive, but "
            "used to bootstrap new corpora.",
            f"The summary orchestrator "
            f"({h.c('eugene_graph_summary_orchestrator(max_workers=3)')}, "
            f"line 40) is the component that emits the "
            f"{h.c(':featured_in')} and {h.c(':analyzed_in')} edges "
            f"between {h.c(':drug')} / {h.c(':gene_protein')} anchors "
            f"and the {h.c(':Research')} node. The drug-anchor edges "
            f"come from extracted drug mentions; the gene-anchor edges "
            "from extracted gene/protein mentions.",
            f"Embeddings are computed during the load via "
            f"{h.c('FoundationalNodeEmbeddingProvider')} (see "
            f"{h.c('conf.py:247-248')}); they support the similarity "
            "route, not the pubmed search route itself.",
        ]),
        h.p("Fix-up tooling", h.H2),
        h.p(
            f"{h.c('src/fix_pubmed_articles.py')} (CLI driving "
            f"{h.c('PubmedFixOrchestrator')} from "
            f"{h.c('src/pubmed/provider/pubmed_fix_orchestrator.py')}) "
            "is the maintenance script for repairing Research nodes "
            "whose metadata is stale (missing keywords, missing "
            "embedding, etc.). It does not create new edges &mdash; only "
            "the two stages above add the edges this search route "
            "walks.",
        ),
        h.PageBreak(),
    ]

    # ----- 5. debugging walk ----------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Start the service locally: "
            f"{h.c('uvicorn src.eugene_ws:app --reload')}. Confirm Neo4j "
            f"is up ({h.c('docker compose ps eugene-neo4j')}) and that "
            f"the pubmed subgraph is loaded "
            f"({h.c('MATCH (r:`Research`) RETURN count(r);')} should be "
            "non-zero).",
            f"Hit each endpoint with curl: "
            f"{h.c('curl &quot;http://localhost:8080/pmids/drugs?drug_id=DB00683&amp;page=1&amp;page_size=10&quot;')}, "
            f"then the {h.c('clinicaltrials')} (e.g. "
            f"{h.c('NCT00000122')}) and {h.c('geneproteins')} (e.g. "
            f"{h.c('PDE3A')}) variants. Expect "
            f"{h.c('{ &quot;search_id&quot;: ..., &quot;count&quot;: N, &quot;results&quot;: [...] }')} "
            f"(or {h.c('gene_protein')} key for the third route).",
            f"Breakpoint at {h.c('pubmed_search_router.py:73')} (the "
            f"adapter call). Step into "
            f"{h.c('Neo4jPubmedQueryAdapter.find_related_pubmed_by_drug')} "
            f"({h.c('neo4j_pubmed_query_adapter.py:27')}). Inspect the "
            f"assembled Cypher string at "
            f"{h.c('neo4j_pubmed_query_adapter.py:91-108')} (it is also "
            f"emitted at INFO via the {h.c('logger.info(f&quot;search: {search}&quot;)')} "
            "on line 78).",
            f"Copy that Cypher into {h.c('cypher-shell')} and run with "
            f"{h.c(':param drug_id => &quot;DB00683&quot;')}. Row count "
            f"must equal {h.c('count')} in the HTTP response. If it does "
            f"not, candidate explanations are (a) "
            f"{h.c('normalize_drug_id')} mutated the id (re-check the "
            f"log line {h.c('searching for related pubmed by drug: ...')}), "
            f"(b) you are pointed at a different Neo4j instance than "
            f"the API is, or (c) you forgot the {h.c('SKIP/LIMIT')} when "
            "running by hand &mdash; the API always paginates.",
            f"Force the validator: "
            f"{h.c('curl &quot;.../pmids/drugs?drug_id=DB%24000683&amp;page=1&amp;page_size=10&quot;')} "
            f"(URL-encoded {h.c('$')}). Expect a 422 from "
            f"{h.c('validate_value')}. Repeat for the clinicaltrials "
            f"route with a missing {h.c('NCT')} prefix (e.g. "
            f"{h.c('?nct_id=00000122')}); expect a 422 from "
            f"{h.c('validate_clinical_trail_id')}. Repeat with "
            f"{h.c('page_size=101')}; expect 422 from FastAPI's "
            f"{h.c('le=100')}.",
            f"Cross-check pagination against the count route: "
            f"{h.c('curl &quot;.../count/pmids/drugs?drug_id=DB00683&quot;')} "
            f"and confirm "
            f"{h.c('ceil(pubmed_count / page_size)')} pages exist. "
            f"Page 1 + page 2 + ... should sum back to "
            f"{h.c('pubmed_count')}; divergence indicates a duplicate "
            f"{h.c(':featured_in')} edge or a "
            f"{h.c('count(*) vs count(DISTINCT)')} mismatch worth "
            "investigating on the count adapter side.",
        ]),
        h.PageBreak(),
    ]

    # ----- 6. reference index ---------------------------------------------
    story += [
        h.p("6. Reference index (file paths)", h.H1),
        h.code(
            "Route &amp; wiring\n"
            "  src/eugene_ws.py:50,72            (import + add_routers)\n"
            "  src/foundation/router/pubmed_search_router.py\n"
            "  src/foundation/router/validate_util.py:35-42  (validate_value)\n"
            "  src/foundation/router/validate_util.py:45-55  (validate_clinical_trail_id)\n"
            "  src/foundation/router/validate_util.py:71-77  (validate_gene_protein)\n"
            "  src/foundation/model/case_helper.py            (normalize_*)\n"
            "  src/foundation/conf/conf.py:219-226            (neo4j_pubmed_query_adapter)\n"
            "  src/foundation/conf/conf.py:271-272            (pubmed_search_result_mapper)\n"
            "\n"
            "Adapter (Cypher)\n"
            "  src/foundation/infra/db/adapter/neo4j_pubmed_query_adapter.py\n"
            "    :27-40   find_related_pubmed_by_drug\n"
            "    :42-55   find_related_pubmed_by_clinicaltrail\n"
            "    :57-70   find_related_pubmed_by_gene\n"
            "    :72-108  _find_related_pubmed_by_drug + Cypher generator\n"
            "    :110-152 _find_related_pubmed_by_clinicaltrail + Cypher generator\n"
            "    :154-190 _find_related_pubmed_by_gene + Cypher generator\n"
            "  src/foundation/infra/db/util/pagination.py     (Pagination.calculate_limit_and_offset)\n"
            "\n"
            "Mapper &amp; response models\n"
            "  src/foundation/mapper/pubmed_search_result_mapper.py\n"
            "    :17-30  map_drug_response\n"
            "    :32-45  map_clinicaltrail_response\n"
            "    :47-62  map_gene_response\n"
            "    :64-69  _to_row\n"
            "    :71-76  _check_id_and_log\n"
            "  src/foundation/model/pubmed/pubmed_search_result.py\n"
            "  src/foundation/model/pubmed/pubmed_and_gene_search_result.py\n"
            "  src/foundation/model/pubmed/pubmed_search_result_row.py\n"
            "\n"
            "Domain model (labels &amp; rel types)\n"
            "  src/foundation/model/foundational_node_enum.py\n"
            "    :10   CLINICAL_TRIAL = ClinicalTrial\n"
            "    :14   DRUG           = drug\n"
            "    :18   GENE_PROTEIN   = gene_protein\n"
            "    :33   RESEARCH       = Research\n"
            "  src/foundation/model/foundational_relationship_enum.py\n"
            "    :28   FEATURED_IN  = featured_in\n"
            "    :29   ANALYZED_IN  = analyzed_in\n"
            "\n"
            "Companion count route (same anchors, count(*) instead of pagination)\n"
            "  src/foundation/router/pubmed_count_router.py\n"
            "  src/foundation/infra/db/adapter/neo4j_pubmed_count_adapter.py\n"
            "  src/foundation/conf/conf.py:209-216            (neo4j_pubmed_count_adapter)\n"
            "\n"
            "ETL\n"
            "  src/download_pubmed.py                         (NCBI fetch + PDF download CLI)\n"
            "  src/pubmed/provider/pubmed_orchestrator.py     (search + fetch + download + upsert)\n"
            "  src/pubmed/provider/pubmed_search_provider.py  (NCBI e-search wrapper)\n"
            "  src/pubmed/provider/pubmed_fetch_provider.py   (NCBI e-fetch wrapper)\n"
            "  src/pubmed/provider/pubmed_download_provider.py(PDF retrieval)\n"
            "  src/pubmed/infra/db/neo4j_article_adapter.py   (Research-node upsert)\n"
            "  src/link_pubmed_articles.py                    (LLM extraction + edge build CLI)\n"
            "  src/fix_pubmed_articles.py                     (metadata + embedding fix-up)\n"
            "  src/pubmed/provider/pubmed_fix_orchestrator.py\n"
        ),
        h.Spacer(1, 6),
        h.p(
            "<i>End of pubmed-search route flow guide.</i>",
            h.BODY,
        ),
    ]

    return story
