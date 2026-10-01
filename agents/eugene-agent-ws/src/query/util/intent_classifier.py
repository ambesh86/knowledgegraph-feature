"""Lightweight keyword-based intent classifier.

Goal: reduce agent surface area. Given the user's prompt, decide which tool
families are actually relevant. The agent is then initialised with only
those tools, which both:

  1. Makes runaway ReAct loops far less likely (the agent can't call
     `current_time` if the tool isn't in its toolset).
  2. Makes answers faster and cheaper (fewer tools = shorter system prompt
     tokens sent on each LLM turn).

This is intentionally simple. A future iteration can swap in a small
classifier model, but for Eugene's well-defined domain keyword rules give
>90% precision with zero extra latency or cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from query.model.tool_request_enum import ToolRequestEnum


@dataclass
class IntentResult:
    tools: list[ToolRequestEnum]
    reason: str


_WEB_RE = re.compile(
    r"\b(web|internet|online|google|latest|recent|news|published|link|url)\b",
    re.IGNORECASE,
)
_PUBMED_RE = re.compile(
    r"\b(pubmed|publication|paper|article|literature|journal|citation|abstract)\b",
    re.IGNORECASE,
)
_PATENT_RE = re.compile(
    r"\b(patent|uspto|ip\b|intellectual property|assignee|patent\s*number)\b",
    re.IGNORECASE,
)
_GRAPH_RE = re.compile(
    r"\b(drug|disease|gene|protein|pathway|trial|indication|contraindication|organization|target|neighbors?|relationship|node_id|biogen|roche|csl|hemophilia|factor|emicizumab|afstyla|eloctate|hemlibra)\b",
    re.IGNORECASE,
)


def classify_intent(
    prompt: str,
    user_requested: list[ToolRequestEnum] | None = None,
) -> IntentResult:
    """Decide the datasources for this turn.

    The user's datasource buttons (Eugene KG / Web / PubMed) are AUTHORITATIVE:
    if the user ticked any, we use exactly those and do NOT auto-add others.
    This keeps a "Eugene KG"-only question on the graph instead of pulling in
    web/pubmed tools (which also require internet egress the VPC may not have).

    Only when the user selected nothing do we infer from the prompt, always
    including EUGENE (the graph is the read-only, bounded default).
    """
    user = list(user_requested or [])
    reasons: list[str] = []

    if user:
        # Explicit selection wins — no silent expansion.
        return IntentResult(
            tools=sorted(set(user), key=lambda t: t.value),
            reason="user-selected datasources (authoritative)",
        )

    inferred: set[ToolRequestEnum] = {ToolRequestEnum.EUGENE}
    reasons.append("default to graph")
    if _WEB_RE.search(prompt) or _PATENT_RE.search(prompt):
        inferred.add(ToolRequestEnum.HTTP)
        reasons.append("web/patent keyword")
    if _PUBMED_RE.search(prompt):
        inferred.add(ToolRequestEnum.PUBMED)
        reasons.append("pubmed keyword")

    return IntentResult(
        tools=sorted(inferred, key=lambda t: t.value),
        reason=", ".join(reasons) or "none",
    )
