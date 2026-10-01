import logging
from typing import Annotated
from fastapi import APIRouter, Path
from pydantic import AfterValidator

from foundation.router.model.list_response import ListResponse
from foundation.router.validate_util import (
    validate_value,
)
from organization.conf.search_conf import organization_adapter


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/list",
    tags=["organization"],
)

org_adapter = organization_adapter()


"""
@deprecated the organization datamodel was change and no longer supports aliases
"""


@router.get(
    "/organization/aliases/{organization_name}",
    response_model=ListResponse,
    response_model_exclude_none=True,
)
async def list_organization_aliases(
    organization_name: Annotated[
        str,
        Path(
            description="The organization name to list aliases for",
            max_length=256,
            min_length=0,
            example="CSL Behring",
        ),
        AfterValidator(validate_value),
    ],
):
    aliases = org_adapter.find_aliases_by_name(organization=organization_name)
    if aliases is None:
        return ListResponse(count=0, results=[])
    aliases.sort()
    return ListResponse(count=len(aliases), results=aliases)
