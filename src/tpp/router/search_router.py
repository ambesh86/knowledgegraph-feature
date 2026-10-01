import logging
from typing import Annotated
from fastapi import APIRouter, Path
from pydantic import AfterValidator

from tpp.router.search_util import (
    EmbeddingSearchParams,
    SearchResponse,
    to_question_enum,
    to_search_response,
    validate_question_type,
)
from tpp.conf.eugene_ws_conf import (
    semantic_search_embedding_provider,
    tpp_search_orchestrator,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/embeddings",
    tags=["embeddings"],
)

search_orchestrator = tpp_search_orchestrator()
embedding_provider = semantic_search_embedding_provider()


@router.post("/", response_model=SearchResponse, response_model_exclude_none=True)
async def find_patents_by_embeddings(embedding_search_params: EmbeddingSearchParams):
    include_terms = embedding_search_params.include_terms
    exclude_terms = embedding_search_params.exclude_terms
    merged_embeddings = embedding_provider.to_embedding(
        include_terms=include_terms, exclude_terms=exclude_terms
    )
    results = search_orchestrator.find_patent_applications_by_embedding(
        merged_embeddings
    )
    return to_search_response(results)


@router.get(
    "/tpps/{tpp_id}", response_model=SearchResponse, response_model_exclude_none=True
)
async def find_patents_by_tpp_id(
    tpp_id: Annotated[
        str,
        Path(
            description="The id of the tpp to base your patent search",
            max_length=32,
            min_length=32,
        ),
    ],
):
    results = search_orchestrator.find_patent_applications_by_tpp(tpp_id=tpp_id)
    return to_search_response(results)


@router.get(
    "/tpps/{tpp_id}/graph",
    response_model=SearchResponse,
    response_model_exclude_none=True,
)
async def find_patents_by_tpp_id_and_graph_embeddings(
    tpp_id: Annotated[
        str,
        Path(
            description="The id of the tpp to base your patent search",
            max_length=32,
            min_length=32,
        ),
    ],
):
    results = search_orchestrator.find_patent_applications_by_tpp_and_graph_embeddings(
        tpp_id=tpp_id
    )
    return to_search_response(results)


@router.get(
    "/tpps/{tpp_id}/question/{question_type}",
    response_model=SearchResponse,
    response_model_exclude_none=True,
)
async def find_patents_by_tpp_id_and_question_embeddings(
    tpp_id: Annotated[
        str,
        Path(
            description="The id of the tpp to base your patent search",
            max_length=32,
            min_length=32,
        ),
    ],
    question_type: Annotated[
        str,
        Path(description="The tpp question type to narrow your patent search"),
        AfterValidator(validate_question_type),
    ],
):
    question = to_question_enum(question_type)
    logger.debug(f"tpp_id: {tpp_id} question_type: {question_type}")
    results = search_orchestrator.find_patent_applications_by_tpp_question(
        tpp_id=tpp_id, tpp_question=question
    )
    return to_search_response(results)
