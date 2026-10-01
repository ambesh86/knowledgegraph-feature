from __future__ import annotations
from dataclasses import dataclass

from strands.agent.agent_result import AgentResult


@dataclass
class AgentMetrics:
    total_tokens: int
    execution_time: float
    tools_used: list[str]

    def __repr__(self) -> str:
        return (
            f"Total Tokens Used: {self.total_tokens}"
            f"Total Execution Time: {self.execution_time:.2f} seconds"
            f"Unique Tools Used: {len(self.tools_used)} ({', '.join(self.tools_used)})"
        )

    @staticmethod
    def of(result: AgentResult) -> AgentMetrics:
        if not result:
            raise ValueError("cannot build metrics from empty agent result!")
        total_tokens = result.metrics.accumulated_usage["totalTokens"]
        execution_time = sum(result.metrics.cycle_durations)
        tools_used = list(set(result.metrics.tool_metrics.keys()))
        return AgentMetrics(
            total_tokens=total_tokens,
            execution_time=execution_time,
            tools_used=tools_used,
        )
