"""Flow-guide section module for Eugene's facts route.

Endpoint: GET /graph/facts/start/{start_id}?page=<int>&page_size=<int>

Renders the 1-hop neighborhood of a node as a set of natural-language
"facts" sentences (e.g. ``Drug Flurandrenolide has drug effect, Pruritus``).
This is the route the MCP ``fetch_facts`` tool drives and the form most
LLM-friendly to splice into prompts.

Built by the flow-guide generator -> ``docs/EUGENE_FACTS_FLOW_GUIDE.pdf``.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_FACTS_FLOW_GUIDE.pdf"
TITLE = "Eugene Facts Route - End-to-End Flow"


def build_story() -> list:
    story = []

    # ---- Title block ------------------------------------------------------
    story += [
        h.p("Eugene Facts Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP request &rarr; FastAPI router &rarr; "
            "shared n-hop Cypher &rarr; FactsMapper &rarr; sentence-shaped "
            "ListResponse",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene turns its graph "
            "neighborhood into LLM-ready natural-language sentences. The "
            "facts route is a thin re-skin over the same n-hop Cypher used "
            "by " + h.c("/graph/relationship/start/{start_id}") + ", but "
            "where that route returns an adjacency-list "
            + h.c("Graph") + ", this one collapses each "
            "(start, rel, end) triple into a single English sentence and "
            "returns them as a flat list of strings. Every reference uses "
            "the form " + h.c("path/to/file.py:line") + ".",
        ),
        h.p("Reference endpoint", h.H2),
        *h.bullets([
            h.c("GET /graph/facts/start/{start_id}?page=1&amp;page_size=10")
            + " &mdash; 1-hop facts around the anchor, paginated.",
            "<b>Hop depth is fixed at 1</b>. The router handler hard-codes "
            + h.c("n_hop=1") + " when calling the orchestrator (line ~69). "
            "A commented-out " + h.c("n_hop") + " query param sits in the "
            "signature as a reminder &mdash; do not uncomment without also "
            "reworking the mapper, which assumes a star-shaped subgraph.",
            h.c("page") + " is " + h.c("gt=0") + ", "
            + h.c("page_size") + " is " + h.c("gt=0, le=50")
            + " &mdash; Pydantic rejects 0 / 51+ before the handler runs.",
            h.c("start_id") + " is "
            + h.c("Annotated[str]") + " with "
            + h.c("max_length=512") + " and an "
            + h.c("AfterValidator(validate_id)") + ".",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "Facts are derived directly from graph topology. There is no "
            "curated sentence template per relationship type &mdash; "
            + h.c("FactsMapper._to_fact") + " mechanically interpolates "
            "the label and the relationship type into the same string "
            "shape. The resulting sentences are <i>truthful</i> but read "
            "awkwardly for some rel types (e.g. "
            + h.c("drug_drug") + " becomes a "
            "<font face='Courier'>relationship to drug</font> clause via "
            "the redundancy fix-up). If you need polished prose, do it in "
            "the LLM layer, not here.",
        ),
        h.PageBreak(),
    ]

    # ---- 0. Schema --------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "Facts derive directly from graph topology &mdash; every "
            "sentence corresponds to exactly one "
            + h.c("(startNode)-[r]-(endNode)") + " triple in Neo4j. The "
            "route does not introspect a schema registry; "
            + h.c("FactsMapper") + " just pretty-prints whatever labels "
            "and relationship types the database returns.",
        ),
        h.p(
            "The label and relationship-type names that get rendered are "
            "the canonical Eugene enums:",
        ),
        h.code(
            "# src/foundation/model/foundational_node_enum.py\n"
            "FoundationalNodeEnum:\n"
            "    DRUG               = 'drug'\n"
            "    DISEASE            = 'disease'\n"
            "    GENE_PROTEIN       = 'gene_or_protein'\n"
            "    PATHWAY            = 'pathway'\n"
            "    EFFECT_PHENOTYPE   = 'effect_or_phenotype'\n"
            "\n"
            "# src/foundation/model/foundational_relationship_enum.py\n"
            "FoundationalRelationshipEnum:\n"
            "    INDICATION         = 'indication'\n"
            "    DRUG_DRUG          = 'drug_drug'\n"
            "    DRUG_EFFECT        = 'drug_effect'\n"
            "    DRUG_PROTEIN       = 'drug_protein'\n"
            "    DISEASE_PROTEIN    = 'disease_protein'\n"
            "    PATHWAY_PROTEIN    = 'pathway_protein'\n"
            "    PROTEIN_PROTEIN    = 'protein_protein'"
        ),
        *h.bullets([
            "<b>Label-agnostic Cypher</b>: the underlying query (section 2) "
            "matches any label on either side. The enums above are the "
            "<i>observed</i> values FactsMapper will see; new labels would "
            "be rendered just by replacing underscores with spaces.",
            "<b>Single-label assumption</b>: "
            + h.c("FactsMapper._to_fact") + " calls "
            + h.c("set(start_node.labels).pop()") + " &mdash; if a node "
            "carries two labels the choice is non-deterministic. In "
            "practice Eugene nodes ship with one label so this is fine, "
            "but be aware before bolting on multi-label data.",
            "<b>Relationship types from data, not enum</b>: the Cypher "
            "returns " + h.c("type(rel)") + " verbatim. If the ETL writes "
            "an unknown relationship type, the sentence still renders &mdash; "
            "it just may read oddly.",
            "Paths only exist if upstream ETL populated the graph. An "
            "empty " + h.c("ListResponse") + " usually means the seed/ETL "
            "for that domain has not run yet, not that the route is "
            "broken.",
        ]),
        h.PageBreak(),
    ]

    # ---- 1. HTTP entry ----------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; router, validators, DI", h.H1),
        h.p(h.c("src/foundation/router/facts_router.py"), h.PATH),
        *h.bullets([
            "Module-load DI at line 22: "
            + h.c("facts_orchestrator = foundational_facts_orchestrator()")
            + ". Instantiated once on import; the orchestrator (and its "
            "driver-backed adapter) is reused for every request.",
            "Router prefix is " + h.c("/graph")
            + " (line 17-20: "
            + h.c("APIRouter(prefix=\"/graph\", tags=[\"facts\"])")
            + "), so the full path is "
            + h.c("GET /graph/facts/start/{start_id}") + ".",
            "Decorator (lines 25-29): "
            + h.c("response_model=ListResponse") + ", "
            + h.c("response_model_exclude_none=True") + ".",
            "Path param " + h.c("start_id")
            + " (lines 31-40): "
            + h.c("Annotated[str, Path(..., max_value=512, min_length=0)]")
            + " plus an "
            + h.c("AfterValidator(validate_id)") + ".",
            "Query param " + h.c("page") + " (lines 41-48): "
            + h.c("int") + ", " + h.c("gt=0") + ", required.",
            "Query param " + h.c("page_size") + " (lines 49-57): "
            + h.c("int") + ", " + h.c("gt=0, le=50") + ", required.",
            "Handler body (lines 68-75) is a three-liner: call "
            + h.c("facts_orchestrator.find_facts_by_start_id(start_id, "
                  "n_hop=1, page_size, page)") + ", "
            "guard against " + h.c("None") + ", wrap the resulting "
            + h.c("set[str]") + " as "
            + h.c("ListResponse(count=len(facts), results=list(facts))")
            + ".",
        ]),
        h.p("Validator", h.H2),
        h.p(h.c("src/foundation/router/validate_util.py"), h.PATH),
        h.code(
            "def validate_id(id: str) -> str:\n"
            "    invalid_chars = ['%', '$', ';', ':', '^', '*']\n"
            "    is_valid = not has_invalid_char(\n"
            "        invalid_chars=invalid_chars, value=id\n"
            "    )\n"
            "    if not is_valid:\n"
            "        raise ValueError(\n"
            "            f\"id cannot have a special character: {invalid_chars}\"\n"
            "        )\n"
            "    return id"
        ),
        h.p(
            "Defense-in-depth: the Cypher uses parameterised "
            + h.c("$start_id") + " so injection is not the concrete threat. "
            "The validator exists to fail fast on URL-encoded payloads, "
            "regex metacharacters, and similar garbage before the driver "
            "round-trips to Neo4j.",
        ),
        h.p("DI factory", h.H2),
        h.p(h.c("src/foundation/conf/conf.py:406-410"), h.PATH),
        h.code(
            "def foundational_facts_orchestrator() -> FoundationalFactsOrchestrator:\n"
            "    return _foundational_facts_orchestrator(\n"
            "        foundational_n_hop_provider=foundational_n_hop_provider(),\n"
            "        facts_mapper=facts_mapper(),\n"
            "    )"
        ),
        h.p(
            "The orchestrator composes the <b>same</b> "
            + h.c("foundational_n_hop_provider") + " the "
            + h.c("/graph/relationship/start/...") + " route uses with a "
            "domain-specific " + h.c("FactsMapper") + " in place of the "
            "adjacency-list " + h.c("GraphMapper") + ". This is the key "
            "structural point of the route: <i>same Cypher, different "
            "mapper</i>.",
        ),
        h.p("Response model", h.H2),
        h.p(h.c("src/foundation/router/model/list_response.py"), h.PATH),
        h.code(
            "class ListResponse(BaseModel):\n"
            "    count:   int\n"
            "    results: list[str]"
        ),
        h.p(
            "Deliberately flat. Each entry is one rendered fact sentence; "
            + h.c("count") + " is just " + h.c("len(results)") + " &mdash; "
            "no separate total/total-pages field because the underlying "
            "n-hop adapter does not currently surface a global count.",
        ),
        h.PageBreak(),
    ]

    # ---- 2. Underlying Cypher --------------------------------------------
    story += [
        h.p("2. Underlying Cypher &mdash; shared with the n-hop route", h.H1),
        h.p(
            h.c(
                "src/foundation/infra/db/adapter/"
                "neo4j_foundational_n_hop_adapter.py"
            ),
            h.PATH,
        ),
        h.p(
            "The facts route does <b>not</b> have its own adapter. The "
            "orchestrator calls "
            + h.c(
                "foundational_n_hop_provider"
                ".find_subgraph_by_start_id_and_end_id"
            )
            + ", which calls the same n-hop adapter that powers "
            + h.c("/graph/relationship/start/...") + ". The Cypher is "
            "exactly what that route's flow guide documents &mdash; "
            "reproduced here for convenience:",
        ),
        h.code(
            "MATCH (startNode { node_id: $start_id })-[r]-{0,N_HOP}(endNode)\n"
            "UNWIND(r) AS rel\n"
            "RETURN DISTINCT\n"
            "    startNode(rel).node_name             AS startName,\n"
            "    toStringOrNull(startNode(rel).node_id) AS startId,\n"
            "    labels(startNode(rel))               AS startLabels,\n"
            "    endNode(rel).node_name               AS endName,\n"
            "    toStringOrNull(endNode(rel).node_id) AS endId,\n"
            "    labels(endNode(rel))                 AS endLabels,\n"
            "    type(rel)                            AS relType\n"
            "ORDER BY startName\n"
            "SKIP  $offset\n"
            "LIMIT $limit"
        ),
        *h.bullets([
            "<b>N_HOP is always 1</b> for this route &mdash; the facts "
            "router hard-codes "
            + h.c("n_hop=1") + " (line ~69) when calling the orchestrator. "
            "The adapter still goes through its "
            + h.c("_ensure_valid_n_hop_size_or_throw") + " guard "
            "(MAX_SUPPORTED_HOPS=2), which is a no-op for 1.",
            "<b>No " + h.c("end_id") + " branch</b>: facts always wants the "
            "open neighborhood, so the orchestrator passes "
            + h.c("end_id=None") + ", which makes the adapter emit "
            + h.c("(endNode)") + " with no property filter.",
            "<b>Pagination</b> via " + h.c("SKIP") + " / "
            + h.c("LIMIT") + " from the router's "
            + h.c("page") + " / " + h.c("page_size")
            + ". Offset is computed by "
            + h.c("Pagination.calculate_limit_and_offset") + " in "
            + h.c("src/foundation/infra/db/util/pagination.py") + ".",
            "<b>" + h.c("MAX_RESULT_COUNT = 10_000")
            + "</b> ceiling in "
            + h.c("FoundationalNHopProvider") + ": if the DataFrame "
            "exceeds that, the provider raises rather than truncating. "
            "Page sizes are capped at 50 at the router so a single "
            "request cannot trip this, but cumulative caller behaviour "
            "can if the start node sits in a hub.",
            "<b>Result transformer</b>: "
            + h.c("result_transformer_=neo4j.Result.to_df") + ". The "
            "DataFrame columns match "
            + h.c("src/foundation/mapper/const.py") + " constants which "
            + h.c("GraphMapper") + " then turns into the "
            + h.c("Graph") + " that "
            + h.c("FactsMapper") + " consumes.",
        ]),
        h.PageBreak(),
    ]

    # ---- 3. Facts mapper --------------------------------------------------
    story += [
        h.p("3. Facts mapper &mdash; triples to sentences", h.H1),
        h.p(h.c("src/foundation/mapper/facts_mapper.py"), h.PATH),
        h.p(
            h.c("FactsMapper.map(graph)") + " (line 13) is the only "
            "public entry. It builds a dict "
            + h.c("{node_id -> Node}") + " from "
            + h.c("graph.nodes") + ", then iterates every key of "
            + h.c("graph.relationships") + " and renders one fact "
            "per outgoing " + h.c("Relationship") + ". Output type is "
            + h.c("set[str]") + " &mdash; duplicate sentences (e.g. "
            "from the undirected "
            + h.c("-[r]-") + " match producing the triple in both "
            "directions) are de-duped naturally.",
        ),
        h.p("The template", h.H2),
        h.p(
            h.c("_to_fact(start_node, rel, end_node)") + " (line 34) "
            "renders, after redundancy fix-up:",
        ),
        h.code(
            '"{StartLabel} {StartValue} has {RelType} {EndLabel}, {EndValue}"'
        ),
        h.p(
            "Each piece is run through "
            + h.c("_label_to_text") + " which replaces underscores with "
            "spaces, and through "
            + h.c("_remove_redundant") + " which strips a leading word "
            "of " + h.c("clause2") + " when it matches the trailing word "
            "of " + h.c("clause1") + ". The start label is "
            + h.c(".capitalize()") + "'d. For the triple "
            + h.c("(:drug {Flurandrenolide})-[:drug_effect]-(:effect_or_phenotype {Pruritus})") + ":",
        ),
        h.code(
            "start_label   = 'drug'\n"
            "relationship  = 'drug effect'                # _label_to_text(rel)\n"
            "fixed_rel     = _remove_redundant('drug', 'drug effect')\n"
            "              = 'effect'                     # 'drug' matched both sides -> drop\n"
            "end_label     = 'effect or phenotype'\n"
            "fixed_end     = _remove_redundant('drug effect', 'effect or phenotype')\n"
            "              = 'or phenotype'               # trailing 'effect' matched leading 'effect'\n"
            "# final sentence:\n"
            "# 'Drug Flurandrenolide has effect or phenotype, Pruritus'"
        ),
        h.p(
            "<i>Aside</i>: the redundancy fix-up is heuristic. For "
            + h.c("drug_drug") + ", "
            + h.c("_remove_redundant") + " has a special branch "
            "(lines 61-63) that detects "
            + h.c("splits2[0] == splits2[1]") + " and rewrites the "
            "clause to " + h.c("relationship to drug") + " so the "
            "sentence does not read like "
            + h.c("&hellip; has drug drug drug &hellip;") + ".",
        ),
        h.p("Worked example", h.H2),
        h.code(
            "# Triple coming out of the n-hop Cypher:\n"
            "(:drug {node_name: 'Flurandrenolide'})\n"
            "    -[:drug_effect]-\n"
            "(:effect_or_phenotype {node_name: 'Pruritus'})\n"
            "\n"
            "# Sentence produced by FactsMapper._to_fact:\n"
            "'Drug Flurandrenolide has drug effect, Pruritus'"
        ),
        h.p(
            "Other shapes follow the same pattern: "
            + h.c("'Drug Imatinib has drug protein, ABL1'") + " from "
            "a " + h.c(":drug_protein") + " edge, "
            + h.c("'Disease Hemophilia A has indication, Factor VIII'")
            + " from a " + h.c(":indication") + " edge, and so on. "
            "Pathway and protein-protein triples render analogously.",
        ),
        h.p("Edge cases", h.H2),
        *h.bullets([
            h.c("graph is None") + " &rarr; returns empty set. The router "
            "then wraps that as "
            + h.c("ListResponse(count=0, results=[])") + ".",
            "Node with multiple labels &rarr; "
            + h.c("set(...).pop()") + " is non-deterministic; the "
            "sentence will still render but the picked label is "
            "arbitrary.",
            "Self-loops (the " + h.c("0") + " in "
            + h.c("-[r]-{0,N}") + " can produce a self-row from the "
            "anchor): same start and end node, treated as a regular "
            "triple. In practice these are rare in Eugene's data.",
            "<b>No ordering</b>: " + h.c("set[str]") + " is unordered. "
            "The router converts to "
            + h.c("list(facts)") + " for the response, but two calls "
            "with the same input may return the same strings in "
            "different orders.",
        ]),
        h.PageBreak(),
    ]

    # ---- 4. Response model ------------------------------------------------
    story += [
        h.p("4. Response model &mdash; sample JSON", h.H1),
        h.p(
            "The wire format is the flat "
            + h.c("ListResponse") + " from "
            + h.c("src/foundation/router/model/list_response.py") + ":",
        ),
        h.code(
            "{\n"
            '  "count": 4,\n'
            '  "results": [\n'
            '    "Drug Flurandrenolide has drug effect, Pruritus",\n'
            '    "Drug Flurandrenolide has drug effect, Erythema",\n'
            '    "Drug Flurandrenolide has drug protein, NR3C1",\n'
            '    "Drug Flurandrenolide has indication, Atopic dermatitis"\n'
            "  ]\n"
            "}"
        ),
        *h.bullets([
            h.c("count") + " is always " + h.c("len(results)") + ". It is "
            "a convenience for the UI &mdash; there is no separate "
            "total-pages count.",
            h.c("results") + " is " + h.c("list[str]") + ": each entry is "
            "one rendered fact. Order is not stable across calls (the "
            "underlying " + h.c("set") + " is unordered).",
            "Empty graph &rarr; "
            + h.c("{\"count\": 0, \"results\": []}") + " (the router's "
            "explicit " + h.c("None") + " guard at lines 72-73).",
            h.c("response_model_exclude_none=True") + " is set but the "
            "model has no optional fields, so it is a no-op here &mdash; "
            "kept for consistency with the other routes.",
        ]),
        h.PageBreak(),
    ]

    # ---- 5. Data source ---------------------------------------------------
    story += [
        h.p("5. Data source &mdash; where the edges come from", h.H1),
        h.p(
            "This route is <b>purely read-side</b>. It does not create or "
            "merge anything. The facts you see are entirely a function of "
            "what the global ETL pipelines have written into Neo4j:",
        ),
        *h.bullets([
            h.c("src/ingest_drug_aliases.py") + " &mdash; CSV ingest of "
            "drug product names &amp; synonyms; attaches "
            + h.c(":drug_product") + " and "
            + h.c(":drug_synonym") + " to canonical "
            + h.c(":drug") + " nodes via "
            + h.c(":has_drug_alias") + ". See "
            + h.c("EUGENE_DRUG_ALIAS_FLOW_GUIDE.pdf") + ".",
            h.c("src/download_patents.py") + " &mdash; USPTO / patent "
            "metadata; attaches " + h.c(":patent") + " nodes to "
            "assignees and target drugs via "
            + h.c(":has_patent") + " edges. See "
            + h.c("EUGENE_PATENT_FLOW_GUIDE.pdf") + ".",
            h.c("src/download_clinicaltrail.py") + " &mdash; "
            "clinicaltrials.gov records; connects "
            + h.c(":clinical_trial") + " nodes to drug + indication.",
            h.c("src/download_pubmed.py") + " &mdash; PubMed publication "
            "ingest; attaches "
            + h.c(":publication") + " nodes and citation edges.",
            "Seed Cypher under " + h.c("bin/seed/") + " &mdash; creates "
            "the canonical " + h.c(":drug") + ", "
            + h.c(":disease") + ", "
            + h.c(":gene_or_protein") + ", "
            + h.c(":pathway") + ", "
            + h.c(":effect_or_phenotype") + " nodes everything else "
            "hangs off.",
        ]),
        h.p(
            "If a fresh database returns "
            + h.c("{\"count\": 0, \"results\": []}") + " for a known good "
            + h.c("start_id") + ", the failure is almost always upstream &mdash; "
            "the seed Cypher or one of the ingest CLIs did not run for "
            "the domain you are testing.",
        ),
        h.p("How to confirm there is something to render", h.H2),
        h.code(
            "// In neo4j-browser:\n"
            "MATCH (n { node_id: '19725' }) RETURN n, labels(n)\n"
            "MATCH (n { node_id: '19725' })-[r]-(m) RETURN type(r), count(*)\n"
            "// If the second query is empty the facts response will be too."
        ),
        h.PageBreak(),
    ]

    # ---- 6. Debug walk ----------------------------------------------------
    story += [
        h.p("6. Suggested debugging walk", h.H1),
        *h.bullets([
            "<b>Bring the stack up</b>: "
            + h.c("docker-compose up eugene_neo4j eugene_ws")
            + ". Confirm the seed Cypher has run (see section 5) so "
            "there is something to traverse.",
            "<b>Sanity-curl</b>: "
            + h.c(
                "curl -s '$EUGENE_WS/graph/facts/start/19725"
                "?page=1&amp;page_size=10' | jq"
            )
            + ". Expect a non-empty "
            + h.c("results") + " array of English sentences and a "
            + h.c("count") + " that matches "
            + h.c("results | length") + ".",
            "<b>Breakpoint at the router handler</b>: "
            + h.c("src/foundation/router/facts_router.py:68")
            + " (the " + h.c("facts_orchestrator.find_facts_by_start_id")
            + " call). Inspect "
            + h.c("start_id") + ", "
            + h.c("page") + ", " + h.c("page_size") + " after FastAPI "
            "validation and confirm the hard-coded "
            + h.c("n_hop=1") + ".",
            "<b>Step into the orchestrator</b>: "
            + h.c("src/foundation/provider/foundational_facts_orchestrator.py:29")
            + " &mdash; watch it delegate to "
            + h.c("foundational_n_hop_provider.find_subgraph_by_start_id_and_end_id")
            + ". The intermediate " + h.c("Graph") + " object is the same "
            "shape the " + h.c("/graph/relationship/...") + " route returns.",
            "<b>Step through the n-hop adapter</b>: breakpoint at "
            + h.c(
                "src/foundation/infra/db/adapter/"
                "neo4j_foundational_n_hop_adapter.py:112"
            )
            + " (" + h.c("_collect_n_hop") + "). Copy the assembled Cypher "
            "string + " + h.c("params") + " dict into Neo4j Browser to "
            "feel what it returns; confirm the "
            + h.c("-[r]-{0,1}") + " bound.",
            "<b>Inspect the mapper</b>: breakpoint at "
            + h.c("src/foundation/mapper/facts_mapper.py:34")
            + " (" + h.c("_to_fact") + "). Step into "
            + h.c("_remove_redundant") + " and confirm the redundancy "
            "fix-up does what you expect for your label / rel-type "
            "combo &mdash; especially for tricky cases like "
            + h.c("drug_drug") + " or "
            + h.c("protein_protein") + ".",
        ]),
        h.PageBreak(),
    ]

    # ---- 7. Reference index ----------------------------------------------
    story += [
        h.p("7. Reference index", h.H1),
        h.code(
            "Schema (informational)\n"
            "  src/foundation/model/foundational_node_enum.py          # DRUG, DISEASE, GENE_PROTEIN, PATHWAY, EFFECT_PHENOTYPE\n"
            "  src/foundation/model/foundational_relationship_enum.py  # INDICATION, DRUG_DRUG, DRUG_EFFECT, DRUG_PROTEIN,\n"
            "                                                          # DISEASE_PROTEIN, PATHWAY_PROTEIN, PROTEIN_PROTEIN\n"
            "  # NOTE: the Cypher is label-agnostic; enums describe what FactsMapper will see, not what it filters on.\n\n"
            "Router & wiring\n"
            "  src/foundation/router/facts_router.py                   # endpoint, line 22 DI, lines 25-29 decorator, lines 30-75 handler\n"
            "  src/foundation/router/validate_util.py                  # validate_id, line 98-104\n"
            "  src/foundation/router/model/list_response.py            # ListResponse{count, results}\n"
            "  src/foundation/conf/conf.py                             # foundational_facts_orchestrator factory L406-410\n\n"
            "Orchestrator & mapper\n"
            "  src/foundation/provider/foundational_facts_orchestrator.py  # find_facts_by_start_id, line 25-34\n"
            "  src/foundation/mapper/facts_mapper.py                       # map L13, _to_fact L34, _remove_redundant L53\n\n"
            "Shared n-hop machinery (same as /graph/relationship route)\n"
            "  src/foundation/provider/foundational_n_hop_provider.py  # MAX_RESULT_COUNT=10_000\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py  # Cypher L138-170\n"
            "  src/foundation/infra/db/util/pagination.py              # SKIP/LIMIT helper\n"
            "  src/foundation/mapper/graph_mapper.py                   # DataFrame -> Graph (input to FactsMapper)\n"
            "  src/foundation/mapper/const.py                          # DataFrame column names\n"
            "  src/foundation/model/graph/graph.py                     # Graph dataclass\n"
            "  src/foundation/model/graph/node.py                      # Node dataclass\n"
            "  src/foundation/model/graph/relationship.py              # Relationship dataclass\n\n"
            "ETL (for graph data)\n"
            "  src/ingest_drug_aliases.py\n"
            "  src/download_patents.py\n"
            "  src/download_clinicaltrail.py\n"
            "  src/download_pubmed.py\n"
            "  bin/seed/*.cypher                                       # canonical node seed\n"
        ),
    ]

    return story
