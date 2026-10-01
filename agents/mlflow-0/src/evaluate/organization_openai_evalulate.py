import logging

import mlflow

from mlflow.genai.datasets.evaluation_dataset import EvaluationDataset

from openai import OpenAI

from evaluate.evaluate import evaluate_organization_resolution_prompt

client = OpenAI()

logger = logging.getLogger(__name__)


def openai_evaluate_organization_resolution_prompt(dataset: EvaluationDataset):
    evaluate_organization_resolution_prompt(dataset, predict_fn)


@mlflow.trace
def predict_fn(question: str, temperature: float) -> str:
    # Set these metadata keys to associate the trace to a user and session
    # mlflow.update_current_trace(
    #     metadata={
    #         "mlflow.trace.user": "test_user",
    #         "mlflow.trace.session": "session_1",
    #     }
    # )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely.",
            },
            {"role": "user", "content": question},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content
