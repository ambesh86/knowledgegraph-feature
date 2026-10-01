import logging

from mlflow.genai.scorers import scorer

logger = logging.getLogger(__name__)


@scorer
def contains_required_mentions(outputs: str, expectations: dict) -> float:
    """Check if response contains required information."""
    if "must_mention" not in expectations:
        return 1.0

    output_lower = outputs.lower()
    mentioned = [term for term in expectations["must_mention"] if term in output_lower]
    return len(mentioned) / len(expectations["must_mention"])


# @scorer
# def greater_than_equal(outputs: str, expectation: int) -> float:
#     """Check if response contains required information."""
#     logger.info(f"greater_than_equal expectations: {expectation} outputs: {outputs}")
    
#     # score = expectations[score]
#     # payload = json.loads(outputs.lower())
#     # payoad_score = payload["score"]
#     # return val 
#     return 1
