import logging
from typing import Annotated
from fastapi import APIRouter, Path, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    drug_aliases_result_mapper,
    neo4j_drug_aliases_adapter,
)
from foundation.router.validate_util import (
    validate_value,
)
from foundation.model.drug.drug_alias_search_result import DrugAliasSearchResult
from foundation.model.case_helper import normalize_drug_id


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/drugs",
    tags=["drugs"],
)

drug_aliases_adapter = neo4j_drug_aliases_adapter()
result_mapper = drug_aliases_result_mapper()


@router.get(
    "/aliases/{drug_name}",
    response_model=DrugAliasSearchResult,
    response_model_exclude_none=True,
)
async def search_drug_aliases_by_value(
    drug_name: Annotated[
        str,
        Path(
            description="The drug name to list aliases for",
            max_length=256,
            min_length=1,
            example="Adderall",
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
    results = drug_aliases_adapter.find_drug_aliases_by_drug_name(
        drug_name=drug_name, fuzzy_match=fuzzy_match
    )
    if results is None:
        return DrugAliasSearchResult(drug=drug_name, count=0, results=[])
    return result_mapper.map(drug_name, results)


@router.get(
    "/aliases/id/{drug_id}",
    response_model=DrugAliasSearchResult,
    response_model_exclude_none=True,
)
async def search_drug_aliases_by_id(
    drug_id: Annotated[
        str,
        Path(
            description="The drug bank id to list aliases for",
            max_length=256,
            min_length=1,
            example="DB00182",
        ),
        AfterValidator(validate_value),
    ],
):
    drug_id = normalize_drug_id(drug_id)
    results = drug_aliases_adapter.find_drug_aliases_by_drug_id(drug_id=drug_id)
    if results is None:
        return DrugAliasSearchResult(drug=drug_id, count=0, results=[])
    return result_mapper.map(drug_id, results)
