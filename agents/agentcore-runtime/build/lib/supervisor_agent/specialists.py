from __future__ import annotations

import logging
import os
from typing import Any

from .shared import configure_shared_agent_imports

configure_shared_agent_imports()

from query.agent.eugene_data_agent import EugeneDataAgent
from query.conf.conf import llm_model
from query.model.tool_request_enum import ToolRequestEnum
from query.tools.external_tools import (
    search_clinical_trials,
    search_europepmc,
    search_patents_web,
    search_pubmed,
)
from query.util.response import unwrap_agent_result
from strands import Agent
from strands_tools import http_request

logger = logging.getLogger(__name__)

_DOMAIN_CONFIG = {
    "clinical_trials": {
        "name": "ClinicalTrialsSpecialist",
        "tools": [search_clinical_trials],
        "prompt": (
            "You are the ClinicalTrials.gov research specialist. Answer only from "
            "the live search_clinical_trials tool results. Preserve real NCT ids, "
            "status, dates, and URLs; state when live lookup fails or returns no hits."
        ),
    },
    "pubmed": {
        "name": "LiteratureSpecialist",
        "tools": [search_pubmed, search_europepmc],
        "prompt": (
            "You are the biomedical literature specialist. Answer only from live "
            "PubMed/Europe PMC tool results. Preserve real PMID or record identifiers, "
            "publication dates, and URLs; do not invent citations."
        ),
    },
    "web": {
        "name": "WebResearchSpecialist",
        "tools": [search_patents_web, search_clinical_trials, http_request],
        "prompt": (
            "You are the live web and patent research specialist. Use the supplied "
            "tools only, report the source and retrieval limitations, and never "
            "invent a result or URL."
        ),
    },
}


def run_specialist(
    specialist: str,
    *,
    prompt: str,
    access_token: str | None,
    conversation_id: str,
) -> str:
    if specialist == "eugene_graph":
        token = access_token or os.environ.get("EUGENE_MCP_BEARER_TOKEN")
        if not token:
            raise RuntimeError(
                "Eugene graph access requires an Authorization bearer token or "
                "EUGENE_MCP_BEARER_TOKEN."
            )
        agent = EugeneDataAgent(
            eugene_mcp_server_url=os.environ["EUGENE_MCP_SERVER_URL"],
            model=llm_model(),
        )
        result = agent.execute(
            token=token,
            user_prompt=prompt,
            conversation_id=conversation_id,
            include_tools=[ToolRequestEnum.EUGENE],
        )
        return unwrap_agent_result(result)

    config: dict[str, Any] | None = _DOMAIN_CONFIG.get(specialist)
    if config is None:
        raise ValueError(f"Unregistered specialist: {specialist}")
    agent = Agent(
        name=config["name"],
        model=llm_model(),
        tools=config["tools"],
        system_prompt=config["prompt"],
    )
    return unwrap_agent_result(agent(prompt))


def registered_specialists() -> tuple[str, ...]:
    return ("eugene_graph", *_DOMAIN_CONFIG.keys())