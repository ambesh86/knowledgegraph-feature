"""Flow guide section module for Eugene's n_hop_router.

Endpoint: GET /graph/relationship/start/{start_id}
Returns the variable-length sub-graph (up to N hops) anchored at a start node,
optionally bounded by an end node. This is the route Eugene's UI uses to
"expand" a context graph and the MCP tool ``fetch_node_relationships``
delegates to.

Built by the flow-guide generator -> ``docs/EUGENE_N_HOP_FLOW_GUIDE.pdf``.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_N_HOP_FLOW_GUIDE.pdf"
TITLE = "Eugene N-Hop Neighborhood - End-to-End Flow"


def build_story() -> list:
    story = []

    # ---- Title block ------------------------------------------------------
    story += [
        h.p("Eugene N-Hop Neighborhood &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: HTTP request &rarr; FastAPI router &rarr; "
            "Neo4j variable-length MATCH &rarr; DataFrame &rarr; adjacency-list "
            "Graph response",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how Eugene expands the "
            "neighborhood around a node &mdash; one or two hops out &mdash; "
            "and returns it as an adjacency-list subgraph. This is the "
            "read-side route behind the UI's <i>expand</i> action and the MCP "
            "tool that fetches relationships for a node. Every reference uses "
            "the form <font face='Courier'>path/to/file.py:line</font>.",
        ),
        h.p("Reference endpoints", h.H2),
        *h.bullets([
            "<font face='Courier'>GET /graph/relationship/start/{start_id}</font> &mdash; "
            "one-hop neighborhood (n_hop default 1).",
            "<font face='Courier'>GET /graph/relationship/start/{start_id}?n_hop=2</font> &mdash; "
            "two-hop neighborhood. Two is the hard ceiling: "
            "<font face='Courier'>n_hop</font> is constrained "
            "<font face='Courier'>gt=0, le=2</font> at the router and the adapter "
            "re-checks via <font face='Courier'>MAX_SUPPORTED_HOPS = 2</font>.",
            "<font face='Courier'>GET /graph/relationship/start/{start_id}?end_id=DB00538&amp;n_hop=2</font> &mdash; "
            "bounded path search: same query, but the end node is also pinned by "
            "<font face='Courier'>node_id</font>.",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "The Eugene graph is densely connected. The adapter comment "
            "(<font face='Courier'>neo4j_foundational_n_hop_adapter.py:17-19</font>) "
            "warns that a sufficient number of hops causes the entire graph to "
            "return &mdash; hence the <font face='Courier'>MAX_SUPPORTED_HOPS = 2</font> "
            "ceiling. Even at 2 hops, popular anchors (a common drug, a hub "
            "pathway) can blow past the provider's "
            "<font face='Courier'>MAX_RESULT_COUNT = 10_000</font> guard and raise. "
            "Treat this route as <i>local-neighborhood</i> expansion, not "
            "general traversal.",
        ),
        h.PageBreak(),
    ]

    # ---- 0. Schema --------------------------------------------------------
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p(
            "Unlike the drug-alias or patent routes, the n-hop query is "
            "<b>label-agnostic</b>. It matches any node label and any "
            "relationship type, anchored only by a "
            "<font face='Courier'>node_id</font> property on the start "
            "(and optionally end) node:",
        ),
        h.code(
            "(startNode { node_id: $start_id })-[r]-{0,N}(endNode [{ node_id: $end_id }])\n"
            "// any label on either side, any relationship type r"
        ),
        *h.bullets([
            "Node labels that appear in results are whatever exists in the "
            "graph: <font face='Courier'>:drug</font>, "
            "<font face='Courier'>:disease</font>, "
            "<font face='Courier'>:gene_or_protein</font>, "
            "<font face='Courier'>:pathway</font>, "
            "<font face='Courier'>:patent</font>, "
            "<font face='Courier'>:clinical_trial</font>, "
            "<font face='Courier'>:organization</font>, etc. The canonical set "
            "lives in " + h.c("src/foundation/model/foundational_node_enum.py") + ".",
            "Relationship types come from " + h.c("src/foundation/model/foundational_relationship_enum.py") +
            " &mdash; <font face='Courier'>HAS_DRUG_ALIAS</font>, "
            "<font face='Courier'>HAS_INDICATION</font>, "
            "<font face='Courier'>HAS_TARGET</font>, "
            "<font face='Courier'>HAS_PATENT</font>, etc.",
            "<b>Important</b>: the n-hop Cypher does <b>not</b> reference these "
            "enums. They constrain only what callers (e.g. the UI legend, the "
            "mapper consumers) <i>interpret</i> &mdash; the database query happily "
            "returns any label/type that exists.",
            "Paths only exist if upstream ETL has populated the graph. "
            "An empty subgraph response usually means the seed/ETL steps for "
            "that domain have not run, not that the route is broken.",
            "Idempotency in Eugene is by " + h.c("MERGE") + " on "
            "<font face='Courier'>node_id</font>; there are no Neo4j "
            "<font face='Courier'>CREATE CONSTRAINT</font> statements.",
        ]),
        h.PageBreak(),
    ]

    # ---- 1. HTTP entry ----------------------------------------------------
    story += [
        h.p("1. HTTP entry &mdash; router &amp; wiring", h.H1),
        h.p("<font face='Courier'>src/foundation/router/n_hop_router.py</font>", h.PATH),
        *h.bullets([
            "Module-load DI at line 21: <font face='Courier'>n_hop_provider = foundational_n_hop_provider()</font>. "
            "The provider (and its driver-backed adapter) is built once on import "
            "and reused for every request.",
            "Endpoint declared at lines 24-27: <font face='Courier'>@router.get(\"/relationship/start/{start_id}\", response_model_exclude_none=True)</font>. "
            "The router prefix " + h.c("/graph") + " is applied in the "
            "<font face='Courier'>APIRouter(prefix=\"/graph\", tags=[\"foundation\"])</font> "
            "declaration (lines 16-19).",
            "Path param <font face='Courier'>start_id</font> (lines 29-38) &mdash; "
            "annotated with " + h.c("AfterValidator(validate_id)") + ".",
            "Query param <font face='Courier'>end_id</font> (lines 39-47) &mdash; "
            "optional, same " + h.c("validate_id") + " AfterValidator.",
            "Query param <font face='Courier'>n_hop</font> (lines 48-56) &mdash; "
            "<font face='Courier'>int</font>, "
            "<font face='Courier'>gt=0, le=2</font>, default <font face='Courier'>1</font>. "
            "Pydantic rejects 0 and 3+ before the handler runs.",
            "Handler body (line 58-60) is a one-liner: "
            "<font face='Courier'>n_hop_provider.find_subgraph_by_start_id_and_end_id(start_id=start_id, end_id=end_id, n_hop=n_hop)</font>.",
        ]),
        h.p("Validators", h.H2),
        h.p("<font face='Courier'>src/foundation/router/validate_util.py</font>", h.PATH),
        h.code(
            "def validate_id(id: str) -> str:                              # line 98\n"
            "    # these are regex like characters that do not show up in our ids\n"
            "    invalid_chars = ['%', '$', ';', ':', '^', '*']\n"
            "    is_valid = not has_invalid_char(invalid_chars=invalid_chars, value=id)\n"
            "    if not is_valid:\n"
            "        raise ValueError(f\"id cannot have a special character: {invalid_chars}\")\n"
            "    return id"
        ),
        h.p(
            "This is a defense-in-depth check &mdash; the underlying Cypher uses "
            "parameterised " + h.c("$start_id") + " / " + h.c("$end_id") +
            " so injection is not the threat. The validator exists to fail "
            "fast on obvious garbage ids (URL-encoded payloads, regex meta in "
            "logs) before the driver round-trips to Neo4j.",
        ),
        h.p("DI factories", h.H2),
        h.p("<font face='Courier'>src/foundation/conf/conf.py</font>", h.PATH),
        *h.bullets([
            "<font face='Courier'>neo4j_foundational_n_hop_adapter()</font> at "
            "lines 137-138 &mdash; pulls the shared driver via "
            "<font face='Courier'>_neo4j_driver()</font>.",
            "<font face='Courier'>_neo4j_foundational_n_hop_adapter(driver)</font> "
            "at lines 141-144 &mdash; pure constructor over the driver.",
            "<font face='Courier'>foundational_n_hop_provider()</font> at "
            "lines 341-345 &mdash; composes the adapter with "
            "<font face='Courier'>graph_mapper()</font>.",
        ]),
        h.p("First breakpoint", h.H2),
        h.p(
            "Set a breakpoint on " + h.c("src/foundation/router/n_hop_router.py:28") +
            " (the <font face='Courier'>async def find_n_hop</font> signature). "
            "Hit the endpoint with curl and inspect the bound parameters "
            "<i>after</i> validators have run &mdash; you should see "
            "<font face='Courier'>start_id</font>, "
            "<font face='Courier'>end_id</font>, "
            "<font face='Courier'>n_hop</font> all as clean Python values.",
        ),
        h.PageBreak(),
    ]

    # ---- 2. Query adapter -------------------------------------------------
    story += [
        h.p("2. Query adapter &mdash; the variable-length Cypher", h.H1),
        h.p("<font face='Courier'>src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py</font>", h.PATH),
        h.p(
            "Public entry: <font face='Courier'>collect_by_start_id_and_end_id</font> "
            "(line 38). The sequence is straightforward: clamp "
            "<font face='Courier'>n_hop</font>, ensure the driver is alive, "
            "build the Cypher, run it, return a DataFrame.",
        ),
        h.code(
            "def collect_by_start_id_and_end_id(self, start_id, page, page_size,\n"
            "                                   end_id=None, n_hop=2):       # line 38\n"
            "    n_hop = self._ensure_valid_n_hop_size_or_throw(n_hop)        # MAX_SUPPORTED_HOPS = 2\n"
            "    ensure_connection(self.driver)\n"
            "    return self._collect_n_hop_by_id(\n"
            "        start_id=start_id, end_id=end_id, n_hop=n_hop,\n"
            "        page=page, page_size=page_size,\n"
            "    )"
        ),
        h.p("The Cypher (built around lines 138-147 + 158-170)", h.H2),
        h.code(
            "MATCH (startNode { node_id: $start_id })-[r]-{0,N}(endNode{ node_id: $end_id })\n"
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
            "<b>N is interpolated</b>, not parameterised: "
            "<font face='Courier'>\"%s\" % n_hop</font> in "
            "<font face='Courier'>_build_n_hop_by_id_query</font> (line 138). "
            "Neo4j requires variable-length pattern bounds to be literals, so "
            "they cannot be bound via " + h.c("$params") + ". The "
            "<font face='Courier'>n_hop</font> value is already clamped by both "
            "the FastAPI " + h.c("le=2") + " and the adapter's "
            "<font face='Courier'>_ensure_valid_n_hop_size_or_throw</font> guard "
            "(line 149), so the substitution is safe.",
            "<b>Optional end_id branch</b>: when "
            "<font face='Courier'>end_id is None</font>, line 145 emits "
            "<font face='Courier'>(endNode)</font> with no property filter &mdash; "
            "i.e. <i>any</i> reachable node within N hops. When provided, the "
            "<font face='Courier'>{ node_id: $end_id }</font> clause pins the "
            "far end and the query becomes a bounded path search.",
            "<b>The <font face='Courier'>-[r]-{0,N}</font> form</b> walks 0 to N "
            "hops in either direction (undirected). The lower bound "
            "<font face='Courier'>0</font> means the start node itself is "
            "included in the result (as a self-row), which is why the mapper "
            "sees the anchor in its uniq-ids set even when no edges exist.",
            "<b>Pagination</b> via SKIP/LIMIT comes from "
            "<font face='Courier'>Pagination.calculate_limit_and_offset(page, page_size)</font> in "
            + h.c("src/foundation/infra/db/util/pagination.py") + ". The "
            "router does not currently expose <font face='Courier'>page</font> / "
            "<font face='Courier'>page_size</font> &mdash; the provider passes "
            "<font face='Courier'>page=1, page_size=MAX_RESULT_COUNT=10000</font>, "
            "so in practice every call asks for the whole 10k window.",
            "<b><font face='Courier'>ensure_connection(self.driver)</font></b> "
            "(imported from " + h.c("graph.util.util") + ") verifies the Neo4j "
            "driver can ping before issuing the query &mdash; useful for surfacing "
            "auth/network failures as a clear error instead of a hung session.",
            "<b>Result transformer</b>: "
            "<font face='Courier'>result_transformer_=neo4j.Result.to_df</font> "
            "(line 118) hands the work to the Neo4j driver's built-in pandas "
            "converter. The adapter returns a DataFrame &mdash; no row-by-row "
            "Python loop on the hot path.",
        ]),
        h.PageBreak(),
    ]

    # ---- 3. Mapper / response model ---------------------------------------
    story += [
        h.p("3. Mapper &amp; response model", h.H1),
        h.p("<font face='Courier'>src/foundation/provider/foundational_n_hop_provider.py</font>", h.PATH),
        h.p(
            "The provider sits between router and adapter. After the DataFrame "
            "comes back it enforces "
            "<font face='Courier'>MAX_RESULT_COUNT = 10_000</font> "
            "(line 17): if the DataFrame has more rows than that, the call "
            "<i>raises</i> rather than truncating, on the theory that a 10k+ "
            "subgraph is almost certainly the wrong answer and the caller "
            "should pick a less central anchor.",
        ),
        h.code(
            "df = self.neo4j_foundational_n_hop_adapter.collect_by_start_id_and_end_id(...)\n"
            "self._ensure_result_size_or_raise(df)        # ValueError if > 10_000 rows\n"
            "return self.graph_mapper.map(df=df)"
        ),
        h.p("<font face='Courier'>src/foundation/mapper/graph_mapper.py</font>", h.PATH),
        h.p(
            "<font face='Courier'>GraphMapper.map()</font> (line 32) turns the "
            "row-shaped DataFrame into an adjacency-list "
            "<font face='Courier'>Graph</font> in two passes:",
        ),
        *h.bullets([
            "<b>Unique nodes</b> (<font face='Courier'>_build_uniq_nodes</font>, "
            "line 52): union of <font face='Courier'>startId</font> / "
            "<font face='Courier'>endId</font> columns, then for each id pick "
            "the first row in which it appears and read its name + labels.",
            "<b>Relationships</b> (<font face='Courier'>_build_relationships</font>, "
            "line 96): group rows by <font face='Courier'>startId</font>; for each "
            "start node build a set of "
            "<font face='Courier'>Relationship(id=endId, rel=relType)</font>.",
            "DataFrame column names come from " + h.c("src/foundation/mapper/const.py") +
            ": " + h.c("startId, startName, startLabels, endId, endName, endLabels, relType") + ".",
        ]),
        h.p("Response dataclasses", h.H2),
        h.code(
            "# src/foundation/model/graph/graph.py\n"
            "@dataclass(frozen=True, unsafe_hash=True)\n"
            "class Graph:\n"
            "    node_count:    int\n"
            "    nodes:         set[Node]\n"
            "    relationships: dict[str, set[Relationship]]\n\n"
            "# src/foundation/model/graph/node.py\n"
            "class Node:\n"
            "    id:     str\n"
            "    value:  str            # node_name\n"
            "    labels: frozenset[str] # sorted, frozen for hashability\n\n"
            "# src/foundation/model/graph/relationship.py\n"
            "class Relationship:\n"
            "    id:  str   # the OTHER endpoint's node_id\n"
            "    rel: str   # relType, e.g. 'has_target'"
        ),
        h.p("Example JSON (FastAPI serialisation)", h.H2),
        h.code(
            "{\n"
            "  \"node_count\": 3,\n"
            "  \"nodes\": [\n"
            "    {\"id\": \"DB00846\", \"value\": \"Felodipine\",  \"labels\": [\"drug\"]},\n"
            "    {\"id\": \"P35968\",  \"value\": \"VEGFR-2\",    \"labels\": [\"gene_or_protein\"]},\n"
            "    {\"id\": \"DB00538\", \"value\": \"Sorafenib\",   \"labels\": [\"drug\"]}\n"
            "  ],\n"
            "  \"relationships\": {\n"
            "    \"DB00846\": [{\"id\": \"P35968\",  \"rel\": \"has_target\"}],\n"
            "    \"DB00538\": [{\"id\": \"P35968\",  \"rel\": \"has_target\"}]\n"
            "  }\n"
            "}"
        ),
        h.p(
            "<i>Note</i>: " + h.c("response_model_exclude_none=True") + " on the "
            "route trims null fields. Sets are emitted as JSON arrays.",
        ),
        h.PageBreak(),
    ]

    # ---- 4. Data source ---------------------------------------------------
    story += [
        h.p("4. Data source &mdash; where the edges come from", h.H1),
        h.p(
            "This route is <b>purely read-side</b>. It does not create or "
            "merge anything. For a meaningful subgraph to come back, upstream "
            "ETL has to have populated nodes and "
            "<font face='Courier'>:relationship</font> edges. The relevant CLIs:",
        ),
        *h.bullets([
            h.c("src/download_patents.py") + " &mdash; pulls USPTO / patent "
            "metadata and attaches <font face='Courier'>:patent</font> nodes to "
            "their assignees and target drugs via "
            "<font face='Courier'>HAS_PATENT</font> edges.",
            h.c("src/ingest_drug_aliases.py") + " &mdash; the alias ETL "
            "covered in <i>EUGENE_DRUG_ALIAS_FLOW_GUIDE</i>. Adds "
            "<font face='Courier'>:drug_product</font> and "
            "<font face='Courier'>:drug_synonym</font> nodes connected by "
            "<font face='Courier'>HAS_DRUG_ALIAS</font>.",
            h.c("src/download_clinicaltrail.py") + " &mdash; ingests "
            "clinicaltrials.gov records; connects "
            "<font face='Courier'>:clinical_trial</font> to its drug + "
            "indication.",
            h.c("src/download_pubmed.py") + " &mdash; PubMed publication "
            "ingest; attaches <font face='Courier'>:publication</font> nodes "
            "and citation edges.",
            "Plus the seed Cypher files under " + h.c("bin/seed/") + " which "
            "create the canonical <font face='Courier'>:drug</font>, "
            "<font face='Courier'>:disease</font>, "
            "<font face='Courier'>:gene_or_protein</font>, "
            "<font face='Courier'>:pathway</font>, "
            "<font face='Courier'>:organization</font> nodes that everything "
            "else hangs off.",
        ]),
        h.p(
            "If a fresh database returns an empty Graph for a known good "
            "<font face='Courier'>start_id</font>, the failure is almost "
            "always upstream &mdash; the seed Cypher or one of the ingest CLIs "
            "did not run for the domain you are testing.",
        ),
        h.p("How to confirm there is anything to traverse", h.H2),
        h.code(
            "# In neo4j-browser:\n"
            "MATCH (n { node_id: 'DB00846' }) RETURN n, labels(n)\n"
            "MATCH (n { node_id: 'DB00846' })-[r]-(m) RETURN type(r), count(*)\n"
            "// If the second query is empty, your n-hop response will be too."
        ),
        h.PageBreak(),
    ]

    # ---- 5. Debug walk ----------------------------------------------------
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "<b>Bring the stack up</b>: "
            "<font face='Courier'>docker-compose up eugene_neo4j eugene_ws</font>. "
            "Confirm the seed Cypher has run (see section 4) so there is "
            "something to traverse.",
            "<b>Sanity-curl</b>: "
            "<font face='Courier'>curl -s '$EUGENE_WS/graph/relationship/start/DB00846?n_hop=1' | jq</font>. "
            "Expect a non-empty <font face='Courier'>nodes</font> array and "
            "the start id as a key in <font face='Courier'>relationships</font>.",
            "<b>Breakpoint at the router</b>: " +
            h.c("src/foundation/router/n_hop_router.py:28") +
            " (signature of <font face='Courier'>find_n_hop</font>). Inspect "
            "<font face='Courier'>start_id</font>, "
            "<font face='Courier'>end_id</font>, "
            "<font face='Courier'>n_hop</font> after FastAPI validation.",
            "<b>Validator</b>: drop a breakpoint at " +
            h.c("src/foundation/router/validate_util.py:98") +
            " and try a bad id like "
            "<font face='Courier'>'DB008%46'</font> &mdash; you should see the "
            "ValueError fire before the handler runs.",
            "<b>Connection guard</b>: step into " +
            h.c("neo4j_foundational_n_hop_adapter.py:47") +
            " (the " + h.c("ensure_connection(self.driver)") + " call). If "
            "Neo4j is down or auth is wrong, this is where you will see it &mdash; "
            "not later in result mapping.",
            "<b>Inspect the assembled Cypher</b>: breakpoint at "
            "<font face='Courier'>_collect_n_hop</font> "
            "(<font face='Courier'>neo4j_foundational_n_hop_adapter.py:112</font>). "
            "Copy the <font face='Courier'>query</font> string + "
            "<font face='Courier'>params</font> dict into Neo4j Browser to feel "
            "what it returns. Confirm the "
            "<font face='Courier'>-[r]-{0,N}</font> bound matches your "
            "<font face='Courier'>n_hop</font> value.",
            "<b>Mapper build</b>: breakpoint at " +
            h.c("src/foundation/mapper/graph_mapper.py:32") +
            " (<font face='Courier'>GraphMapper.map</font>). Watch "
            "<font face='Courier'>uniq_ids</font> grow, then the "
            "<font face='Courier'>relationships</font> dict. If a row from the "
            "DataFrame is missing from the output, it is either de-duped by "
            "set semantics or its id is null (drop site at "
            "<font face='Courier'>_build_uniq_nodes</font> line 59).",
            "<b>Response inspection</b>: confirm the final "
            "<font face='Courier'>Graph</font>'s "
            "<font face='Courier'>node_count</font> equals "
            "<font face='Courier'>len(nodes)</font> and that every key in "
            "<font face='Courier'>relationships</font> is also present in "
            "<font face='Courier'>nodes</font>.",
        ]),
        h.PageBreak(),
    ]

    # ---- 6. Reference index ----------------------------------------------
    story += [
        h.p("6. Reference index", h.H1),
        h.code(
            "Schema\n"
            "  src/foundation/model/foundational_node_enum.py          # label catalogue (informational)\n"
            "  src/foundation/model/foundational_relationship_enum.py  # rel-type catalogue (informational)\n"
            "  # NOTE: the n-hop Cypher is label-agnostic; enums constrain callers, not the query\n\n"
            "Router & wiring\n"
            "  src/foundation/router/n_hop_router.py                   # endpoint, line 21 DI, line 28 handler\n"
            "  src/foundation/router/validate_util.py                  # validate_id, line 98-104\n"
            "  src/foundation/conf/conf.py                             # factories L137-144, L341-345\n\n"
            "Read path\n"
            "  src/foundation/provider/foundational_n_hop_provider.py  # MAX_RESULT_COUNT=10_000, line 17\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_n_hop_adapter.py  # MAX_SUPPORTED_HOPS=2, Cypher L138-170\n"
            "  src/foundation/infra/db/util/pagination.py              # SKIP/LIMIT helper\n"
            "  src/foundation/mapper/graph_mapper.py                   # DataFrame -> Graph\n"
            "  src/foundation/mapper/const.py                          # DataFrame column names\n"
            "  src/foundation/model/graph/graph.py                     # Graph dataclass\n"
            "  src/foundation/model/graph/node.py                      # Node dataclass\n"
            "  src/foundation/model/graph/relationship.py              # Relationship dataclass\n\n"
            "ETL (for graph data)\n"
            "  src/download_patents.py\n"
            "  src/ingest_drug_aliases.py\n"
            "  src/download_clinicaltrail.py\n"
            "  src/download_pubmed.py\n"
            "  bin/seed/*.cypher                                       # canonical node seed\n"
        ),
    ]

    return story
