import logging
from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_foundational_similarity_adapter,
)
from foundation.router.response_util import (
    to_similarity_response,
)
from foundation.router.validate_util import (
    str_to_label_enum,
    validate_label,
)
from foundation.router.model.similarity_search_values import SimilaritySearchValues
from foundation.router.model.facet_label import FacetLabel


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/similarity",
    tags=["similarity"],
)

foundational_similarity_adapter = neo4j_foundational_similarity_adapter()


@router.post(
    "/{label}",
    response_model_exclude_none=True,
)
async def calculate_similarity_by_label_and_values(
    label: Annotated[
        FacetLabel,
        Path(
            description="The node type to list. e.g. disease, drug",
            max_length=64,
            min_length=0,
            examples=["disease, drug"],
        ),
        AfterValidator(validate_label),
    ],
    similarity_search_values: SimilaritySearchValues,
):
    label_enum = str_to_label_enum(label.value[1])
    values = (
        similarity_search_values.values
        if similarity_search_values.values is not None
        else []
    )
    dataframe = foundational_similarity_adapter.calculate_similar_by_label_and_values(
        label=label_enum, values=values
    )
    logger.debug(f"similar: {dataframe}")
    return to_similarity_response(dataframe)
