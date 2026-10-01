import logging

import mlflow

from mlflow.genai.datasets.evaluation_dataset import EvaluationDataset

from openai import OpenAI

from evaluate.evaluate import evaluate_on_topic_prompt

client = OpenAI()

logger = logging.getLogger(__name__)


def openai_evaluate_on_topic_prompt(dataset: EvaluationDataset):
    evaluate_on_topic_prompt(dataset, predict_fn)


@mlflow.trace
def predict_fn(question: str, temperature: float) -> str:
    logger.debug(f"question: {question}")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            # {
            #     "role": "system",
            #     "content": "What recent pubmed studies mention ABL1?",
            # },
            {"role": "user", "content": question},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content
