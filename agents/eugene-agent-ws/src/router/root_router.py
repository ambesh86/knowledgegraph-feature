import logging

from fastapi import APIRouter


router = APIRouter(
    prefix="",
    tags=["root"],
)

logger = logging.getLogger(__name__)


@router.get("/")
async def app_root():
    return {
        "message": "Welcome to the EUGENE agentic chat webservice. Visit the Swagger docs at /docs"
    }
