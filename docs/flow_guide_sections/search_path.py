"""Eugene Search Path - end-to-end developer flow guide section."""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_SEARCH_PATH_FLOW_GUIDE.pdf"
TITLE = "Eugene Search Path - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # -- title block --------------------------------------------------------
    story += [
        h.p("Eugene Search Path &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP request &rarr; id validation &rarr; "
            "FoundationalPathProvider &rarr; Neo4j SHORTEST / ANY traversal &rarr; "
            "ShortestPaths / Reachability response",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene answers "
            "&quot;what is the shortest path between two graph nodes?&quot; and "
            "&quot;is node A reachable from node B within N hops?&quot;. Unlike the "
            "drug-alias and patent flows, the search-path route is label-agnostic: "
            "the Cypher queries match <b>any</b> node label and <b>any</b> "
            "relationship type, anchored only on the "
            "<font face='Courier'>node_id</font> property. Every reference uses "
            "the form <font face='Courier'>path/to/file.py:line</font>.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            "<font face='Courier'>GET /graph/path/start/{start_id}/end/{end_id}?n_hop=&lt;int&gt;</font> "
            "&mdash; returns up to 10 shortest paths (each a list of node_ids) between two nodes.",
            "<font face='Courier'>GET /graph/reachability/start/{start_id}/end/{end_id}?n_hop=&lt;int&gt;</font> "
            "&mdash; returns a boolean: does any path of length &le; <i>n_hop</i> exist?",
        ]),
        h.p("How to read this guide", h.H2),
        h.p(
            "The flow is short: the router is thin, there is exactly one "
            "provider and one Neo4j adapter, and the response models are flat "
            "frozen dataclasses. Read section 0 first &mdash; it explains why "
            "this route does not own any ETL of its own."
        ),
        h.PageBreak(),
    ]

    # -- 0. schema ----------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "Unlike the drug-alias or patent routes, the search-path queries "
            "do <b>not</b> pin themselves to any label or relationship type. The "
            "Cypher patterns look like:",
        ),
        h.code(
            "(startNode { node_id: $start_id })-[link]-{0,N}(endNode { node_id: $end_id })"
        ),
        *h.bullets([
            "Both endpoints are <b>anchored on the </b><font face='Courier'>node_id</font><b> property</b> only &mdash; no label filter, no relationship-type filter.",
            "Any node previously written to the graph by an upstream ETL pipeline (drugs, patents, clinical trials, pubmed, organizations, etc.) is a valid <font face='Courier'>start_id</font> or <font face='Courier'>end_id</font>.",
            "Edges are walked undirected: the Cypher uses <font face='Courier'>-[link]-</font>, not <font face='Courier'>-[link]-&gt;</font>.",
            "The graph must be <b>pre-populated</b> for these queries to return anything. The search-path route is read-only &mdash; see section 4.",
            "Hop bound <font face='Courier'>{0,N}</font> is interpolated from the <font face='Courier'>n_hop</font> query parameter. 0 hops means the start and end are the same node.",
        ]),
        h.PageBreak(),
    ]

    # -- 1. HTTP entry ------------------------------------------------------
    story += [
        h.p("1. HTTP entry", h.H1),
        h.p("src/foundation/router/search_path_router.py", h.PATH),
        *h.bullets([
            "Module-load DI at line 20: <font face='Courier'>search_path_provider = foundational_path_provider()</font> &mdash; constructed once at import time and reused across requests.",
            "Router prefix is <font face='Courier'>/graph</font> with tag <font face='Courier'>foundation</font> (lines 15-18).",
            "<font face='Courier'>GET /graph/path/start/{start_id}/end/{end_id}</font> (line 23) &mdash; delegates to <font face='Courier'>provider.find_shortest_path_by_start_id_and_end_id(...)</font> at line 58.",
            "<font face='Courier'>GET /graph/reachability/start/{start_id}/end/{end_id}</font> (line 63) &mdash; delegates to <font face='Courier'>provider.find_is_reachable_by_start_id_and_end_id(...)</font> at line 98, then logs the result.",
            "Both endpoints declare <font face='Courier'>n_hop</font> as a <font face='Courier'>Query(gt=0, le=4)</font> int &mdash; FastAPI rejects out-of-range values with HTTP 422 before the provider is even called (lines 48-56 and 88-96).",
        ]),
        h.p("Id validation", h.H2),
        h.p("src/foundation/router/validate_util.py", h.PATH),
        h.p(
            "Both <font face='Courier'>start_id</font> and <font face='Courier'>end_id</font> "
            "are wrapped with <font face='Courier'>AfterValidator(validate_id)</font>. "
            "<font face='Courier'>validate_id</font> (line 98) rejects ids that contain "
            "any of <font face='Courier'>%</font>, <font face='Courier'>$</font>, "
            "<font face='Courier'>;</font>, <font face='Courier'>:</font>, "
            "<font face='Courier'>^</font>, <font face='Courier'>*</font> with a "
            "<font face='Courier'>ValueError</font>:"
        ),
        h.code(
            "def validate_id(id: str) -> str:\n"
            "    invalid_chars = [\"%\", \"$\", \";\", \":\", \"^\", \"*\"]\n"
            "    is_valid = not has_invalid_char(invalid_chars=invalid_chars, value=id)\n"
            "    if not is_valid:\n"
            "        raise ValueError(f\"id cannot have a special character: {invalid_chars}\")\n"
            "    return id"
        ),
        h.p("DI factory", h.H2),
        h.p(
            "<font face='Courier'>foundational_path_provider()</font> lives at "
            "<font face='Courier'>src/foundation/conf/conf.py:358</font>. It calls "
            "<font face='Courier'>_foundational_path_provider(...)</font> (line 364) "
            "which wires a "
            "<font face='Courier'>Neo4jFoundationalPathAdapter</font> (factory at "
            "<font face='Courier'>conf.py:147</font>) into a "
            "<font face='Courier'>FoundationalPathProvider</font>. The Neo4j "
            "<font face='Courier'>Driver</font> comes from the shared "
            "<font face='Courier'>_neo4j_driver()</font> helper."
        ),
        h.PageBreak(),
    ]

    # -- 2. query adapter ---------------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the two Cypher patterns", h.H1),
        h.p("src/foundation/infra/db/adapter/neo4j_foundational_path_adapter.py", h.PATH),
        *h.bullets([
            "Class constants (lines 18-19): <font face='Courier'>MAX_SUPPORTED_HOPS = 4</font> and <font face='Courier'>TOP_N = 10</font>.",
            "Public entry points: <font face='Courier'>find_shortest_path_by_start_id_and_end_id</font> (line 30) and <font face='Courier'>find_is_reachable_by_start_id_and_end_id</font> (line 38).",
            "Both call <font face='Courier'>_ensure_valid_n_hop_size_or_throw(n_hop)</font> (line 106) and <font face='Courier'>ensure_connection(self.driver)</font> before issuing Cypher.",
        ]),
        h.p("Shortest path Cypher (lines 89-96)", h.H2),
        h.code(
            "MATCH path = SHORTEST 10\n"
            "(startNode { node_id: $start_id })-[link]-{0,N}(endNode { node_id: $end_id })\n"
            "RETURN [n in nodes(path) | n.node_id] AS paths"
        ),
        *h.bullets([
            "<font face='Courier'>SHORTEST 10</font> is Neo4j 5's <i>k</i>-shortest-paths form &mdash; returns up to <font face='Courier'>TOP_N = 10</font> shortest paths, not just one.",
            "Each returned row is a list of <font face='Courier'>node_id</font> values along the path, projected by the comprehension <font face='Courier'>[n in nodes(path) | n.node_id]</font>.",
            "<font face='Courier'>N</font> in <font face='Courier'>{0,N}</font> is the <font face='Courier'>n_hop</font> argument, string-interpolated via <font face='Courier'>%s</font> (lines 93-96). It is not a Cypher parameter &mdash; that is why <font face='Courier'>n_hop</font> is range-checked at two layers (FastAPI <font face='Courier'>le=4</font> + <font face='Courier'>_ensure_valid_n_hop_size_or_throw</font>).",
        ]),
        h.p("Reachability Cypher (lines 98-104)", h.H2),
        h.code(
            "MATCH path = ANY\n"
            "(startNode { node_id: $start_id })-[link]-{0,N}(endNode { node_id: $end_id })\n"
            "RETURN toBoolean(count(path)) as is_reachable"
        ),
        *h.bullets([
            "<font face='Courier'>SHORTEST 10</font> enumerates paths; <font face='Courier'>ANY</font> short-circuits as soon as one path of length &le; N is found. Use reachability when you only need a yes/no &mdash; it is the cheaper query.",
            "<font face='Courier'>count(path)</font> wrapped in <font face='Courier'>toBoolean(...)</font> collapses to <font face='Courier'>true</font> if any row is produced, <font face='Courier'>false</font> otherwise.",
            "<font face='Courier'>_find_is_reachable</font> (line 62) reads <font face='Courier'>df[\"is_reachable\"][0]</font> &mdash; defaults to <font face='Courier'>False</font> if the driver returned <font face='Courier'>None</font>.",
        ]),
        h.p("Hop guard (lines 106-113)", h.H2),
        h.code(
            "def _ensure_valid_n_hop_size_or_throw(self, n_hop: int) -> int:\n"
            "    n_hop = max(1, n_hop)\n"
            "    max_supported_hops = Neo4jFoundationalPathAdapter.MAX_SUPPORTED_HOPS\n"
            "    if n_hop > max_supported_hops:\n"
            "        raise ValueError(\n"
            "            \"Request for N hop query of size {n_hop} exceeds max supported hops of {max_supported_hops}\"\n"
            "        )\n"
            "    return n_hop"
        ),
        h.p(
            "The Eugene graph is highly connected (the comment at line 17 spells "
            "it out). A 5-hop query can fan out into millions of paths, which is "
            "why the cap is <font face='Courier'>MAX_SUPPORTED_HOPS = 4</font> "
            "and the router declares <font face='Courier'>le=4</font> on the "
            "query param."
        ),
        h.PageBreak(),
    ]

    # -- 3. provider / response models -------------------------------------
    story += [
        h.p("3. Provider &amp; response models", h.H1),
        h.p("src/foundation/provider/foundational_path_provider.py", h.PATH),
        *h.bullets([
            "<font face='Courier'>FoundationalPathProvider</font> is a thin wrapper over the adapter &mdash; no business logic beyond DataFrame &rarr; dataclass shaping.",
            "<font face='Courier'>find_shortest_path_by_start_id_and_end_id</font> (line 26): if the adapter returns <font face='Courier'>None</font>, the provider returns an empty <font face='Courier'>ShortestPaths(count=0, paths=())</font> rather than raising (lines 32-39).",
            "Otherwise, each <font face='Courier'>paths</font> row from the DataFrame is converted to a tuple, and all rows are packed into a tuple-of-tuples for hashability (lines 41-52).",
            "<font face='Courier'>find_is_reachable_by_start_id_and_end_id</font> (line 54) simply forwards to the adapter, which already returns a <font face='Courier'>Reachability</font> dataclass.",
            "Both methods are decorated with <font face='Courier'>@log_time</font> &mdash; latency is logged per call.",
        ]),
        h.p("ShortestPaths dataclass", h.H2),
        h.p("src/foundation/model/shortest_paths.py", h.PATH),
        h.code(
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class ShortestPaths:\n"
            "    start_id: str\n"
            "    end_id:   str\n"
            "    max_hop:  int\n"
            "    count:    int\n"
            "    paths:    Tuple[Tuple[str, ...], ...]"
        ),
        h.p("Example response (curl GET /graph/path/start/DB00846/end/DB00538?n_hop=2)", h.H2),
        h.code(
            "{\n"
            "  \"start_id\": \"DB00846\",\n"
            "  \"end_id\":   \"DB00538\",\n"
            "  \"max_hop\":  2,\n"
            "  \"count\":    3,\n"
            "  \"paths\": [\n"
            "    [\"DB00846\", \"P12345\", \"DB00538\"],\n"
            "    [\"DB00846\", \"GENE_ABL1\", \"DB00538\"],\n"
            "    [\"DB00846\", \"PATHWAY_07\", \"DB00538\"]\n"
            "  ]\n"
            "}"
        ),
        h.p("Reachability dataclass", h.H2),
        h.p("src/foundation/model/reachability.py", h.PATH),
        h.code(
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class Reachability:\n"
            "    start_id:     str\n"
            "    end_id:       str\n"
            "    max_hop:      int\n"
            "    is_reachable: bool"
        ),
        h.p("Example response (curl GET /graph/reachability/start/DB00846/end/DB00538?n_hop=3)", h.H2),
        h.code(
            "{\n"
            "  \"start_id\":     \"DB00846\",\n"
            "  \"end_id\":       \"DB00538\",\n"
            "  \"max_hop\":      3,\n"
            "  \"is_reachable\": true\n"
            "}"
        ),
        h.PageBreak(),
    ]

    # -- 4. data source -----------------------------------------------------
    story += [
        h.p("4. Data source &mdash; where the graph comes from", h.H1),
        h.p(
            "The search-path route is strictly read-only. It owns no loader, "
            "no orchestrator, no ETL CLI &mdash; it queries whatever the upstream "
            "pipelines have already MERGEd into Neo4j."
        ),
        *h.bullets([
            "<b>Drug pipeline</b> &mdash; <font face='Courier'>src/ingest_drug_aliases.py</font> + drug node seed scripts under <font face='Courier'>bin/seed/*.cypher</font>.",
            "<b>Patent pipeline</b> &mdash; covered in <font face='Courier'>EUGENE_PATENT_FLOW_GUIDE.pdf</font>. Patent nodes carry <font face='Courier'>node_id</font> of the form <font face='Courier'>P&lt;number&gt;</font>.",
            "<b>Clinical trial pipeline</b> &mdash; ingest scripts under <font face='Courier'>src/ingest_*</font> for ClinicalTrials.gov sources.",
            "<b>PubMed pipeline</b> &mdash; literature ingest producing <font face='Courier'>:publication</font> nodes joined into the graph.",
            "All upstream ETL writers MERGE on <font face='Courier'>node_id</font>; the search-path queries rely on that property being unique and indexed.",
            "If <font face='Courier'>SHORTEST 10</font> returns 0 rows, the graph &mdash; not the route &mdash; is the most likely culprit. Verify the start/end nodes exist (see debugging walk).",
        ]),
        h.PageBreak(),
    ]

    # -- 5. debugging walk --------------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "Spin up the stack: <font face='Courier'>docker-compose up eugene_neo4j eugene_ws</font>. Make sure at least one ETL has populated the graph.",
            "Hit the shortest-path endpoint: <font face='Courier'>curl 'http://localhost:8000/graph/path/start/DB00846/end/DB00538?n_hop=2'</font>. Set a breakpoint at <font face='Courier'>src/foundation/router/search_path_router.py:58</font> to inspect the validated <font face='Courier'>start_id</font>, <font face='Courier'>end_id</font>, <font face='Courier'>n_hop</font>.",
            "Hit the reachability endpoint: <font face='Courier'>curl 'http://localhost:8000/graph/reachability/start/DB00846/end/DB00538?n_hop=3'</font>. Breakpoint at <font face='Courier'>search_path_router.py:98</font>.",
            "Sanity-check in Neo4j Browser that the nodes actually exist and confirm their labels: <font face='Courier'>MATCH (n {node_id: 'DB00846'}) RETURN labels(n), n</font>.",
            "Step into <font face='Courier'>Neo4jFoundationalPathAdapter._build_shortest_path_by_ids_query</font> (line 89) and copy the rendered Cypher string into Neo4j Browser with <font face='Courier'>$start_id</font> / <font face='Courier'>$end_id</font> set in the params panel &mdash; gives a feel for fan-out at each <font face='Courier'>n_hop</font>.",
            "Force a validation error: <font face='Courier'>curl 'http://localhost:8000/graph/path/start/foo%25bar/end/DB00538?n_hop=2'</font> &mdash; observe <font face='Courier'>validate_id</font> reject the <font face='Courier'>%</font> with HTTP 422. Repeat with <font face='Courier'>n_hop=5</font> to watch FastAPI's <font face='Courier'>le=4</font> guard fire.",
        ]),
        h.PageBreak(),
    ]

    # -- 6. reference index -------------------------------------------------
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "HTTP layer\n"
            "  src/foundation/router/search_path_router.py\n"
            "  src/foundation/router/validate_util.py            # validate_id L98\n\n"
            "DI factories\n"
            "  src/foundation/conf/conf.py                       # foundational_path_provider L358\n"
            "                                                    # neo4j_foundational_path_adapter L147\n\n"
            "Provider\n"
            "  src/foundation/provider/foundational_path_provider.py\n\n"
            "Neo4j adapter\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_path_adapter.py\n"
            "                                                    # SHORTEST 10  L89-96\n"
            "                                                    # ANY          L98-104\n"
            "                                                    # n_hop guard  L106-113\n\n"
            "Response models\n"
            "  src/foundation/model/shortest_paths.py\n"
            "  src/foundation/model/reachability.py\n\n"
            "Adjacent / upstream\n"
            "  src/ingest_drug_aliases.py                        # one of several ETL writers\n"
            "  bin/seed/*.cypher                                 # canonical node seeds\n"
        ),
    ]

    return story
