"""ReportLab section: Eugene generic count route end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 7-9 PDF pages.
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_COUNT_FLOW_GUIDE.pdf"
TITLE = "Eugene Count Route - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------- title --------------------------------- #
    story += [
        h.p("Eugene Count Route &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: ETL-seeded Neo4j labels &rarr; FastAPI router &rarr; "
            "label validator &rarr; Cypher <font face='Courier'>count(n)</font> &rarr; JSON response",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to understand how the generic "
            "<font face='Courier'>GET /count/{label}</font> endpoint resolves a user-supplied "
            "label string into a Neo4j node label and returns the total node count. "
            "This is the simplest read endpoint in Eugene &mdash; one path parameter, one "
            "Cypher, one JSON object &mdash; which makes it a useful reference for the "
            "validator + adapter + router pattern used everywhere else. Every reference "
            "uses the form <font face='Courier'>path/to/file.py:line</font>.",
        ),
        h.p("Reference endpoint", h.H2),
        *h.bullets([
            "<font face='Courier'>GET /count/{label}</font> &mdash; e.g. "
            "<font face='Courier'>/count/drug</font>, <font face='Courier'>/count/disease</font>, "
            "<font face='Courier'>/count/gene_protein</font>.",
            "Response: <font face='Courier'>{ \"count\": &lt;int&gt;, \"label\": \"&lt;normalized&gt;\" }</font>.",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "The route relies on whatever node labels the ETL pipelines have produced "
            "in Neo4j. There are no constraints or uniqueness rules &mdash; a label that "
            "exists in the enum but has never been ingested simply returns "
            "<font face='Courier'>count = 0</font>. The <font face='Courier'>Label</font> "
            "Pydantic enum (the validator) is intentionally narrower than the full "
            "<font face='Courier'>FoundationalNodeEnum</font>: only the foundational "
            "biomedical labels are exposed via this endpoint; counts for patents, "
            "pubmed documents, organizations, etc. live behind dedicated routers.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 0. schema (read this first) ------------------- #
    story += [
        h.p("0. Schema (read this first)", h.H1),
        h.p("The count endpoint touches a single node label and no relationships:"),
        h.code(
            "(:anatomy             { node_id, node_name, ... })\n"
            "(:biological_process  { node_id, node_name, ... })\n"
            "(:disease             { node_id, node_name, ... })\n"
            "(:drug                { node_id, node_name, drug_bank_id, ... })\n"
            "(:effect_phenotype    { node_id, node_name, ... })\n"
            "(:exposure            { node_id, node_name, ... })\n"
            "(:gene_protein        { node_id, node_name, ... })\n"
            "(:molecular_function  { node_id, node_name, ... })\n"
            "(:pathway             { node_id, node_name, ... })"
        ),
        *h.bullets([
            "Permitted labels are enumerated by <font face='Courier'>Label</font> in "
            "<font face='Courier'>src/foundation/router/model/label.py</font> &mdash; nine "
            "values: anatomy, biological_process, disease, drug, effect_phenotype, "
            "exposure, gene_protein, molecular_function, pathway.",
            "Each is mapped back to a <font face='Courier'>FoundationalNodeEnum</font> "
            "entry by <font face='Courier'>str_to_label_enum()</font> in "
            "<font face='Courier'>src/foundation/router/validate_util.py:107-111</font>. "
            "The enum tuple is <font face='Courier'>(int_id, lowercase_label)</font>; the "
            "second element is what gets interpolated into Cypher.",
            "No relationships are walked. The Cypher is "
            "<font face='Courier'>MATCH (n:`&lt;label&gt;`) RETURN count(n)</font>.",
            "Like the rest of Eugene there are no Neo4j CREATE CONSTRAINTs &mdash; the "
            "count is simply whatever currently exists with the requested label.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 1. HTTP entry --------------------------------- #
    story += [
        h.p("1. HTTP entry", h.H1),
        h.p("<font face='Courier'>src/foundation/router/count_router.py</font>", h.PATH),
        *h.bullets([
            "Router prefix <font face='Courier'>/count</font>, tag "
            "<font face='Courier'>foundation</font> (lines 18-21).",
            "Module-load DI at line 23: "
            "<font face='Courier'>foundational_node_count_adapter = neo4j_foundational_node_count_adapter()</font> "
            "&mdash; one driver-bound adapter per process, reused across requests.",
            "Single route: <font face='Courier'>GET /count/{label}</font> (line 26-28). "
            "<font face='Courier'>response_model=dict[str, int | str]</font> with "
            "<font face='Courier'>response_model_exclude_none=True</font>.",
            "Path param is <font face='Courier'>label: Label</font> (the Pydantic enum) "
            "with FastAPI <font face='Courier'>Path(min_length=1, max_length=64)</font> "
            "and an <font face='Courier'>AfterValidator(validate_label)</font> &mdash; so an "
            "unknown string is rejected as a 422 before it ever touches Neo4j.",
        ]),
        h.p("Verbatim handler (count_router.py:26-42)", h.H2),
        h.code(
            "@router.get(\n"
            "    \"/{label}\", response_model=dict[str, int | str], response_model_exclude_none=True\n"
            ")\n"
            "async def count_by_label(\n"
            "    label: Annotated[\n"
            "        Label,\n"
            "        Path(\n"
            "            description=\"The node type to count. e.g. drug, disease\",\n"
            "            max_length=64,\n"
            "            min_length=1,\n"
            "        ),\n"
            "        AfterValidator(validate_label),\n"
            "    ],\n"
            "):\n"
            "    label_value = label.value[1]\n"
            "    count = foundational_node_count_adapter.count_all_by_label(label_value)\n"
            "    return {\"count\": count, \"label\": label_value}"
        ),
        h.p("Validator (validate_util.py:13-21)", h.H2),
        h.code(
            "def validate_label(label: Label) -> FoundationalNodeEnum:\n"
            "    logger.info(f\"validating label: {label}\")\n"
            "    is_valid = label in Label\n"
            "    if not is_valid:\n"
            "        valid_labels = [el.value for el in list(Label)]\n"
            "        err_msg = f\"invalid label {label}. Valid labels: {valid_labels}\"\n"
            "        raise ValueError(err_msg)\n"
            "    node_type = str_to_label_enum(label.value)\n"
            "    return node_type"
        ),
        h.p(
            "Subtlety: <font face='Courier'>validate_label</font> returns a "
            "<font face='Courier'>FoundationalNodeEnum</font>, but the route signature is "
            "still typed as <font face='Courier'>Label</font>. Because the handler reads "
            "<font face='Courier'>label.value[1]</font> &mdash; the second tuple element &mdash; the "
            "code happens to work whether the runtime object is the narrow "
            "<font face='Courier'>Label</font> enum (value is a plain string, so "
            "<font face='Courier'>[1]</font> would actually grab the second character) or "
            "the broader <font face='Courier'>FoundationalNodeEnum</font> (value is a "
            "tuple). In practice FastAPI runs the <font face='Courier'>AfterValidator</font> "
            "after coercion, and the validator returns the enum &mdash; so "
            "<font face='Courier'>label.value[1]</font> is the lowercase label string. "
            "Worth knowing when stepping through.",
        ),
        h.p("Registration", h.H2),
        h.p(
            "<font face='Courier'>src/eugene_ws.py:36, 61</font> &mdash; "
            "<font face='Courier'>add_routers()</font> imports the module as "
            "<font face='Courier'>foundation_count_router</font> and includes it via "
            "<font face='Courier'>app.include_router(router.router)</font>.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 2. Query adapter ------------------------------ #
    story += [
        h.p("2. Query adapter (verbatim Cypher)", h.H1),
        h.p(
            "<font face='Courier'>src/foundation/infra/db/adapter/neo4j_foundational_node_count_adapter.py</font>",
            h.PATH,
        ),
        *h.bullets([
            "Constructed in <font face='Courier'>src/foundation/conf/conf.py:99-106</font>: "
            "<font face='Courier'>neo4j_foundational_node_count_adapter()</font> returns a "
            "<font face='Courier'>Neo4jFoundationalNodeCountAdapter</font> built around the "
            "shared <font face='Courier'>_neo4j_driver()</font>.",
            "Public entry: <font face='Courier'>count_all_by_label(label: str) -&gt; int</font> "
            "(line 22). Calls <font face='Courier'>ensure_connection(self.driver)</font> "
            "first &mdash; the standard Eugene pattern for transparently reconnecting a stale "
            "Neo4j driver before issuing a query.",
            "Builds the Cypher with <font face='Courier'>_build_count_all_by_label()</font> "
            "(line 40) and executes via "
            "<font face='Courier'>driver.execute_query(query_=query, result_transformer_=neo4j.Result.single)</font> "
            "&mdash; one record back, take the <font face='Courier'>count</font> column.",
            "Errors from the driver (<font face='Courier'>DriverError</font>, "
            "<font face='Courier'>Neo4jError</font>) are logged and re-raised; FastAPI "
            "renders them as 500s.",
        ]),
        h.p("Cypher (neo4j_foundational_node_count_adapter.py:40-47)", h.H2),
        h.code(
            "MATCH (n:`%s`)\n"
            "    RETURN count(n) as count"
        ),
        h.p(
            "The <font face='Courier'>%s</font> is filled with the lowercase label string "
            "via Python <font face='Courier'>%</font>-formatting &mdash; <b>not</b> a "
            "parameterised query. That is safe here only because the value has already "
            "been constrained to the nine-entry <font face='Courier'>Label</font> enum by "
            "<font face='Courier'>validate_label</font>; any other call site that wanted "
            "to reuse this adapter would need to apply the same validation before "
            "calling. The commented-out "
            "<font face='Courier'>normalize_node_label(label)</font> in the source is a "
            "reminder that earlier iterations normalised the label here &mdash; "
            "responsibility now lives in the router-level validator.",
        ),
        h.p("Execute path (lines 26-38)", h.H2),
        h.code(
            "def _count_all_by_label(self, label: str) -&gt; int:\n"
            "    query = self._build_count_all_by_label(label)\n"
            "    logger.info(f\"count all: {query}\")\n"
            "    try:\n"
            "        record = self.driver.execute_query(\n"
            "            query_=query,\n"
            "            result_transformer_=neo4j.Result.single,\n"
            "        )\n"
            "        logger.info(f\"cypher response: {record}\")\n"
            "        return record[\"count\"]\n"
            "    except (DriverError, Neo4jError) as exception:\n"
            "        logging.error(\"%s raised an error: \\n%s\", query, exception)\n"
            "        raise exception"
        ),
        h.PageBreak(),
    ]

    # --------------------- 3. Mapper / response model -------------------- #
    story += [
        h.p("3. Mapper / response model", h.H1),
        h.p(
            "Unlike the more elaborate routes (drug-alias, n-hop, facts), the count "
            "endpoint has no mapper class &mdash; the handler builds the JSON object "
            "inline. The response is typed at the FastAPI layer as "
            "<font face='Courier'>dict[str, int | str]</font>:",
        ),
        h.code(
            "@router.get(\n"
            "    \"/{label}\", response_model=dict[str, int | str], response_model_exclude_none=True\n"
            ")"
        ),
        h.p("Example response", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"count\": 4173,\n"
            "  \"label\": \"drug\"\n"
            "}"
        ),
        *h.bullets([
            "<font face='Courier'>count</font> &mdash; integer; the result of "
            "<font face='Courier'>count(n)</font> in Neo4j. Zero is a perfectly valid "
            "answer (label exists in the enum but no nodes have been ingested with that "
            "label yet).",
            "<font face='Courier'>label</font> &mdash; the lowercase, normalized label "
            "string actually used in the Cypher. Echoing it back lets clients confirm "
            "what they queried (relevant because FastAPI is case-sensitive on the path "
            "param but the validator is case-fixed via the enum).",
            "Errors: a label outside the <font face='Courier'>Label</font> enum yields a "
            "<font face='Courier'>422 Unprocessable Entity</font> with the standard "
            "FastAPI validation envelope; a driver error yields a "
            "<font face='Courier'>500</font>.",
        ]),
        h.p("Example error (422)", h.H2),
        h.code(
            "$ curl -sS http://localhost:8000/count/bogus | jq .\n"
            "{\n"
            "  \"detail\": [\n"
            "    {\n"
            "      \"type\": \"enum\",\n"
            "      \"loc\": [\"path\", \"label\"],\n"
            "      \"msg\": \"Input should be 'anatomy', 'biological_process', ...\",\n"
            "      \"input\": \"bogus\"\n"
            "    }\n"
            "  ]\n"
            "}"
        ),
        h.PageBreak(),
    ]

    # --------------------- 4. Data source / ETL -------------------------- #
    story += [
        h.p("4. Data source / ETL", h.H1),
        h.p(
            "The count route is purely read-side &mdash; it has no ETL of its own. The "
            "numbers it returns are a side effect of every other ingest pipeline that "
            "writes nodes carrying one of the nine permitted labels.",
        ),
        h.p("Where the labels come from", h.H2),
        *h.bullets([
            "<font face='Courier'>:drug</font> nodes &mdash; seeded by "
            "<font face='Courier'>bin/seed/csl_behring_assets.cypher</font>, "
            "<font face='Courier'>bin/seed/biogen_assets.cypher</font>, and the "
            "DrugBank/PrimeKG ingests under <font face='Courier'>src/ingest_*.py</font>. "
            "Drug aliases (<font face='Courier'>:drug_product</font>, "
            "<font face='Courier'>:drug_synonym</font>) are <i>not</i> counted by this "
            "route &mdash; only the canonical <font face='Courier'>:drug</font> label is in "
            "the <font face='Courier'>Label</font> enum.",
            "<font face='Courier'>:disease</font>, <font face='Courier'>:gene_protein</font>, "
            "<font face='Courier'>:pathway</font>, <font face='Courier'>:anatomy</font>, "
            "<font face='Courier'>:biological_process</font>, "
            "<font face='Courier'>:molecular_function</font>, "
            "<font face='Courier'>:effect_phenotype</font>, "
            "<font face='Courier'>:exposure</font> &mdash; loaded by the PrimeKG / Hetionet "
            "foundational ingest scripts; see the loaders under "
            "<font face='Courier'>src/foundation/load/</font>.",
            "Patents, pubmed documents, organizations, clinical trials, etc. have "
            "their own count routers "
            "(<font face='Courier'>patent_count_router.py</font>, "
            "<font face='Courier'>pubmed_count_router.py</font>) registered alongside "
            "this one in <font face='Courier'>eugene_ws.py:36-73</font>.",
        ]),
        h.p("Enum source of truth", h.H2),
        h.code(
            "src/foundation/model/foundational_node_enum.py\n"
            "  ANATOMY            = 1,  'anatomy'\n"
            "  BIOLOGICAL_PROCESS = 2,  'biological_process'\n"
            "  DISEASE            = 7,  'disease'\n"
            "  DRUG               = 8,  'drug'\n"
            "  EFFECT_PHENOTYPE   = 9,  'effect_phenotype'\n"
            "  EXPOSURE           = 10, 'exposure'\n"
            "  GENE_PROTEIN       = 12, 'gene_protein'\n"
            "  MOLECULAR_FUNCTION = 14, 'molecular_function'\n"
            "  PATHWAY            = 15, 'pathway'"
        ),
        h.p(
            "<font face='Courier'>FoundationalRelationshipEnum</font> "
            "(<font face='Courier'>src/foundation/model/foundational_relationship_enum.py</font>) "
            "is unused by this route &mdash; <font face='Courier'>count(n)</font> never "
            "traverses an edge.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 5. Debugging walk ----------------------------- #
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            "Bring the stack up: "
            "<font face='Courier'>docker-compose up eugene_neo4j eugene_ws</font>. Confirm "
            "the foundational seed has been applied "
            "(<font face='Courier'>cypher-shell &lt; bin/seed/csl_behring_assets.cypher</font>) "
            "so at least some <font face='Courier'>:drug</font> nodes exist.",
            "Smoke test the happy path: "
            "<font face='Courier'>curl -sS http://localhost:8000/count/drug | jq .</font>. "
            "Expect <font face='Courier'>{\"count\": &gt;0, \"label\": \"drug\"}</font>.",
            "Force a 422: "
            "<font face='Courier'>curl -sS http://localhost:8000/count/bogus</font>. "
            "Breakpoint at <font face='Courier'>count_router.py:29</font> &mdash; the "
            "<font face='Courier'>AfterValidator(validate_label)</font> fires first; you "
            "should never reach the handler body for an invalid label.",
            "Step into the adapter: breakpoint at "
            "<font face='Courier'>neo4j_foundational_node_count_adapter.py:40</font>. "
            "Inspect the assembled Cypher string &mdash; copy/paste it into Neo4j Browser to "
            "confirm the count matches.",
            "Watch the logs &mdash; the adapter emits "
            "<font face='Courier'>logger.info(f\"count all: {query}\")</font> and "
            "<font face='Courier'>logger.info(f\"cypher response: {record}\")</font>; "
            "<font face='Courier'>grep 'count all'</font> on the eugene_ws container is "
            "usually the fastest way to see what was actually run.",
            "Sanity-check the enum mapping: in a Python REPL, "
            "<font face='Courier'>from foundation.router.validate_util import str_to_label_enum; "
            "str_to_label_enum('gene_protein')</font> should return "
            "<font face='Courier'>FoundationalNodeEnum.GENE_PROTEIN</font>; passing a "
            "value not in any enum tuple raises <font face='Courier'>ValueError</font>.",
        ]),
        h.Spacer(1, 10),

        # ----------------- 6. Reference index ---------------------------- #
        h.p("6. Reference index", h.H1),
        h.code(
            "Schema\n"
            "  src/foundation/router/model/label.py                  # the 9-value Label enum\n"
            "  src/foundation/model/foundational_node_enum.py        # full label registry\n"
            "  src/foundation/model/foundational_relationship_enum.py # unused by /count\n\n"
            "HTTP entry\n"
            "  src/foundation/router/count_router.py                 # GET /count/{label}\n"
            "  src/foundation/router/validate_util.py                # validate_label (L13), str_to_label_enum (L107)\n"
            "  src/eugene_ws.py                                      # add_routers() L36, include L61\n\n"
            "Adapter / Cypher\n"
            "  src/foundation/infra/db/adapter/neo4j_foundational_node_count_adapter.py\n"
            "  src/foundation/conf/conf.py                           # factory L99-106\n"
            "  src/graph/util/util.py                                # ensure_connection\n\n"
            "Related count endpoints\n"
            "  src/foundation/router/patent_count_router.py\n"
            "  src/foundation/router/pubmed_count_router.py\n\n"
            "Seed data feeding the counts\n"
            "  bin/seed/csl_behring_assets.cypher\n"
            "  bin/seed/biogen_assets.cypher\n"
            "  src/foundation/load/*.py\n"
        ),
    ]

    return story
