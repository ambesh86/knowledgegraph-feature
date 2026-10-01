import logging

from mlflow import genai

from prompt.const import (
    ON_TOPIC_PROMPT_NAME,
    ORGANIZATION_RESOLUTION_PROMPT_NAME,
    ORGANIZATION_VERIFICATION_PROMPT_NAME,
)
from prompt.prompts import (
    generate_organization_name_verification_prompt,
    organization_resolution_prompt,
    generate_on_topic_prompt,
)

logger = logging.getLogger(__name__)


def ensure_registered_prompts() -> None:
    ensure_registered_prompt(
        name=ORGANIZATION_RESOLUTION_PROMPT_NAME,
        prompt=organization_resolution_prompt(),
    )
    ensure_registered_prompt(
        name=ORGANIZATION_VERIFICATION_PROMPT_NAME,
        prompt=generate_organization_name_verification_prompt(),
    )
    ensure_registered_prompt(
        name=ON_TOPIC_PROMPT_NAME,
        prompt=generate_on_topic_prompt(),
    )


def ensure_registered_prompt(name: str, prompt: str) -> None:
    prompts = genai.search_prompts(filter_string=f"name = '{name}'")
    logger.info(f"Found {len(prompts)} prompts with name {name}")
    if not prompts:
        logger.info(f"Registering prompt: {name}")
        # Register a new prompt
        genai.register_prompt(
            name=name,
            template=prompt,
            commit_message="initial commit",
            tags={
                "author": "damianknopp@cslbehring.com",
                "environment": "development",
            },
        )
