import logging
from typing import Annotated
from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    foundational_path_provider,
)
from foundation.router.validate_util import (
    validate_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graph",
    tags=["foundation"],
)

search_path_provider = foundational_path_provider()


@router.get(
    "/path/start/{start_id}/end/{end_id}",
    response_model_exclude_none=True,
)
async def find_search_paths_by_start_id_and_end_id(
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
        str,
        Path(
            description="The end node id to begin the n hop query",
            max_length=512,
            min_length=0,
            example="DB00538",
        ),
        AfterValidator(validate_id),
    ],
    n_hop: Annotated[
        int,
        Query(
            title="The max number of hops in the path",
            example=2,
            gt=0,
            le=4,
        ),
    ],
):
    return search_path_provider.find_shortest_path_by_start_id_and_end_id(
        start_id=start_id, end_id=end_id, n_hop=n_hop
    )


@router.get(
    "/reachability/start/{start_id}/end/{end_id}",
    response_model_exclude_none=True,
)
async def find_is_reachable_by_start_id_and_end_id(
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
        str,
        Path(
            description="The end node id to begin the n hop query",
            max_length=512,
            min_length=0,
            example="DB00538",
        ),
        AfterValidator(validate_id),
    ],
    n_hop: Annotated[
        int,
        Query(
            title="The max number of hops in the path",
            example=2,
            gt=0,
            le=4,
        ),
    ],
):
    reachable = search_path_provider.find_is_reachable_by_start_id_and_end_id(
        start_id=start_id, end_id=end_id, n_hop=n_hop
    )
    logger.info(f"{reachable}")
    return reachable
