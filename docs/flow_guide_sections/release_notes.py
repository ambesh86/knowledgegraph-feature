"""ReportLab section: Eugene release-notes route end-to-end flow.

Mirrors the structure and styling of build_drug_alias_guide() in
generate_flow_guides.py. Target: 5-7 PDF pages (meta route, shorter is OK).
"""
from __future__ import annotations

from . import _helpers as h


OUT_NAME = "EUGENE_RELEASE_NOTES_FLOW_GUIDE.pdf"
TITLE = "Eugene Release Notes - End-to-End Flow"


def build_story() -> list:
    story: list = []

    # ----------------------------- title --------------------------------- #
    story += [
        h.p("Eugene Release Notes &mdash; End-to-End Flow", h.H_TITLE),
        h.p(
            "Developer walkthrough: in-process Python dict &rarr; FastAPI router &rarr; "
            "JSON response &mdash; the simplest meta route in Eugene",
            h.H_SUB,
        ),
        h.rule(),
        h.Spacer(1, 12),
        h.p("Audience", h.H2),
        h.p(
            "Engineers who need to know how Eugene advertises its own changelog. "
            f"The {h.c('GET /releases')} endpoint is a single-file, zero-dependency "
            "route: no Neo4j, no adapter, no mapper, no validator. The response body "
            "is literally a Python dict declared inside the handler. This guide "
            "exists so the route is documented alongside the others &mdash; and so the "
            "process for updating release notes is unambiguous. Every reference "
            f"uses the form {h.c('path/to/file.py:line')}.",
        ),
        h.p("Reference endpoint", h.H2),
        *h.bullets([
            f"{h.c('GET /releases')} &mdash; no path parameters, no query parameters, "
            "no auth dependencies declared on the route itself.",
            f"Response: a JSON object keyed by version label (e.g. {h.c('&quot;v2.2 - 9/16/25&quot;')}) "
            "whose values are arrays of human-readable changelog strings.",
        ]),
        h.p("Caveat", h.H2),
        h.p(
            "Release notes are <b>hard-coded</b> in the router module &mdash; there is "
            "no file on disk, no database row, no CMS. Updating release notes means "
            f"editing {h.c('src/router/release_notes_router.py')} and shipping a new "
            "build of eugene_ws. Substitute &quot;Data source&quot; for &quot;Schema&quot; in "
            "the next section: there is no graph schema to read; the data source is "
            "the literal dict inside the handler.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 0. Data source -------------------------------- #
    story += [
        h.p("0. Data source (read this first)", h.H1),
        h.p(
            "Where the release notes content lives on disk:",
        ),
        h.code(
            "src/router/release_notes_router.py\n"
            "  line 13:  async def get_releases():\n"
            "  line 14:      releases = { ... }   # the entire payload\n"
            "  line 42:      return releases"
        ),
        *h.bullets([
            f"There is no separate {h.c('.md')}, {h.c('.json')}, or "
            f"{h.c('.yaml')} file. The handler constructs the dict on every call "
            "and returns it directly.",
            "Keys are free-form version-and-date strings &mdash; e.g. "
            f"{h.c('&quot;v1&quot;')}, {h.c('&quot;v1.1 - 8/1/25&quot;')}, "
            f"{h.c('&quot;v2.2 - 9/16/25&quot;')}. No semver enforcement, no ISO date.",
            f"Values are {h.c('list[str]')} &mdash; one bullet per line, sentence "
            "case, no markdown.",
            "Because the dict is rebuilt per request, there is no caching layer "
            "and no startup hook. Memory cost is trivial.",
            "Like the rest of Eugene there is no test fixture pinning the response "
            "shape &mdash; clients must be tolerant of new keys appearing.",
        ]),
        h.p("Verbatim payload (release_notes_router.py:14-41)", h.H2),
        h.code(
            "releases = {\n"
            "    \"v1\": [\"initial release of foundational graph endpoints\"],\n"
            "    \"v1.1 - 8/1/25\": [\n"
            "        \"updated foundational graph endpoints to include ids\",\n"
            "        \"added endpoints to power ui\",\n"
            "        \"added drug aliases endpoint\",\n"
            "        \"added company aliases endpoint\",\n"
            "    ],\n"
            "    \"v1.2 - 8/28/25\": [\n"
            "        \"added pagination and count endpoint\",\n"
            "        \"added more node type labels to endpoints\",\n"
            "        \"removed one hop endpoint in favor of n hop endpoint\",\n"
            "        \"changed company aliases to organization aliases\",\n"
            "    ],\n"
            "    \"v2.0 - 9/4/25\": [\n"
            "        \"loaded eugene 2.0 data. Including patents, clinical trails, and organizations\",\n"
            "        \"added search and count patents by drug id endpoints\",\n"
            "    ],\n"
            "    \"v2.1 - 9/11/25\": [\n"
            "        \"added endpoints for patent searches by clincal trial or gene protein target\",\n"
            "        \"updated drug synonym endpoint to return ids and to accept a drug id parameter\",\n"
            "    ],\n"
            "    \"v2.2 - 9/16/25\": [\n"
            "        \"added a database stats endpoint\",\n"
            "        \"added endpoints for pubmed searches by drug, clincal trial or gene protein target\",\n"
            "        \"updated release notes\",\n"
            "    ],\n"
            "}"
        ),
        h.PageBreak(),
    ]

    # --------------------- 1. HTTP entry --------------------------------- #
    story += [
        h.p("1. HTTP entry", h.H1),
        h.p(f"{h.c('src/router/release_notes_router.py')}", h.PATH),
        *h.bullets([
            f"Router declared at line 6: {h.c('APIRouter(prefix=&quot;&quot;, tags=[&quot;releases&quot;])')}. "
            "Empty prefix &mdash; the path is mounted at the application root.",
            f"Single route: {h.c('GET /releases')} (line 12). No path params, no "
            f"query params, no {h.c('response_model')}, no {h.c('Depends(...)')}.",
            f"The handler is declared {h.c('async def')} but performs no I/O &mdash; "
            "Python returns immediately with the literal dict.",
        ]),
        h.p("Verbatim handler (release_notes_router.py:6-42)", h.H2),
        h.code(
            "router = APIRouter(\n"
            "    prefix=\"\",\n"
            "    tags=[\"releases\"],\n"
            ")\n"
            "\n"
            "\n"
            "@router.get(\"/releases\")\n"
            "async def get_releases():\n"
            "    releases = {\n"
            "        \"v1\": [\"initial release of foundational graph endpoints\"],\n"
            "        # ...see section 0 for the full payload...\n"
            "    }\n"
            "    return releases"
        ),
        h.p("Registration", h.H2),
        h.p(
            f"{h.c('src/eugene_ws.py:33, 59')} &mdash; {h.c('add_routers()')} imports "
            f"the module as {h.c('release_notes_router')} and includes it via "
            f"{h.c('app.include_router(router.router)')} alongside "
            f"{h.c('root_router')} and {h.c('health_router')}.",
        ),
        h.code(
            "# src/eugene_ws.py:33\n"
            "from router import root_router, health_router, release_notes_router\n"
            "\n"
            "# src/eugene_ws.py:55-78\n"
            "routers = [\n"
            "    auth_router,\n"
            "    root_router,\n"
            "    health_router,\n"
            "    release_notes_router,\n"
            "    # ...other routers...\n"
            "]\n"
            "for router in routers:\n"
            "    app.include_router(router.router)"
        ),
        h.PageBreak(),
    ]

    # --------------------- 2. Handler internals -------------------------- #
    story += [
        h.p("2. Handler internals", h.H1),
        h.p(
            "There is essentially nothing to walk through: no file read, no format "
            "conversion, no transformation. The handler builds a dict literal and "
            "returns it. FastAPI / Starlette then runs the default "
            f"{h.c('JSONResponse')} encoder over the return value.",
        ),
        h.p("What FastAPI does to the dict on the way out", h.H2),
        *h.bullets([
            f"No {h.c('response_model')} was declared &mdash; so Pydantic does <b>not</b> "
            "validate or coerce the payload. The dict goes straight to the encoder.",
            f"{h.c('jsonable_encoder')} walks the dict: string keys are kept as-is, "
            f"string values inside the lists are kept as-is. No timestamps, no enums, "
            "no special types &mdash; the encoding is a no-op.",
            f"Content-Type: {h.c('application/json')}. Status: {h.c('200 OK')}.",
            "Because there is no I/O, the route is effectively rate-limited by the "
            f"SlowAPI middleware that {h.c('eugene_ws.py')} attaches to the whole app "
            "(see section 1) &mdash; not by any per-route limiter.",
        ]),
        h.p("Logging", h.H2),
        h.p(
            f"The module declares {h.c('logger = logging.getLogger(__name__)')} (line 4) "
            "but does not log anything inside the handler. Request-level logging "
            "comes from the JSON access-log middleware configured in "
            f"{h.c('eugene_ws.py')}.",
        ),
        h.PageBreak(),
    ]

    # --------------------- 3. Response model ----------------------------- #
    story += [
        h.p("3. Response model", h.H1),
        h.p(
            "There is no Pydantic model. The response shape is whatever the dict "
            "happens to be on the day you ship.",
        ),
        h.p("Example response (200)", h.H2),
        h.code(
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
            "\n"
            "{\n"
            "  \"v1\": [\"initial release of foundational graph endpoints\"],\n"
            "  \"v1.1 - 8/1/25\": [\n"
            "    \"updated foundational graph endpoints to include ids\",\n"
            "    \"added endpoints to power ui\",\n"
            "    \"added drug aliases endpoint\",\n"
            "    \"added company aliases endpoint\"\n"
            "  ],\n"
            "  \"v1.2 - 8/28/25\": [ ... ],\n"
            "  \"v2.0 - 9/4/25\": [ ... ],\n"
            "  \"v2.1 - 9/11/25\": [ ... ],\n"
            "  \"v2.2 - 9/16/25\": [\n"
            "    \"added a database stats endpoint\",\n"
            "    \"added endpoints for pubmed searches by drug, clincal trial or gene protein target\",\n"
            "    \"updated release notes\"\n"
            "  ]\n"
            "}"
        ),
        h.p("Informal schema", h.H2),
        *h.bullets([
            f"Top level: {h.c('dict[str, list[str]]')}.",
            f"Keys: free-form version labels. Current entries follow "
            f"{h.c('&quot;vMAJOR.MINOR - M/D/YY&quot;')} except for {h.c('&quot;v1&quot;')} "
            "which has no date.",
            "Values: ordered list of human-readable changelog strings; oldest first "
            "within each version.",
            "Errors: none expected &mdash; the route has no failure mode short of the "
            "process being down. There is no 404 or 422 path.",
        ]),
        h.p("Known typos in the payload (verbatim)", h.H2),
        *h.bullets([
            f"{h.c('clinical trails')} &rarr; should be {h.c('clinical trials')} "
            f"({h.c('&quot;v2.0 - 9/4/25&quot;')}).",
            f"{h.c('clincal trial')} &rarr; should be {h.c('clinical trial')} "
            f"({h.c('&quot;v2.1 - 9/11/25&quot;')} and {h.c('&quot;v2.2 - 9/16/25&quot;')}).",
            "Fixing them is a one-line change but is a behavior change for any "
            "client that pattern-matches the strings &mdash; leave them alone unless you "
            "are sure no downstream system is keying off the typos.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 4. Maintenance -------------------------------- #
    story += [
        h.p("4. Maintenance &mdash; how to update release notes", h.H1),
        h.p(
            "Because the payload is a Python literal, updating release notes is a "
            "code change. There is no admin UI and no runtime hot-reload.",
        ),
        h.p("Procedure", h.H2),
        *h.bullets([
            f"Open {h.c('src/router/release_notes_router.py')}.",
            f"Add a new top-level key to the {h.c('releases')} dict. Follow the "
            f"existing convention: {h.c('&quot;vMAJOR.MINOR - M/D/YY&quot;')}. Insert "
            "the new key <b>after</b> the previous one so insertion order (which "
            "Python preserves and FastAPI emits in JSON) reads oldest-to-newest.",
            f"Value is a {h.c('list[str]')}. One bullet per string. Lower-case "
            "sentence fragments to match the existing style (no terminal period).",
            f"Commit, run the unit tests if any cover this route, and ship a new "
            f"build of {h.c('eugene_ws')}. The route picks up the change on the "
            "next process start &mdash; there is no cache to bust.",
            "Optional: if you want a typed contract, declare a "
            f"{h.c('response_model=dict[str, list[str]]')} on the decorator. This "
            "is currently absent.",
        ]),
        h.p("Migration paths (if the dict outgrows the file)", h.H2),
        *h.bullets([
            f"Move the payload to {h.c('resources/release_notes.json')} and load "
            "it once at module import. Adds disk I/O at startup but keeps the "
            "handler trivial.",
            f"Move the payload to a markdown file under {h.c('docs/')} and parse "
            "it at request time. Adds a markdown dependency but lets non-engineers "
            "edit the changelog.",
            "Either change would warrant a real Pydantic response model and a "
            "smoke test pinning the shape.",
        ]),
        h.PageBreak(),
    ]

    # --------------------- 5. Debugging walk ----------------------------- #
    story += [
        h.p("5. Suggested debugging walk", h.H1),
        *h.bullets([
            f"Bring the stack up: {h.c('docker-compose up eugene_ws')}. Neo4j is "
            "not required &mdash; this route never touches the graph.",
            f"Smoke test: {h.c('curl -sS http://localhost:8000/releases | jq .')}. "
            "Expect a JSON object with six top-level keys ordered v1 through v2.2.",
            f"Confirm the registration: {h.c('curl -sS http://localhost:8000/openapi.json | jq &apos;.paths.&quot;/releases&quot;&apos;')}. "
            f"The {h.c('tags')} field should show {h.c('[&quot;releases&quot;]')}.",
            f"Breakpoint at {h.c('src/router/release_notes_router.py:14')}; inspect "
            f"the {h.c('releases')} dict. Any divergence between what you see in the "
            "debugger and what curl returns points at middleware (e.g. CORS, gzip), "
            "not at the handler.",
            f"If the route is missing in production, check {h.c('eugene_ws.py:33')} "
            f"and {h.c('eugene_ws.py:59')} &mdash; both lines must mention "
            f"{h.c('release_notes_router')} or the include loop will skip it.",
        ]),
        h.Spacer(1, 10),

        # ----------------- 6. Reference index ---------------------------- #
        h.p("6. Reference index", h.H1),
        h.code(
            "Data source (the dict itself)\n"
            "  src/router/release_notes_router.py        # lines 14-41, the releases dict\n\n"
            "HTTP entry\n"
            "  src/router/release_notes_router.py        # GET /releases (line 12)\n"
            "  src/eugene_ws.py                          # add_routers() L33, include L59\n\n"
            "Surrounding routers (same neighbourhood)\n"
            "  src/router/root_router.py                 # GET /\n"
            "  src/router/health_router.py               # GET /health\n\n"
            "OpenAPI / discoverability\n"
            "  GET /openapi.json   -> .paths.\"/releases\"\n"
            "  GET /docs           -> tag \"releases\"\n"
        ),
    ]

    return story
