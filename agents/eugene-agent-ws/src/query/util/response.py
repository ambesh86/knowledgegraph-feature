from typing import Any
from strands.agent.agent_result import AgentResult


def unwrap_agent_result(resp: AgentResult) -> str:
    d = resp.to_dict()
    return unwrap_agent_dict_result(d)


def unwrap_agent_dict_result(d: dict[str, Any]) -> str:
    return d["message"]["content"][0]["text"]
