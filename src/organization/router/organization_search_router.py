import logging
from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.router.validate_util import (
    validate_id,
)
from foundation.router.model.generic_list_response import GenericListResponse
from organization.conf.search_conf import organization_search_adapter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)

org_search_adapter = organization_search_adapter()


@router.get(
    "/{organization_name}",
    response_model=GenericListResponse,
    response_model_exclude_none=True,
)
async def list_organization_names(
    organization_name: Annotated[
        str,
        Path(
            description="Limited regex to use to search organization names to paginate. Accepts ['*' or '?'] only, others are escaped",
            max_length=256,
            min_length=0,
            example="csl*",
        ),
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
            example=10,
            gt=0,
            le=500,
        ),
    ],
):
    results = org_search_adapter.find_companies_by_name_pattern(
        name_pattern=organization_name, page=page, page_size=page_size
    )
    count = len(results) if results else 0
    return GenericListResponse(count=count, results=results)


@router.get(
    "/assets/{organization_id}",
    response_model_exclude_none=True,
)
async def list_organization_assets(
    organization_id: Annotated[
        str,
        Path(
            description="The organization id to use when searching for organization assets",
            max_length=256,
            min_length=0,
            example="H003644",
        ),
        AfterValidator(validate_id),
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
            example=10,
            gt=0,
            le=500,
        ),
    ],
):
    results = org_search_adapter.find_assets_by_org_id(
        org_id=organization_id, page=page, page_size=page_size
    )
    logger.info(f"results: {results}")
    count = len(results) if results else 0
    return GenericListResponse(count=count, results=results)
