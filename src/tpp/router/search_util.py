import logging
from pydantic import BaseModel

from tpp.infra.db.model.tpp_search_result import TppSearchResult
from tpp.model.question_type_enum import QuestionTypeEnum

logger = logging.getLogger(__name__)


class SearchResponse(BaseModel):
    count: int
    results: list[TppSearchResult]


class EmbeddingSearchParams(BaseModel):
    include_terms: str
    exclude_terms: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "include_terms": "Hemophilia A non-viral, in vivo GenM",
                    "exclude_terms": "von Willebrand Disease",
                }
            ]
        }
    }


def to_question_enum(question_type: str | None) -> QuestionTypeEnum:
    valid_question_types = [el.name for el in list(QuestionTypeEnum)]
    if question_type is None:
        raise ValueError(
            f"question types cannot be None. Valid types: {valid_question_types}"
        )
    logger.info(f"question to enum: {question_type}")
    try:
        return QuestionTypeEnum[question_type.upper()]
    except:
        raise ValueError(
            f"{question_type} is not a valid question type. Valid types: {valid_question_types}"
        )


def validate_question_type(question_type: str) -> str:
    to_question_enum(question_type)
    return question_type


def to_search_response(
    results: list[TppSearchResult] | None,
) -> SearchResponse:
    if results is None:
        return SearchResponse(count=0, results=[])

    return SearchResponse(count=len(results), results=results)
