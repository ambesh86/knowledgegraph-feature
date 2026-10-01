import logging
import mlflow

from conf.const import EXPERIMENT_NAME
from conf.mlflow import enable_mlflow_tracing, set_mlflow_params
from dataset.const import ON_TOPIC_DATASET, ORGANIZATION_RESOLUTION_BEDROCK_TEST_DATASET
from dataset.create import (
    ensure_create_on_topic_datasets,
    ensure_create_organization_resolution_bedrock_test_datasets,
    search_dataset_by_name,
)
from prompt.register import ensure_registered_prompts
from util import parse_args, parse_items_to_run

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    with mlflow.start_run():
        args = parse_args()
        items_to_run = parse_items_to_run(args)
        _setup()
        _run_eval(items_to_run)


def _setup():
    set_mlflow_params()
    enable_mlflow_tracing()
    ensure_registered_prompts()
    mlflow.log_param("EXPERIMENT", EXPERIMENT_NAME)

    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        exit(0)
    logger.info("✓ Successfully connected to MLflow!")

    ensure_create_organization_resolution_bedrock_test_datasets(experiment)
    ensure_create_on_topic_datasets(experiment)


def _run_eval(items_to_run: list[str]) -> None:
    if not items_to_run or len(items_to_run) == 0:
        logger.info("No items to run")
        return

    logger.info(f"running evaluation of {EXPERIMENT_NAME}")
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if not experiment:
        logger.info(f"failed to look up the current experiment")
        return

    if "organization_resolution" in items_to_run:
        _run_organization_resolution(experiment)

    if "on_topic" in items_to_run:
        _run_on_topic(experiment)


def _run_organization_resolution(experiment) -> None:
    from evaluate.organization_bedrock_evaluate import (
        bedrock_evaluate_organization_resolution_prompt,
    )

    logger.info(f"running organization_resolution")
    datasets = search_dataset_by_name(
        expirement=experiment, name=ORGANIZATION_RESOLUTION_BEDROCK_TEST_DATASET
    )
    bedrock_evaluate_organization_resolution_prompt(dataset=datasets[0])


def _run_on_topic(experiment) -> None:
    from evaluate.organization_bedrock_evaluate import (
        bedrock_evaluate_organization_resolution_prompt,
    )

    logger.info(f"running on_topic")
    datasets = search_dataset_by_name(expirement=experiment, name=ON_TOPIC_DATASET)
    bedrock_evaluate_organization_resolution_prompt(dataset=datasets[0])


if __name__ == "__main__":
    main()
