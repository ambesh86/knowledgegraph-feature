import logging
from typing import Callable

from mlflow import genai

from mlflow.genai.scorers import Guidelines, Correctness, RelevanceToQuery
from mlflow.genai.datasets.evaluation_dataset import EvaluationDataset

from openai import OpenAI

from evaluate.scorers.scorers import contains_required_mentions

client = OpenAI()

logger = logging.getLogger(__name__)


def evaluate_organization_resolution_prompt(
    dataset: EvaluationDataset, predict_fn: Callable
):
    valid_json = Guidelines(
        name="valid_json",
        guidelines=["The response must contain valid JSON"],
    )
    required_json_keys = Guidelines(
        name="required_json_keys",
        guidelines=["The response must contain populated official_name json key"],
    )
    # todo:
    # mlflow 3.9+ you can specify a model, until then it defaults to openai?
    correctness = Correctness(name="correctness")
    relevance = RelevanceToQuery(name="relevant response")

    data = dataset.to_df()
    logger.debug(f"{data}")

    genai.evaluate(
        data=data,
        predict_fn=predict_fn,
        scorers=[
            valid_json,
            required_json_keys,
            contains_required_mentions,
            correctness,
            relevance,
        ],
    )


def evaluate_on_topic_prompt(dataset: EvaluationDataset, predict_fn: Callable):
    valid_json = Guidelines(
        name="valid_json",
        guidelines=["The response must contain valid JSON, JSON surrounded by backticks or embedded in markdown is still considered valid"],
    )
    required_json_keys = Guidelines(
        name="required_json_keys",
        guidelines=["The response must contain populated score json key"],
    )
    # todo:
    # mlflow 3.9+ you can specify a model, until then it defaults to openai?
    correctness = Correctness(name="correctness")

    relevance = RelevanceToQuery(name="relevant response")

    data = dataset.to_df()
    logger.debug(f"{data}")

    genai.evaluate(
        data=data,
        predict_fn=predict_fn,
        scorers=[
            valid_json,
            required_json_keys,
            correctness,
            relevance,
        ],
    )
