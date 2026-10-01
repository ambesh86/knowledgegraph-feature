from __future__ import annotations

from .shared import configure_shared_agent_imports

configure_shared_agent_imports()

from query.model.tool_request_enum import ToolRequestEnum
from query.util.intent_classifier import classify_intent

SPECIALIST_REGISTRY = {
    "eugene_graph": (ToolRequestEnum.EUGENE,),
    "clinical_trials": (ToolRequestEnum.CLINICAL_TRIALS,),
    "pubmed": (ToolRequestEnum.PUBMED,),
    "web": (ToolRequestEnum.HTTP,),
}

_SOURCE_TO_SPECIALISTS = {
    ToolRequestEnum.EUGENE: ("eugene_graph",),
    ToolRequestEnum.CLINICAL_TRIALS: ("clinical_trials",),
    ToolRequestEnum.PUBMED: ("pubmed",),
    ToolRequestEnum.HTTP: ("web",),
    ToolRequestEnum.ALL_SOURCES: (
        "eugene_graph",
        "clinical_trials",
        "pubmed",
    ),
}


def select_specialists(prompt: str, requested_sources: list[str] | None = None) -> list[str]:
    """Apply Eugene's authoritative source selection and map it to specialists."""
    requested = [ToolRequestEnum(value) for value in (requested_sources or [])]
    intent = classify_intent(prompt, requested or None)
    specialists: list[str] = []
    for source in intent.tools:
        for specialist in _SOURCE_TO_SPECIALISTS[source]:
            if specialist not in specialists:
                specialists.append(specialist)
    return specialists or ["eugene_graph"]