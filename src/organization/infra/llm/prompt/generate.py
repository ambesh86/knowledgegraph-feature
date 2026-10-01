import logging

from infra.llm.prompt.goal_prompt_title import GoalPromptTitle
from organization.infra.llm.prompt.const import (
    PROMPT_ANALYZE_ORGANIZATION_INPUT_KEY,
    PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY,
    PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY,
)


logger = logging.getLogger(__name__)


PROMPT_GOAL = "goal"
PROMPT_TITLE = "title"


def generate_organization_name_analysis_input_params(
    organization_name: str = "",
) -> dict[str, str]:
    return generate_input_params(
        goal=generate_organization_name_analysis_prompt(),
        organization_name=organization_name,
        title=GoalPromptTitle.GOAL_BASED_ANALYSIS,
    )


def generate_organization_name_verification_input_params(
    organization_name: str = "",
) -> dict[str, str]:
    return {
        PROMPT_GOAL: generate_organization_name_verification_prompt(),
        PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: organization_name,
        PROMPT_TITLE: GoalPromptTitle.GOAL_BASED_ANALYSIS.name,
    }


def generate_organization_acquisition_verification_input_params(
    organization_name: str = "",
    organization_relationships: str = "",
) -> dict[str, str]:
    return {
        PROMPT_GOAL: generate_organization_acquisition_verification_prompt(),
        PROMPT_VERIFY_ORGANIZATION_NAME_INPUT_KEY: organization_name,
        PROMPT_VERIFY_ORGANIZATION_REALTIONSHIPS_INPUT_KEY: organization_relationships,
        PROMPT_TITLE: GoalPromptTitle.GOAL_BASED_ANALYSIS.name,
        "max_tokens_to_sample": "10_000",
    }


def generate_input_params(
    goal: str, organization_name: str, title: GoalPromptTitle
) -> dict[str, str]:
    return {
        PROMPT_GOAL: goal,
        PROMPT_ANALYZE_ORGANIZATION_INPUT_KEY: organization_name,
        PROMPT_TITLE: title.name,
    }


def generate_organization_name_analysis_prompt() -> str:
    return """
-Goal-
Find the company names for the given government, non profit organization, university, hospital, biomedical company, or pharmaceutical company.
-Steps-
1. Categorize the organization name as one of the following types: [company, hospital, university, nonprofit, foundation, government, or organization]
2. Use the generic value "organization" if no given organization category value applies.
1. Find spelling variations, mergers, demergers, parent companies, subsidiaries, and operations in different countries.
2. For international companies be sure to include titles such as; Pte Ltd, SRL, GmbH, Inc, ApS, LLC, Inc, Sp zoo, and AB.
3. If the given company is the parent name list it under parent company.
4. Be sure to include all names.
5. Do not include year of acquisition.
6. When finished, output as JSON with the following schema
{{
    "official_name": "",
    "parent": "",
    "subsidiaries": [],
    "acquisitions": [],
    "spelling_variations": [],
    "mergers": [],
    "demergers": [],
    "organization_type": ""
}}

#######
-Data-
Organization Name: {organization_name}
"""


def generate_organization_name_verification_prompt() -> str:
    return """
-GOAL-
Confirm the following organization data is accurate. Fix fictional organization names. Fix concatenated organization names. Do not hallucinate. Only output the results as JSON with the following schema

-OUTPUT SCHEMA-
{{
    “input”: “”,
    “valid_organization_name”: true or false 
}}

-INPUT DATA-
Organization Name: {organization_name}
"""


def generate_organization_acquisition_verification_prompt() -> str:
    return """
-GOAL-
Confirm the following organization data is accurate. List any acquisitions that cannot be verified or seem incorrect. List fictional organization names. List partnerships incorrectly labeled as acquisitions. List nonexistent acquisitions. Only output the results as JSON with the following schema.

-OUTPUT SCHEMA-
{{
    “invalid_acquisitions": []
}}

-INPUT DATA-
Organization Name: {organization_name}
Relationships: {organization_relationships}
"""
