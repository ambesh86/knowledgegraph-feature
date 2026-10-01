"""Authoritative clock for the agent.

Why this exists: the model has no reliable sense of "now". Its training cutoff is
the only date it knows from the inside, so when asked what "as of now" means it
answers with that cutoff — which is how a 2026 deployment ended up telling a user
"as of now means June 2024". That is not a data problem and no amount of live tool
calling fixes it, because the model reconciles fresh results against a "now" it
believes is two years ago.

The fix is to state the date as an instruction, at the very top of every system
prompt, on every turn. We deliberately do NOT solve this with the `current_time`
tool: utility tools are gated off because they caused runaway ReAct loops (Stage 1
Assessment §04.2), and a tool call is skippable in a way a directive is not.
"""
from __future__ import annotations

import datetime as dt


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def today_iso() -> str:
    return now_utc().date().isoformat()


def human_today() -> str:
    """e.g. 'Saturday, 01 August 2026'."""
    return now_utc().strftime("%A, %d %B %Y")


def build_temporal_directive(
    online: bool = True,
    snapshot_date: str | None = None,
) -> str:
    """The clock block, prepended before every other directive.

    Args:
        online: whether live external sources are reachable this turn.
        snapshot_date: ISO date the internal graph/vector stores were last
            refreshed, when known. Used so "as of" can resolve to a real date
            for internal facts instead of an implied "now".
    """
    today = today_iso()
    lines = [
        "CURRENT DATE — AUTHORITATIVE, READ BEFORE ANYTHING ELSE.",
        f"Today is {human_today()} ({today} UTC).",
        "This date is supplied by the system and OVERRIDES anything you believe about the "
        "current date. Your training cutoff is NOT today. It is a fact about you, not about "
        "the world, and it must NEVER be presented to the user as 'now', 'currently', "
        "'as of now', 'to date', or 'the latest available'.",
        "",
        "DATING RULES — every answer must be explicitly dated.",
        f"1. State what date your information is for. Live tool results are current as of "
        f"{today}. Internal Eugene graph/vector results are current as of the snapshot date, "
        "NOT today.",
        "2. If the user asks what 'as of now' or 'currently' means, the answer is "
        f"{today} — never your training cutoff.",
        "3. NEVER claim something is 'the latest' or 'as of now' unless a live tool actually "
        "returned it on this turn. If you did not verify it live, say plainly where and when "
        "your information is from, e.g. 'the Eugene snapshot dated X shows …'.",
        "4. Research loses value as it ages. When you return results, prefer the most recent "
        "and say how recent they are. If the newest thing you found is more than ~12 months "
        "old, flag that explicitly so the user can judge it.",
        "5. Every tool result carries `retrieved_at` and a `freshness` block. Use those real "
        "values when you date a claim — do not guess a date and do not reuse a date from "
        "your training data.",
    ]

    if snapshot_date:
        lines += [
            "",
            f"INTERNAL SNAPSHOT DATE: the Eugene knowledge graph and vector store were last "
            f"refreshed on {snapshot_date}. Facts drawn from them are current as of that date, "
            "not today. Say so when you use them.",
        ]

    if not online:
        lines += [
            "",
            "⚠️ OFFLINE THIS TURN — the live internet is NOT reachable. You have ONLY the "
            "internal Eugene snapshot. You MUST open your answer with an explicit warning in "
            f"substantially these words: \"Today is {today}, but I currently have no internet "
            "access, so this answer comes only from the internal Eugene snapshot"
            + (f" dated {snapshot_date}" if snapshot_date else "")
            + " and may be out of date.\" Do NOT present snapshot data as current, do NOT "
            "claim you checked a live source, and do NOT invent recent findings to fill the gap.",
        ]

    return "\n".join(lines)
