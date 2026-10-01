import logging
from typing import Annotated
from fastapi import APIRouter, Path
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_foundational_facet_adapter,
)
from foundation.router.validate_util import (
    str_to_label_enum,
    validate_label,
)
from foundation.router.model.facet_search_values import FacetSearchValues
from foundation.router.model.facet_label import FacetLabel


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/facet",
    tags=["facet"],
)

foundational_facet_adapter = neo4j_foundational_facet_adapter()


@router.post(
    "/{label}",
    response_model_exclude_none=True,
)
async def collect_facets_by_label_and_values(
    label: Annotated[
        FacetLabel,
        Path(
            description="The node type to list. e.g. drug, disease",
            max_length=64,
            min_length=0,
            examples=["drug, disease"],
        ),
        AfterValidator(validate_label),
    ],
    facet_search_values: FacetSearchValues,
):
    label_enum = str_to_label_enum(label.value[1])
    values = (
        facet_search_values.values if facet_search_values.values is not None else []
    )
    json_blob = foundational_facet_adapter.collect_facet_by_label(
        label=label_enum, values=values
    )
    logger.debug(f"facet: {json_blob}")
    return json_blob
