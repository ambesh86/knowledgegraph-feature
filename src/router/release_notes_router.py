import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["releases"],
)


@router.get("/releases")
async def get_releases():
    releases = {
        "v1": ["initial release of foundational graph endpoints"],
        "v1.1 - 8/1/25": [
            "updated foundational graph endpoints to include ids",
            "added endpoints to power ui",
            "added drug aliases endpoint",
            "added company aliases endpoint",
        ],
        "v1.2 - 8/28/25": [
            "added pagination and count endpoint",
            "added more node type labels to endpoints",
            "removed one hop endpoint in favor of n hop endpoint",
            "changed company aliases to organization aliases",
        ],
        "v2.0 - 9/4/25": [
            "loaded eugene 2.0 data. Including patents, clinical trails, and organizations",
            "added search and count patents by drug id endpoints",
        ],
        "v2.1 - 9/11/25": [
            "added endpoints for patent searches by clincal trial or gene protein target",
            "updated drug synonym endpoint to return ids and to accept a drug id parameter",
        ],
        "v2.2 - 9/16/25": [
            "added a database stats endpoint",
            "added endpoints for pubmed searches by drug, clincal trial or gene protein target",
            "updated release notes",
        ],
    }
    return releases
