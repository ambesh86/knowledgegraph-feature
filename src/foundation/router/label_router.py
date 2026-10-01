import logging
from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_foundational_node_adapter,
)
from foundation.router.model.name_id_list_response import NameAndIdListResponse
from foundation.router.response_util import (
    to_id_list_response,
)
from foundation.router.validate_util import (
    validate_label,
)
from foundation.router.model.label import Label


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/labels",
    tags=["foundation"],
)

foundational_node_adapter = neo4j_foundational_node_adapter()


@router.get(
    "/{label}", response_model=NameAndIdListResponse, response_model_exclude_none=True
)
async def list_by_label(
    label: Annotated[
        Label,
        Path(
            description="The node type to list. e.g. drug, disease",
            max_length=64,
            min_length=1,
        ),
        AfterValidator(validate_label),
    ],
    page: Annotated[
        int,
        Query(
            description="Page number. See the count endpoint to calculate max page number.",
            example=1,
            gt=0,
        ),
    ],
    page_size: Annotated[
        int,
        Query(
            description="Page size.",
            example=25,
            gt=0,
            le=50,
        ),
    ],
):
    dataframe = foundational_node_adapter.find_by_label(label.value[1], page, page_size)
    return to_id_list_response(dataframe)
