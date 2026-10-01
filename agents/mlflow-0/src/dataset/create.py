import logging

from mlflow.entities import Experiment
from mlflow.genai.datasets import create_dataset, search_datasets, EvaluationDataset

from dataset.const import (
    ON_TOPIC_DATASET,
    ORGANIZATION_RESOLUTION_BEDROCK_TEST_DATASET,
    ORGANIZATION_RESOLUTION_DATASET,
)
from dataset.inputs import (
    generate_csl_resolution_dataset_bedrock_test_entry,
    generate_csl_resolution_dataset_entry,
    generate_on_topic_dataset_entry_0,
    generate_on_topic_dataset_entry_1,
    generate_on_topic_dataset_entry_2,
)

logger = logging.getLogger(__name__)


def ensure_create_on_topic_datasets(expirement: Experiment):
    name = ON_TOPIC_DATASET
    dataset = ensure_create_datasets(expirement, name)
    dataset.merge_records(
        [
            generate_on_topic_dataset_entry_0(),
            generate_on_topic_dataset_entry_1(),
            generate_on_topic_dataset_entry_2(),
        ]
    )


def ensure_create_organization_resolution_bedrock_test_datasets(expirement: Experiment):
    name = ORGANIZATION_RESOLUTION_BEDROCK_TEST_DATASET
    dataset = ensure_create_datasets(expirement, name)
    dataset.merge_records([generate_csl_resolution_dataset_bedrock_test_entry()])


def ensure_create_organization_resolution_datasets(expirement: Experiment):
    name = ORGANIZATION_RESOLUTION_DATASET
    dataset = ensure_create_datasets(expirement, name)
    dataset.merge_records([generate_csl_resolution_dataset_entry()])


def ensure_create_datasets(expirement: Experiment, name: str) -> EvaluationDataset:
    test_datasets = search_dataset_by_name(expirement, name)
    logger.info(f"Found {len(test_datasets)} dataset with name {name}")
    if test_datasets:
        logger.info("Dataset already exists. Skipping initialization...")
        return test_datasets[0]

    dataset = create_dataset(
        name=name,
        experiment_id=expirement.experiment_id,
        tags={
            "version": "1.0",
            "author": "damianknopp@cslbehring.com",
            "environment": "development",
        },
    )
    logger.info(f"Created dataset with ID: {dataset.dataset_id}")
    return dataset


def search_dataset_by_name(expirement: Experiment, name: str):
    test_datasets = search_datasets(
        experiment_ids=[expirement.experiment_id],
        filter_string=f"name = '{name}'",
        order_by=["created_time ASC"],
    )
    return test_datasets
