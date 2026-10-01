import logging
from typing import Annotated
from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    foundational_n_hop_provider,
)
from foundation.router.validate_util import (
    validate_id,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graph",
    tags=["foundation"],
)

n_hop_provider = foundational_n_hop_provider()


@router.get(
    "/relationship/start/{start_id}",
    response_model_exclude_none=True,
)
async def find_n_hop(
    start_id: Annotated[
        str,
        Path(
            description="The start node id to begin the n hop query",
            max_value=512,
            min_length=0,
            example="DB00846",
        ),
        AfterValidator(validate_id),
    ],
    end_id: Annotated[
        str | None,
        Query(
            description="The optional end node id to end the n hop query",
            max_length=512,
            example="DB00538",
        ),
        AfterValidator(validate_id),
    ] = None,
    n_hop: Annotated[
        int,
        Query(
            title="The max number of hops in the path, defaults to 1",
            example=2,
            gt=0,
            le=2,
        ),
    ] = 1,
):
    return n_hop_provider.find_subgraph_by_start_id_and_end_id(
        start_id=start_id, end_id=end_id, n_hop=n_hop
    )
