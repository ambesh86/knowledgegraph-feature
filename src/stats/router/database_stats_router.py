import logging

from fastapi import APIRouter

from stats.conf.conf import neo4j_database_stats_adapter
from stats.model.system_stats import DatabaseStats


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
)

stats_adapter = neo4j_database_stats_adapter()


@router.get("", response_model=DatabaseStats, response_model_exclude_none=True)
async def fetch_database_stats():
    # todo: add daily caching
    return stats_adapter.query_system_stats()


@router.get("/top-proteins")
async def fetch_top_connected_proteins(limit: int = 20):
    """Gene/proteins ranked by overall connectivity (degree), with a per-type
    breakdown of connected diseases / proteins / drugs."""
    return {"results": stats_adapter.query_top_connected_proteins(limit)}


@router.get("/shared-gene-diseases")
async def fetch_shared_gene_diseases(min_shared: int = 3, limit: int = 25):
    """Disease pairs that share at least `min_shared` associated genes."""
    return {
        "min_shared": min_shared,
        "results": stats_adapter.query_shared_gene_diseases(min_shared, limit),
    }
