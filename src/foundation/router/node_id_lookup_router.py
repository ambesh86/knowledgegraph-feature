import logging
from typing import Annotated
from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.router.validate_util import (
    validate_value,
)
from foundation.conf.conf import foundational_node_id_provider


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/node",
    tags=["foundation"],
)

node_id_provider = foundational_node_id_provider()


@router.get(
    "/find/{node_value}",
    response_model_exclude_none=True,
)
async def lookup_node_id_by_value(
    node_value: Annotated[
        str,
        Path(
            description="The node value to search",
            max_length=2048,
            min_length=0,
            example="Flurandrenolide",
        ),
        AfterValidator(validate_value),
    ],
    fuzzy_match: Annotated[
        bool,
        Query(
            title="True to do a fuzzy search, otherwise False. A fuzzy match is a regex match",
            example=False,
        ),
    ] = False,
):
    return node_id_provider.find_node_id_by_node_name(
        value=node_value, fuzzy_match=fuzzy_match
    )
