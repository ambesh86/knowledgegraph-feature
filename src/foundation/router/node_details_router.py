import logging
from typing import Annotated
from fastapi import APIRouter
from pydantic import AfterValidator

from foundation.router.validate_util import (
    validate_node_details_request,
)
from foundation.conf.conf import (
    foundational_node_details_provider,
)
from foundation.router.model.node_details_request import NodeDetailsRequest


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/node",
    tags=["foundation"],
)

node_details_provider = foundational_node_details_provider()


@router.post(
    "/details",
    response_model_exclude_none=True,
)
async def lookup_node_details_by_id(
    node_details_request: Annotated[
        NodeDetailsRequest,
        AfterValidator(validate_node_details_request),
    ],
):
    ids = set(node_details_request.ids)
    return node_details_provider.find_node_details_by_node_ids(ids)
