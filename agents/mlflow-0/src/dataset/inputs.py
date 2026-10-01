import logging
from typing import Any

from prompt.prompts import generate_on_topic_prompt, organization_resolution_prompt

logger = logging.getLogger(__name__)

CSL_ORG_NAME = "CSL BEHRING LLC"

def generate_csl_resolution_dataset_entry() -> dict[str, Any]:
    prompt = organization_resolution_prompt()
    prompt = prompt.replace("{organization_name}", CSL_ORG_NAME)
    logger.debug(f"Generated prompt: {prompt}")
    # must mention is a custom scorer
    dataset_entry = {
        "inputs": {
            "question": prompt,
            "temperature": 0.7,
        },
        "expectations": {
            "expected_response": "CSL BEHRING LLC",
            "must_mention": [
                "csl",
                "csl behring",
                "csl ltd",
                "csl behring llc",
                "csl behring gmbh",
            ],
        },
    }
    logger.debug(f"Entry: {dataset_entry}")
    return dataset_entry


def generate_csl_resolution_dataset_bedrock_test_entry() -> dict[str, Any]:
    # must mention is a custom scorer
    dataset_entry = {
        "inputs": {
            "organization_name": CSL_ORG_NAME,
        },
        "expectations": {
            "expected_response": "CSL BEHRING LLC",
            "must_mention": [
                "csl",
                "csl behring",
                "csl ltd",
                "csl behring llc",
                "csl behring gmbh",
            ],
        },
    }
    logger.debug(f"Entry: {dataset_entry}")
    return dataset_entry


def generate_on_topic_dataset_entry_0() -> dict[str, Any]:
    prompt = generate_on_topic_prompt()
    prompt = prompt.replace("{user_question}", "How do I cook the perfect steak on a campfire?")
    logger.debug(f"Generated prompt: {prompt}")
    dataset_entry = {
        "inputs": {
            "question": prompt,
            "temperature": 0.7,
        },
        "expectations": {
            "expected_response": "0",
        },
    }
    logger.debug(f"Entry: {dataset_entry}")
    return dataset_entry


def generate_on_topic_dataset_entry_1() -> dict[str, Any]:
    prompt = generate_on_topic_prompt()
    prompt = prompt.replace("{user_question}", "What PSI should my tire be during the winter?")
    logger.debug(f"Generated prompt: {prompt}")
    dataset_entry = {
        "inputs": {
            "question": prompt,
            "temperature": 0.7,
        },
        "expectations": {
            "expected_response": "0",
        },
    }
    logger.debug(f"Entry: {dataset_entry}")
    return dataset_entry


def generate_on_topic_dataset_entry_2() -> dict[str, Any]:
    prompt = generate_on_topic_prompt()
    prompt = prompt.replace("{user_question}", "List drug aliases for Adderall")
    logger.debug(f"Generated prompt: {prompt}")
    dataset_entry = {
        "inputs": {
            "question": prompt,
            "question": prompt,
            "temperature": 0.7,
        },
        "expectations": {
            "expected_response": "8",
        },
    }
    logger.debug(f"Entry: {dataset_entry}")
    return dataset_entry
