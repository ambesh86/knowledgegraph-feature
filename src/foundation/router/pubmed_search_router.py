import logging
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_pubmed_query_adapter,
    pubmed_search_result_mapper,
)
from foundation.router.validate_util import (
    validate_clinical_trail_id,
    validate_gene_protein,
    validate_value,
)
from foundation.model.case_helper import (
    normalize_clinical_trial_id,
    normalize_drug_id,
    normalize_gene_protein,
)
from foundation.model.pubmed.pubmed_search_result import PubmedSearchResult
from foundation.model.pubmed.pubmed_and_gene_search_result import (
    PubmedAndGeneSearchResult,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pmids",
    tags=["pubmed"],
)

query_adapter = neo4j_pubmed_query_adapter()
search_result_mapper = pubmed_search_result_mapper()


@router.get(
    "/drugs",
    response_model=PubmedSearchResult,
    response_model_exclude_none=True,
)
async def find_related_pubmed_docs_by_drug_id(
    drug_id: Annotated[
        str,
        Query(
            example="DB00683",
            description="The canonical drug id to begin search for related patents. See drug synonym endpoint to retrieve a canonical drug id",
            max_length=64,
            min_length=1,
        ),
        AfterValidator(validate_value),
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
            example=50,
            gt=0,
            le=100,
        ),
    ],
):
    drug_id = normalize_drug_id(drug_id)
    dataframe = query_adapter.find_related_pubmed_by_drug(drug_id, page, page_size)
    return search_result_mapper.map_drug_response(
        search_id=drug_id, dataframe=dataframe
    )


@router.get(
    "/clinicaltrials",
    response_model=PubmedSearchResult,
    response_model_exclude_none=True,
)
async def find_related_pubmed_docs_by_clinicaltrial_id(
    nct_id: Annotated[
        str,
        Query(
            example="NCT00000122",
            description="The clinical trial id to begin search for related patents.",
            max_length=24,
            min_length=1,
        ),
        AfterValidator(validate_clinical_trail_id),
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
            example=50,
            gt=0,
            le=100,
        ),
    ],
):
    nct_id = normalize_clinical_trial_id(nct_id)
    dataframe = query_adapter.find_related_pubmed_by_clinicaltrail(
        nct_id, page, page_size
    )
    return search_result_mapper.map_clinicaltrail_response(
        search_id=nct_id, dataframe=dataframe
    )


@router.get(
    "/geneproteins",
    response_model=PubmedAndGeneSearchResult,
    response_model_exclude_none=True,
)
async def find_related_pubmed_docs_by_geneprotein_id(
    gene_protein: Annotated[
        str,
        Query(
            example="PDE3A",
            description="The gene to begin search for related patents.",
            max_length=24,
            min_length=1,
        ),
        AfterValidator(validate_gene_protein),
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
            example=50,
            gt=0,
            le=100,
        ),
    ],
):
    gene_protein = normalize_gene_protein(gene_protein)
    dataframe = query_adapter.find_related_pubmed_by_gene(gene_protein, page, page_size)
    return search_result_mapper.map_gene_response(
        gene_protein=gene_protein, dataframe=dataframe
    )
