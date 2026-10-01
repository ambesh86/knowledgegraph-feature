import logging
from typing import Annotated
from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    foundational_facts_orchestrator,
)
from foundation.router.validate_util import (
    validate_id,
)
from foundation.router.model.list_response import ListResponse


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graph",
    tags=["facts"],
)

facts_orchestrator = foundational_facts_orchestrator()


@router.get(
    "/facts/start/{start_id}",
    response_model=ListResponse,
    response_model_exclude_none=True,
)
async def find_n_hop(
    start_id: Annotated[
        str,
        Path(
            description="The start node id to begin collecting facts",
            max_value=512,
            min_length=0,
            example="19725",
        ),
        AfterValidator(validate_id),
    ],
    page: Annotated[
        int,
        Query(
            description="Page number. See the count endpoint to calculate max page number.",
            example=4,
            gt=0,
        ),
    ],
    page_size: Annotated[
        int,
        Query(
            description="Page size.",
            example=10,
            gt=0,
            le=50,
        ),
    ],
    # n_hop: Annotated[
    #     int,
    #     Query(
    #         title="The max number of hops to collect facts, defaults to 1",
    #         example=1,
    #         gt=0,
    #         le=1,
    #     ),
    # ] = 1,
):
    facts = facts_orchestrator.find_facts_by_start_id(
        start_id=start_id, n_hop=1, page_size=page_size, page=page
    )

    if facts is None:
        return ListResponse(count=0, results=[])

    return ListResponse(count=len(facts), results=list(facts))
