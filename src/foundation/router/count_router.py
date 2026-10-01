import logging
from typing import Annotated, Any

from fastapi import APIRouter, Path
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_foundational_node_count_adapter,
)
from foundation.router.validate_util import (
    validate_label,
)
from foundation.router.model.label import Label


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/count",
    tags=["foundation"],
)

foundational_node_count_adapter = neo4j_foundational_node_count_adapter()


@router.get(
    "/{label}", response_model=dict[str, int | str], response_model_exclude_none=True
)
async def count_by_label(
    label: Annotated[
        Label,
        Path(
            description="The node type to count. e.g. drug, disease",
            max_length=64,
            min_length=1,
        ),
        AfterValidator(validate_label),
    ],
):
    label_value = label.value[1]
    count = foundational_node_count_adapter.count_all_by_label(label_value)
    return {"count": count, "label": label_value}
