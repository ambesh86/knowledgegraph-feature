import logging
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import AfterValidator

from foundation.conf.conf import (
    neo4j_patent_query_adapter,
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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/count/patents",
    tags=["patents"],
)

patent_query_adapter = neo4j_patent_query_adapter()


@router.get("/drugs", response_model_exclude_none=True)
async def count_related_patents_by_drug_id(
    drug_id: Annotated[
        str,
        Query(
            example="DB00993",
            description="The canonical drug id to begin search for related patents. See drug synonym endpoint to retrieve a canonical drug id.",
            max_length=64,
            min_length=1,
        ),
        AfterValidator(validate_value),
    ],
):
    drug_id = normalize_drug_id(drug_id)
    count = patent_query_adapter.count_related_patents_by_drug(drug_id)
    return {"drug": drug_id, "patent_count": count}


@router.get("/clinicaltrials", response_model_exclude_none=True)
async def count_related_patents_by_clinicaltrial_id(
    nct_id: Annotated[
        str,
        Query(
            example="NCT05648006",
            description="The clinical trial id to begin search for related patents.",
            max_length=24,
            min_length=1,
        ),
        AfterValidator(validate_clinical_trail_id),
    ],
):
    nct_id = normalize_clinical_trial_id(nct_id)
    count = patent_query_adapter.count_related_patents_by_clinicaltrail(nct_id)
    return {"nct_id": nct_id, "patent_count": count}


@router.get("/geneproteins", response_model_exclude_none=True)
async def count_related_patents_by_geneprotein_id(
    gene_protein: Annotated[
        str,
        Query(
            example="ABL1",
            description="The gene to begin search for related patents.",
            max_length=24,
            min_length=1,
        ),
        AfterValidator(validate_gene_protein),
    ],
):
    gene_protein = normalize_gene_protein(gene_protein)
    count = patent_query_adapter.count_related_patents_by_gene(gene_protein)
    return {"gene_protein": gene_protein, "patent_count": count}
