import asyncio
import logging
import os
from typing import Any, AsyncGenerator

import httpx
from mcp.client.streamable_http import streamable_http_client
from strands import Agent
from strands.tools.mcp import MCPClient
from strands.agent.agent_result import AgentResult
from strands_tools import current_time, http_request, calculator, python_repl
from query.tools.external_tools import (
    search_pubmed,
    search_patents_web,
    search_clinical_trials,
    search_europepmc,
)
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.file_session_manager import FileSessionManager


from annotation.timer_annotation import log_time
from query.util.agent_debug import debugger_callback_handler
from query.util.connectivity import is_online
from query.util.temporal import build_temporal_directive, today_iso
from query.model.tool_request_enum import ToolRequestEnum
from query.model.agent_metrics import AgentMetrics

logger = logging.getLogger(__name__)


# Hard caps — see Stage 1 Assessment §04.2 (Hanging Runs root causes)
_AGENT_MAX_ITERATIONS = int(os.environ.get("EUGENE_AGENT_MAX_ITERATIONS", "20"))
_AGENT_STREAM_TIMEOUT_S = float(os.environ.get("EUGENE_AGENT_STREAM_TIMEOUT_S", "180"))
_MCP_VERIFY_SSL = os.environ.get("EUGENE_MCP_VERIFY_SSL", "true").lower() != "false"
_ALLOW_PYTHON_REPL = os.environ.get("EUGENE_ALLOW_PYTHON_REPL", "false").lower() == "true"
# `calculator`/`current_time` create ReAct-loop surface area for questions that
# have nothing to do with arithmetic or clock. They are opt-in per request.
_ALLOW_UTILITY_TOOLS = os.environ.get("EUGENE_ALLOW_UTILITY_TOOLS", "false").lower() == "true"
# Per-tool-call duplicate-input cap — if the agent issues the same
# (tool_name, input_json) more than this many times, we raise.
_MAX_DUPLICATE_TOOL_CALLS = 2
# Absolute hard cap on any single stream's tool calls.
_HARD_TOOL_CALL_BUDGET = int(os.environ.get("EUGENE_MAX_TOOL_CALLS", "25"))


def _source_key(include_tools: list[ToolRequestEnum]) -> str:
    """Stable key for the selected source set, used to SCOPE conversation memory.

    Each (conversation, source-set) gets its own session so that switching the
    datasource (Eugene KG / Web / PubMed) never lets a previous source's answer
    bleed into the new source's turn. Without this, a prior Eugene answer in the
    same conversation would be replayed when the user switches to Web/PubMed.
    """
    vals = sorted({t.value for t in include_tools}) or ["none"]
    return "+".join(vals)


def _all_sources_directive() -> str:
    """Tiered cascade policy for the All Sources mode.

    Unlike the single-source chips — which enforce STRICT SOURCE ISOLATION — All
    Sources deliberately spans every research source, but in a fixed order:
    the internal graph first, then live trial registrations, then literature.
    The escalation criteria are spelled out concretely (empty lookup, missing
    edge type, explicit recency ask) so "the graph didn't have it" is a testable
    condition rather than a judgement call the model makes silently.
    """
    return "\n".join(
        [
            "ACTIVE DATA SOURCES FOR THIS TURN — STRICT, READ FIRST.",
            "MODE = ALL SOURCES (CASCADING). You have every research source available this turn: "
            "the Eugene knowledge graph (MCP `lookup_*`/`fetch_*`/`find_*` tools), ClinicalTrials.gov "
            "(`search_clinical_trials`), and biomedical literature (`search_pubmed`, `search_europepmc`). "
            "You MUST consult them in strict tier order and escalate only on a real miss.",
            "",
            "TIER 1 — EUGENE INTERNAL KNOWLEDGE (always first, never skip). Your FIRST tool call of every "
            "turn MUST be `search_fused` on the user's question. This runs BOTH internal retrievers at once — "
            "the Neo4j graph (exact/lexical) and the Milvus vector store (semantic) — and returns ONE ranked, "
            "deduplicated evidence list. Results whose `retrievers` field lists both 'graph' and 'vector' were "
            "corroborated by independent lexical AND semantic retrieval: treat those as your strongest internal "
            "evidence and lead with them. This holds even when the question is obviously about live or recent "
            "data, because grounding first tells you the canonical entity names to search the external tiers "
            "with. Going straight to `search_clinical_trials` or `search_pubmed` without a Tier 1 "
            "`search_fused` call is a bug. "
            "Then deepen: take the `node_index`/`node_id` of the best hits and call `fetch_node_relationships` "
            "/ `fetch_facts` / `find_organization_*`. The graph contains `clinical_trial` nodes ingested from "
            "ClinicalTrials.gov, reachable from drugs via `evaluated_in` and from diseases via `featured_in` — "
            "check those edges before escalating a trial question. Escalate to Tier 2 ONLY when one of these "
            "is true, and say which one: (a) `search_fused` returned no relevant entity; "
            "(b) the entity resolved but the graph has no edges of the type asked for; (c) the user explicitly "
            "asked for *current*, *recent*, *recruiting*, *latest*, or *this year* information — the internal "
            "stores are a static snapshot and cannot answer that.",
            "",
            "TIER 2 — CLINICALTRIALS.GOV. Call `search_clinical_trials(query, max_results)` for live trial "
            "status, phases, sponsors, and enrollment. Cite the real NCT ids and URLs the tool returned. "
            "Escalate to Tier 3 when the question is about mechanism, efficacy, safety findings, or published "
            "evidence rather than trial registration facts — or when Tier 2 returned nothing.",
            "",
            "TIER 3 — PUBMED / EUROPE PMC. Call `search_pubmed(query, max_results)` and, for patent-adjacent "
            "or preprint coverage, `search_europepmc(query, max_results, patents_only)`. Cite the real PMIDs "
            "and URLs the tool returned.",
            "",
            "COLLATION — how to combine the tiers into one answer.",
            "Work the tiers ONE AT A TIME and keep each tier's findings separate as you go. Only after you "
            "have finished retrieving do you write the answer, and you write it as a SINGLE collated response, "
            "not as three stacked mini-answers. Concretely: "
            "(i) group the evidence by FINDING (the drug, the trial, the claim), not by which tool produced it; "
            "(ii) where two tiers describe the same entity — e.g. a trial present both in the graph and in the "
            "live ClinicalTrials.gov result — MERGE them into one item and note that both agree, rather than "
            "listing it twice; "
            "(iii) rank the collated findings by how well corroborated they are: internal `search_fused` hits "
            "marked by both retrievers plus an external confirmation are the strongest, a single-retriever hit "
            "with no external support is the weakest; "
            "(iv) if a tier contributed nothing useful, say so in one short clause rather than padding the "
            "answer with its empty result.",
            "",
            "SYNTHESIS RULES.",
            "1. Do NOT stop at Tier 1 merely because it produced *something* — if the internal answer is "
            "materially incomplete for what was asked, continue to the next tier and combine the results.",
            "2. Attribute every fact inline to the tier that produced it. Never present a live ClinicalTrials.gov "
            "or PubMed fact as a graph fact, or vice versa.",
            "3. When tiers disagree (e.g. the graph shows a trial completed and ClinicalTrials.gov shows it "
            "recruiting), surface the disagreement explicitly and prefer the LIVE source for status, noting "
            "that the graph snapshot is static.",
            "4. Never fabricate a source, identifier, or URL. Only ever cite what a tool actually returned.",
            "5. Respect the tool-call budget: at most ~20 calls per turn. Prefer 2-4 precise calls per tier "
            "over exhaustive sweeps. Never repeat a tool with identical arguments.",
            "",
            "End every answer with a 'Sources:' footer naming every tier you ACTUALLY queried, e.g. "
            "'Sources: Eugene knowledge graph — Emicizumab, Hemophilia A · ClinicalTrials.gov NCT04158648 "
            "(https://clinicaltrials.gov/study/NCT04158648) · PubMed PMID 38421789 "
            "(https://pubmed.ncbi.nlm.nih.gov/38421789/)'. Naming a tier you did not query is a bug.",
        ]
    )


def build_source_directive(include_tools: list[ToolRequestEnum]) -> str:
    """Per-request data-source policy, prepended to the system prompt.

    The datasource chips (Eugene KG / Web / PubMed) are authoritative and map
    to distinct tool families in `_init_agent`. This directive tells the model
    how to BEHAVE for the exact combination the user selected: stay inside the
    graph for Eugene-only (and ask for consent before suggesting the internet),
    use the live tools when Web/PubMed are enabled, and always cite the source.
    """
    # All Sources is a CASCADE, not a union of the other chips — it has its own
    # tiered policy and must be checked before the isolation rules below.
    if ToolRequestEnum.ALL_SOURCES in include_tools:
        return _all_sources_directive()

    has_eugene = ToolRequestEnum.EUGENE in include_tools
    has_web = ToolRequestEnum.HTTP in include_tools
    has_pubmed = ToolRequestEnum.PUBMED in include_tools
    # Empty selection behaves like Eugene-only (the bounded, safe default).
    if not (has_eugene or has_web or has_pubmed):
        has_eugene = True

    enabled = []
    if has_eugene:
        enabled.append("Eugene knowledge graph")
    if has_web:
        enabled.append("Web (live internet)")
    if has_pubmed:
        enabled.append("PubMed / Europe PMC")
    lines = [
        "ACTIVE DATA SOURCES FOR THIS TURN — STRICT, READ FIRST.",
        f"The user has enabled ONLY these source(s): {', '.join(enabled)}. "
        "These selections are authoritative. You must answer using ONLY the enabled source(s) "
        "and must clearly tell the user which source each answer came from.",
    ]

    eugene_only = has_eugene and not has_web and not has_pubmed
    if eugene_only:
        lines += [
            "MODE = EUGENE-ONLY. Answer EXCLUSIVELY from the Eugene knowledge graph via the MCP "
            "graph tools (lookup_*/fetch_*/find_*). You have NO web or PubMed tools this turn, and you "
            "MUST NOT use your own training knowledge, guess, or produce ANY external/internet/Google "
            "link. If — after a real `lookup_node_by_value` (fuzzy_match=true) that returns nothing — the "
            "information is genuinely not in the graph, do NOT answer from outside and do NOT paste a "
            "search link. Instead: (1) state plainly that it is not in the Eugene knowledge graph, and "
            "(2) ASK the user for consent to look elsewhere, in these words or similar: \"This isn't in the "
            "Eugene knowledge graph. If you'd like me to search the public web or PubMed, enable the Web "
            "or PubMed source button and re-send your question, and I'll search there.\" Only proceed to an "
            "external source if the user re-sends with that source enabled.",
        ]
    else:
        if has_eugene:
            lines.append(
                "The Eugene knowledge graph is enabled: prefer it for any entity it contains "
                "(drugs, diseases, genes/proteins, trials, patents, organizations already ingested)."
            )
        else:
            lines.append(
                "The Eugene knowledge graph is NOT enabled this turn: do not present graph facts as the "
                "source; answer only from the enabled external source(s) and say so."
            )
        if has_web:
            lines.append(
                "WEB enabled: you MAY use `search_patents_web`, `search_clinical_trials`, and `http_request` "
                "for live internet data (Google Patents, ClinicalTrials.gov, arbitrary URLs). State the data "
                "is live from the named source and cite the REAL URLs the tool returned."
            )
        if has_pubmed:
            lines.append(
                "PUBMED enabled: you MAY use `search_pubmed` and `search_europepmc` for biomedical "
                "literature (and patents via Europe PMC). Cite the REAL PMIDs / URLs the tool returned."
            )
        lines.append(
            "The user explicitly enabled the external source(s) above, so you do NOT need to ask for "
            "consent before using them. Attribute every fact to the source it came from."
        )

    lines.append(
        "STRICT SOURCE ISOLATION: use ONLY the tools belonging to the enabled source(s) above. Do NOT answer "
        "from your own training knowledge, and do NOT reuse an answer from an earlier turn that used a "
        "different source. If the enabled tools cannot answer the question, do NOT return an empty reply — "
        "say clearly that the question can't be answered from the enabled source(s) and suggest which source "
        "would help (e.g. 'This is a knowledge-graph lookup — enable Eugene KG'). "
        "ALWAYS finish with a 'Sources:' line (see SOURCE ATTRIBUTION below). Never claim or link a source "
        "you did not actually query."
    )
    return "\n".join(lines)


class EugeneDataAgent:
    system_prompt = """You are Eugene, an agent that answers biomedical competitive-intelligence questions by querying the CSL Behring Eugene knowledge graph.
Scope: drugs, diseases, gene/proteins, pathways, patents, clinical trials, organizations, and the relationships between them.

Follow the ReAct pattern (Reason → Act → Observe). Prefer MCP tools (fetch_*, find_*, lookup_*) for facts. When the graph does not contain the requested information, state that clearly and stop — do not loop.

TOOL GUIDE:
- CITATION LABELS — YOU MAY NOT WRITE LINKS TO INTERNAL EVIDENCE. Every `search_fused` result carries a backend-issued `evidence_label` such as "Evidence 3". When you use a passage, cite it by that exact label in square brackets — e.g. "…reduced proteinuria at 24 weeks [Evidence 3]." NEVER construct a URL, a document id, or a chunk id yourself for an internal passage: the interface resolves the label to the highlighted source region. A citation you invent is a fabricated citation even when the underlying fact is right. (Real URLs returned by the LIVE external tools — PubMed, ClinicalTrials.gov, Europe PMC — are still quoted normally; this rule governs internal evidence.)
- PAPER PASSAGES: `search_fused` may return `paper_chunk` results — actual passages extracted from research PDFs Eugene has ingested, each with `doc_id`, `chunk_id`, `page` and `paper_title`. These are the strongest evidence available: the exact region of the source PDF can be shown to the user. When one answers the question, quote or closely paraphrase it and name the paper and page number. Do NOT paraphrase a passage into a vaguer claim — the specificity is what makes it verifiable.
- BEST STARTING POINT for any entity question: `search_fused(query)`. It runs Neo4j full-text and the Milvus vector store concurrently and returns one reciprocal-rank-fused evidence list. Results tagged with BOTH 'graph' and 'vector' in their `retrievers` field were corroborated by independent lexical and semantic retrieval — trust those most. Use the returned `node_index` / `node_id` to drill in with `fetch_node_relationships` / `fetch_facts`. Prefer this over a bare `lookup_node_by_value` when the user's phrasing may not match the canonical entity name.
- Graph lookup (drugs, genes, diseases, organizations, patents already ingested): use the MCP `fetch_*` / `lookup_*` / `find_organization_*` tools.
- ORGANIZATION ASSETS — ALWAYS two steps, never guess an id:
  1. Call `find_organization_names(name_pattern)` with the organization name the user gave (e.g. "CSL", "Roche"). This returns matching organizations each with their real `node_id`.
  2. Take the `node_id` from step 1's result and pass it to `find_organization_assets(organization_id)`.
  NEVER pass a guessed or placeholder id (such as "C010405") to `find_organization_assets`. The id MUST come from a prior `find_organization_names` result. If `find_organization_names` returns nothing, tell the user the organization is not in the graph and stop — do not call `find_organization_assets`.
- FACTS vs RELATIONSHIPS — pick the right tool:
  * `fetch_facts(node_id)` returns indications / contraindications / off-label uses (for drugs) or associated genes/proteins/drugs (for diseases). It does NOT return clinical trials, neighbors, or organizations.
  * `fetch_node_relationships(node_id)` returns the node's graph edges (e.g. clinical trials via `evaluated_in`/`featured_in`, neighbors, sponsors). USE THIS for "which clinical trials reference X", "what is connected to X", "neighbors of X".
  * Clinical trials in this graph link to DRUGS and DISEASES, not to gene/protein nodes. If asked for trials referencing a gene/protein, report that gene/protein nodes have no direct trial links rather than retrying.
- Latest patents on the open web: call `search_patents_web(query)` — it returns a Google Patents deep-link the user can follow. Do NOT try to scrape Google Patents with `http_request`, it will return 503.
- Biomedical literature (PubMed papers, including patent-adjacent publications): call `search_pubmed(query, max_results)`. It uses NCBI E-utilities and returns structured {pmid, title, journal, year, authors, url} records.
- LIVE clinical trials (recruiting status, recent/ongoing trials, sponsors, phases) — use `search_clinical_trials(query, max_results)`. It queries ClinicalTrials.gov in real time and returns {nct_id, title, status, phase, sponsor, conditions, url}. Prefer this over the static graph when the user asks about *current* or *recent* trials.
- LIVE literature AND patents — use `search_europepmc(query, max_results, patents_only)`. Real-time Europe PMC search; set patents_only=True to restrict to patent documents. Returns {id, source, title, authors, year, url}. This is the best available real-time PATENT data source (returns actual records, unlike search_patents_web which only returns a link).
- When the user asks for "latest", "recent", "current", "this year", "real-time", or "search the internet/web", PREFER the live tools above (search_clinical_trials, search_europepmc, search_pubmed) over the static Eugene graph, and clearly state the data is live from the named source.
- Arbitrary URL fetch: `http_request` — only for non-biomedical pages. Many biomedical sites rate-limit bots.

HARD RULES:
1. Do NOT call `calculator` or `current_time` unless the user's question is explicitly about arithmetic or the current date/time. They are forbidden for data lookups.
2. NEVER call the same tool with the same arguments more than once. A tool that returns successfully has given you its complete answer — even if that answer is empty or lacks what you hoped for. Do NOT retry it hoping for a different result. If the result does not contain what you need, either try a DIFFERENT tool or conclude with what you have. Repeating a call with identical inputs is always a bug.
3. Do NOT invent data. BEFORE telling the user that something is "not in the Eugene knowledge graph" you MUST have actually called `lookup_node_by_value` (try fuzzy_match=true) and received an empty / "Unable to fetch" result. If `lookup_node_by_value` returns ANY node for the entity — even an alias/synonym variant — then the entity DOES exist in the graph: continue with `fetch_node_relationships` / `fetch_facts` on the resolved id. When the entity genuinely does not resolve, follow the ACTIVE DATA SOURCES policy that appears at the very top of this prompt — it decides whether you may use an external source or must ask the user for consent first. NEVER paste a raw `google.com/search?q=...` (or any made-up) link; only ever cite a real URL that an external tool actually returned to you.
3a. NODE RESOLUTION — avoid alias dead-ends: `lookup_node_by_value` may return an alias/synonym node whose id contains `_synonym_` or `_alias_` (e.g. `drug_db14473_synonym_0`). Alias nodes have NO biological edges, so running `fetch_node_relationships` / `has_reachable_path` / `fetch_facts` against them returns empty and makes it look like "no connection" when there really is one. When you get such an id, call `fetch_node_details` on it to obtain the canonical entity node, and use that canonical id for all relationship / path / fact queries. A synonym/alias match is PROOF the entity exists — never report it as absent or claim "no connection" based on an alias-node query.
3b. NEVER fabricate placeholder list items. Do not emit rows like "Patent 1: [node_id=null]". If a relationship result has no usable name/title/id, either render its real identifier or omit it entirely — empty or unnamed results must not be padded with numbered placeholders.
4. Keep total tool calls to <= 20 per user turn. Prefer fewer, more precise tool calls.
5. OUTPUT FORMAT: reply to the user in clear, plain prose. Do NOT wrap your answer in <thinking>, <response>, or any other XML/markup tags, and do not narrate your step-by-step internal reasoning — give the user the final answer directly.
6. CLINICAL TRIALS: the graph contains ClinicalTrial nodes. For trials about a drug or disease, resolve the entity (lookup_node_by_value) then fetch_node_relationships to find its `evaluated_in`/`featured_in` ClinicalTrial edges. Only use the live `search_clinical_trials` tool when it is available AND the user explicitly asked for the latest/recruiting status; if that tool errors, fall back to the graph rather than giving up.
7. QUERY SIZE — KEEP RESULTS SMALL (critical, or the model input overflows):
   - Default to n_hop=1. Only use n_hop=2 when the user explicitly needs 2 hops AND the start entity has few neighbors; if a 1-hop result is already large, do NOT expand to 2 hops.
   - Use small page sizes (page_size <= 25) and read the first page; do not page through entire result sets.
   - NEVER fetch an entire label (e.g. all `drug` nodes via fetch_by_label) or a full multi-hop neighborhood — these return thousands of nodes and exceed the model's input limit.
   - For "how many X" / counting questions: there is no count tool, and bulk-fetching to count will overflow. Tell the user exact counts require a database aggregation that isn't exposed as a tool, and instead answer about specific named entities.

Reasoning trace: the UI renders your reasoning-path graph automatically from the tool calls you make — you do NOT need to (and must NOT) write node ids or tool names into your prose. Do NOT append annotations like "[node_id=DB13923, tool=fetch_facts]", "[node_id=null, ...]", or "(node_id: 2159)" to your answer. Reply in clean, human-readable prose with entity NAMES (e.g. "F9", "Factor VIII", "Hemophilia A"), never internal ids or tool names.

SOURCE ATTRIBUTION (always, every answer): the user must always be able to tell where the answer came from. End every answer with a "Sources:" line:
- For graph facts: write "Sources: Eugene knowledge graph" and name the entities you used (e.g. "Eugene knowledge graph — Emicizumab, F9, F10"). The graph has no public URL, so do NOT invent one.
- For external facts: list the REAL URLs / identifiers the external tool returned — e.g. "Sources: PubMed PMID 12345678 (https://pubmed.ncbi.nlm.nih.gov/12345678/)" or "Sources: ClinicalTrials.gov NCT01234567 (https://clinicaltrials.gov/study/NCT01234567)" or the Google Patents / Europe PMC URL the tool gave you.
- If an answer mixes sources, attribute each fact to its source inline and list all sources at the end.
Never claim a source you did not actually query, and never fabricate a link.
""".strip()

    def __init__(self, eugene_mcp_server_url: str, model):
        self.eugene_mcp_server_url = eugene_mcp_server_url
        self.model = model

    # Cache for the internal snapshot date — it changes only on re-ingest, so
    # re-fetching per turn would add latency for a value that is stable for days.
    _snapshot_cache: dict[str, Any] = {"date": None, "checked_at": 0.0}
    _SNAPSHOT_TTL_S = 900.0

    def _snapshot_date(self) -> str | None:
        """ISO date the internal graph/vector stores were last refreshed.

        Read from the core API so the agent can date internal facts honestly
        instead of implying they are current. Failure is non-fatal: we simply omit
        the snapshot line rather than blocking the turn.
        """
        import time

        now = time.time()
        cached = EugeneDataAgent._snapshot_cache
        if cached["date"] and (now - float(cached["checked_at"])) < self._SNAPSHOT_TTL_S:
            return str(cached["date"])
        base = os.environ.get("EUGENE_CORE_API_URL", "http://eugene_ws:8000")
        try:
            resp = httpx.get(f"{base}/health/data-freshness", timeout=5.0)
            resp.raise_for_status()
            date = (resp.json() or {}).get("snapshot_date")
        except Exception as e:
            logger.warning(f"could not read data freshness: {e}")
            date = None
        cached["date"] = date
        cached["checked_at"] = now
        return date

    def _new_conversation_manager(self) -> SlidingWindowConversationManager:
        # AGT-01 fix: instantiate per-conversation, not shared across concurrent sessions
        return SlidingWindowConversationManager(
            window_size=10, should_truncate_results=True, per_turn=2
        )

    @log_time
    def execute(
        self,
        token: str,
        user_prompt: str,
        conversation_id: str,
        include_tools: list[ToolRequestEnum] = [],
    ) -> AgentResult:
        mcp_client = self._build_mcp_client(token=token)
        agent = self._init_agent(
            mcp_client=mcp_client,
            conversation_id=conversation_id,
            include_tools=include_tools,
        )
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"conversation: {conversation_id}")
            logger.info(f"model: {self.model}")
            logger.info(f"user prompt: {user_prompt}")
            logger.info(f"tools: {agent.tool_names}")

        with mcp_client:
            response = agent(user_prompt)

        if logger.isEnabledFor(logging.INFO):
            metrics = AgentMetrics.of(response)
            logger.info(f"{conversation_id} response metrics: {metrics}")
        return response

    @log_time
    async def execute_stream(
        self,
        token: str,
        user_prompt: str,
        conversation_id: str,
        include_tools: list[ToolRequestEnum] = [],
    ) -> AsyncGenerator[dict[str, str], None]:
        # Nova models occasionally emit an invalid tool-use sequence
        # ("modelStreamErrorException: invalid sequence as part of ToolUse").
        # It is non-deterministic, so retry with a fresh agent on transient model
        # errors. A fresh session id per retry avoids replaying the failed turn's
        # partial tool-use state back into the model.
        max_attempts = int(os.environ.get("EUGENE_AGENT_MODEL_RETRIES", "3"))
        yield {"type": "session", "session_id": conversation_id, "content": ""}
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            session_id = (
                conversation_id if attempt == 0 else f"{conversation_id}-r{attempt}"
            )
            mcp_client = self._build_mcp_client(token=token)
            agent = self._init_agent(
                mcp_client=mcp_client,
                conversation_id=session_id,
                include_tools=include_tools,
            )

            # AGT-03 fix: wrap entire stream in a timeout so a stalled MCP/LLM can't hang the connection
            async def _run() -> AsyncGenerator[dict, None]:
                seen_tool_ids: set[str] = set()
                tool_call_budget = {"remaining": _HARD_TOOL_CALL_BUDGET}
                dup_fingerprints: dict[str, int] = {}

                def _register_tool_call(ev: dict) -> str | None:
                    """Return a breaker message if the loop should be killed."""
                    if ev.get("type") != "tool_call":
                        return None
                    tool_call_budget["remaining"] -= 1
                    if tool_call_budget["remaining"] < 0:
                        return (
                            f"Tool-call budget exhausted ({_HARD_TOOL_CALL_BUDGET}). "
                            "Stopping to prevent runaway ReAct loop."
                        )
                    # Duplicate-input detection requires the actual tool input.
                    # Streamed tool_call events frequently arrive with an EMPTY
                    # input (the args are filled in later / harvested post-stream),
                    # so fingerprinting on empty input makes N legitimately
                    # different calls to the SAME tool (e.g. fetch_node_relationships
                    # on several different neighbors) look identical and falsely
                    # trips the breaker. Only fingerprint when input is populated;
                    # the hard tool-call budget above still bounds runaway loops.
                    ti = ev.get("tool_input")
                    if not ti:
                        return None
                    import json as _json
                    try:
                        fp = f"{ev.get('tool')}::{_json.dumps(ti, sort_keys=True, default=str)}"
                    except Exception:
                        fp = f"{ev.get('tool')}::<unhashable>"
                    dup_fingerprints[fp] = dup_fingerprints.get(fp, 0) + 1
                    if dup_fingerprints[fp] > _MAX_DUPLICATE_TOOL_CALLS:
                        return (
                            f"Agent repeated `{ev.get('tool')}` with identical inputs "
                            f"{dup_fingerprints[fp]} times — breaking loop."
                        )
                    return None

                with mcp_client:
                    kill_reason: str | None = None
                    async for event in agent.stream_async(user_prompt):
                        # Text deltas
                        if isinstance(event, dict) and "data" in event:
                            yield {
                                "type": "content",
                                "content": event["data"],
                                "session_id": conversation_id,
                            }
                        # Opportunistic mid-stream extraction (best-effort, shape may vary)
                        for ev in _extract_tool_events(event, conversation_id, seen_tool_ids):
                            yield ev
                            kill_reason = _register_tool_call(ev)
                            if kill_reason:
                                break
                        if kill_reason:
                            break

                    if kill_reason:
                        logger.warning(f"{conversation_id}: {kill_reason}")
                        yield {
                            "type": "content",
                            "content": f"\n\n⚠️ {kill_reason}",
                            "session_id": conversation_id,
                        }

                    # Post-stream: authoritative tool-call extraction from the
                    # agent's full message history. This is the reliable path
                    # because Strands' in-flight event shapes differ across
                    # versions/providers, but `agent.messages` is stable.
                    for ev in _harvest_messages(agent, conversation_id, seen_tool_ids):
                        yield ev

            async def _collect():
                async for item in _run():
                    yield item

            produced = False
            try:
                async for item in self._with_timeout(
                    _collect(), _AGENT_STREAM_TIMEOUT_S
                ):
                    if (
                        isinstance(item, dict)
                        and item.get("type") == "content"
                        and item.get("content")
                    ):
                        produced = True
                    yield item
                yield {"type": "done", "content": "", "session_id": conversation_id}
                logger.info(f"conversation {conversation_id}: completed streaming")
                return
            except asyncio.TimeoutError:
                logger.warning(
                    f"conversation {conversation_id} exceeded {_AGENT_STREAM_TIMEOUT_S}s timeout"
                )
                yield {
                    "type": "error",
                    "content": f"Agent execution exceeded {int(_AGENT_STREAM_TIMEOUT_S)}s timeout",
                    "session_id": conversation_id,
                }
                yield {"type": "done", "content": "", "session_id": conversation_id}
                return
            except Exception as e:
                last_error = e
                em = str(e)
                transient = any(
                    k in em
                    for k in (
                        "ToolUse",
                        "ConverseStream",
                        "ValidationException",
                        "ModelStreamError",
                        "modelStreamError",
                        "Throttl",
                        "throttl",
                    )
                )
                if produced or not transient or attempt == max_attempts - 1:
                    break
                logger.warning(
                    f"conversation {conversation_id}: transient model error on "
                    f"attempt {attempt + 1}/{max_attempts} "
                    f"({type(e).__name__}); retrying with a fresh agent"
                )
                continue

        # All retries exhausted, or a non-retryable / mid-answer error.
        logger.exception(
            f"Error while streaming conversation {conversation_id}: {last_error}"
        )
        yield {
            "type": "error",
            "content": f"Error: {str(last_error)}",
            "session_id": conversation_id,
        }
        yield {"type": "done", "content": "", "session_id": conversation_id}

    @staticmethod
    async def _with_timeout(agen: AsyncGenerator, timeout_s: float):
        """Yield from `agen` but bound total wall time to `timeout_s`."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                item = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                return
            yield item

    def _init_agent(
        self,
        mcp_client: MCPClient,
        conversation_id: str,
        include_tools: list[ToolRequestEnum] = [],
    ) -> Agent:
        logger.info(f"include_tools={include_tools}")
        name = "EugeneDataAgent"

        # Must enter the MCP client context to list tools; the caller re-enters it
        # for the actual agent run, which is safe because MCPClient is re-entrant
        # via its internal session management.
        with mcp_client:
            # Scope memory by source so Eugene / Web / PubMed never share history
            # within the same conversation (prevents cross-source answer bleed).
            scoped_session_id = f"{conversation_id}__{_source_key(include_tools)}"
            session_manager = FileSessionManager(session_id=scoped_session_id)
            logger.info(
                f"writing session to {session_manager.storage_dir} (scope={scoped_session_id})"
            )

            # Utility tools are opt-in — they caused runaway ReAct loops
            # (agent spamming `current_time` trying to "search the web").
            # See Stage 1 Assessment §04.2 (Hanging Runs). AGT-05 for python_repl.
            local_tools: list = []
            if _ALLOW_UTILITY_TOOLS:
                local_tools.extend([calculator, current_time])
            if _ALLOW_PYTHON_REPL:
                local_tools.append(python_repl)
            # Datasource buttons map to distinct external tool families. These
            # require internet egress; in a sealed VPC they fail, so they are
            # only added when the user explicitly selects that datasource.
            all_sources = ToolRequestEnum.ALL_SOURCES in include_tools
            if all_sources:
                # Cascade mode gets the full research toolset. `http_request` is
                # deliberately excluded: arbitrary URL fetching is not a research
                # source and only adds ReAct-loop surface area (see the Stage 1
                # hanging-runs analysis) — the three tiers cover the real sources.
                local_tools.extend(
                    [search_clinical_trials, search_pubmed, search_europepmc]
                )
            if ToolRequestEnum.PUBMED in include_tools:
                local_tools.extend([search_pubmed, search_europepmc])
            if ToolRequestEnum.HTTP in include_tools:
                local_tools.extend([search_patents_web, search_clinical_trials, http_request])

            mcp_tools = []
            # All Sources needs the graph tools for Tier 1.
            if ToolRequestEnum.EUGENE in include_tools or all_sources:
                mcp_tools.extend(mcp_client.list_tools_sync())
            # Dedupe by identity — a request combining `all_sources` with the
            # `pubmed`/`http` chips (possible via the API even though the UI is
            # single-select) would otherwise register the same tool twice.
            seen_tools: set[int] = set()
            local_tools = [
                t for t in local_tools
                if not (id(t) in seen_tools or seen_tools.add(id(t)))
            ]
            tools = [*mcp_tools, *local_tools]

        # The clock goes FIRST — ahead of even the source policy. Without it the
        # model answers "as of now" with its training cutoff (observed: a 2026
        # deployment reporting "as of now means June 2024").
        online = is_online()
        temporal_directive = build_temporal_directive(
            online=online, snapshot_date=self._snapshot_date()
        )
        source_directive = build_source_directive(include_tools)
        system_prompt = (
            f"{temporal_directive}\n\n{source_directive}\n\n{self.system_prompt}"
        )
        logger.info(f"temporal: today={today_iso()} online={online}")
        logger.info(f"source_directive: {source_directive.splitlines()[1] if source_directive else ''}")

        agent = Agent(
            name=name,
            tools=tools,
            model=self.model,
            system_prompt=system_prompt,
            callback_handler=debugger_callback_handler,
            # AGT-01 fix: per-conversation manager
            conversation_manager=self._new_conversation_manager(),
            session_manager=session_manager,
        )
        # AGT-02 fix: cap ReAct iterations. Strands 1.21 does not expose a
        # constructor kwarg for this; set it post-construction defensively so
        # newer releases pick it up and older releases simply ignore it.
        for attr in ("max_iterations", "max_parallel_tools"):
            try:
                setattr(agent, attr, _AGENT_MAX_ITERATIONS if attr == "max_iterations" else 1)
            except Exception:
                pass
        logger.info(f"initialized {name}, tools={agent.tool_names}")
        return agent

    def _build_mcp_client(self, token: str) -> MCPClient:
        # SEC-01 fix: default verify=True; dev can opt out via EUGENE_MCP_VERIFY_SSL=false
        verify = _MCP_VERIFY_SSL
        return MCPClient(
            lambda: streamable_http_client(
                url=self.eugene_mcp_server_url,
                http_client=httpx.AsyncClient(
                    verify=verify,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0),
                ),
            )
        )


# ----------------------------------------------------------------------------
# Tool-call event extraction helpers
# ----------------------------------------------------------------------------

def _extract_tool_events(event, conversation_id: str, seen: set):
    """Yield tool_call / tool_result events if the mid-stream `event` contains them.

    Strands event shapes vary across providers (OpenAI vs Anthropic) and minor
    versions, so this is defensive: we inspect several known keys and skip on
    anything unexpected.
    """
    if not isinstance(event, dict):
        return

    # Path 1: `current_tool_use` (Anthropic-shaped streaming)
    cur = event.get("current_tool_use")
    if isinstance(cur, dict):
        tid = cur.get("toolUseId") or cur.get("id") or ""
        if tid and tid not in seen:
            seen.add(tid)
            yield {
                "type": "tool_call",
                "content": "",
                "session_id": conversation_id,
                "tool": cur.get("name", ""),
                "tool_input": cur.get("input", {}),
                "tool_id": tid,
            }

    # Path 2: completed `message` events containing toolUse / toolResult blocks
    msg = event.get("message")
    if isinstance(msg, dict):
        for block in (msg.get("content") or []):
            if not isinstance(block, dict):
                continue
            if "toolUse" in block:
                t = block["toolUse"] or {}
                tid = t.get("toolUseId") or t.get("id") or ""
                if tid and tid not in seen:
                    seen.add(tid)
                    yield {
                        "type": "tool_call",
                        "content": "",
                        "session_id": conversation_id,
                        "tool": t.get("name", ""),
                        "tool_input": t.get("input", {}),
                        "tool_id": tid,
                    }
            if "toolResult" in block:
                r = block["toolResult"] or {}
                tid = r.get("toolUseId") or ""
                yield {
                    "type": "tool_result",
                    "content": "",
                    "session_id": conversation_id,
                    "tool_id": tid,
                    "tool_output": _flatten_tool_output(r.get("content", [])),
                }


def _harvest_messages(agent, conversation_id: str, seen: set):
    """After stream completes, walk `agent.messages` and emit any tool calls we missed.

    This is the authoritative path: `agent.messages` is Strands' conversation
    history and always contains the full toolUse/toolResult trail.
    """
    messages = getattr(agent, "messages", None) or []
    pending_calls: dict[str, dict] = {}
    for m in messages:
        if not isinstance(m, dict):
            continue
        for block in m.get("content") or []:
            if not isinstance(block, dict):
                continue
            if "toolUse" in block:
                t = block["toolUse"] or {}
                tid = t.get("toolUseId") or t.get("id") or ""
                if not tid:
                    continue
                pending_calls[tid] = {
                    "type": "tool_call",
                    "content": "",
                    "session_id": conversation_id,
                    "tool": t.get("name", ""),
                    "tool_input": t.get("input", {}),
                    "tool_id": tid,
                }
            if "toolResult" in block:
                r = block["toolResult"] or {}
                tid = r.get("toolUseId") or ""
                # Emit the paired tool_call first if we haven't already
                if tid and tid not in seen and tid in pending_calls:
                    seen.add(tid)
                    yield pending_calls[tid]
                yield {
                    "type": "tool_result",
                    "content": "",
                    "session_id": conversation_id,
                    "tool_id": tid,
                    "tool_output": _flatten_tool_output(r.get("content", [])),
                }
    # Any tool_call we discovered that never had a result (rare) — still emit
    for tid, call in pending_calls.items():
        if tid not in seen:
            seen.add(tid)
            yield call


def _flatten_tool_output(content):
    """Tool result `content` is a list of blocks like [{"text": "..."}, {"json": {...}}].
    Parse JSON strings so the UI can walk them for nodes/rels.
    """
    if not isinstance(content, list):
        return content
    out = []
    for block in content:
        if not isinstance(block, dict):
            out.append(block)
            continue
        if "json" in block:
            out.append(block["json"])
        elif "text" in block:
            text = block["text"]
            # Try to parse as JSON; native Strands tools often serialize their
            # dict return as a Python repr (single quotes) which is NOT valid
            # JSON, so fall back to ast.literal_eval before giving up. Without
            # this the UI graph normalizer can't walk the result for nodes.
            parsed = None
            try:
                import json
                parsed = json.loads(text)
            except Exception:
                try:
                    import ast
                    parsed = ast.literal_eval(text)
                except Exception:
                    parsed = text
            out.append(parsed)
        else:
            out.append(block)
    return out

