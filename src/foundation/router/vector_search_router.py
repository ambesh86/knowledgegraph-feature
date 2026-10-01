import logging
from typing import Annotated

from fastapi import APIRouter, Query

from foundation.vector.fusion_search_service import fusion_search_service
from foundation.vector.vector_search_service import vector_search_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vector",
    tags=["vector"],
)

_service = vector_search_service()
_fusion = fusion_search_service()


@router.get("/health")
async def vector_health() -> dict:
    """Readiness of the vector store (collection present + populated)."""
    return _service.health()


@router.get("/search/{query}")
async def vector_search(
    query: str,
    top_k: Annotated[
        int,
        Query(description="Number of semantically nearest summaries to return", ge=1, le=20),
    ] = 5,
) -> dict:
    """Semantic search over Eugene's PubMed-style summary vector store (Milvus).

    Returns the nearest summaries with a similarity score and a source URL.
    """
    logger.info(f"vector search query='{query}' top_k={top_k}")
    return _service.search(query=query, top_k=top_k)


@router.get("/fusion/health")
async def fusion_health() -> dict:
    """Readiness of BOTH retrievers backing fused search (Neo4j + Milvus corpus)."""
    return _fusion.health()


@router.get("/fusion")
async def fusion_search_q(
    q: Annotated[str, Query(description="Search query", min_length=1)],
    top_k: Annotated[
        int,
        Query(description="Number of fused evidence items to return", ge=1, le=500),
    ] = 10,
    candidates: Annotated[
        int | None,
        Query(
            description=(
                "How deep each retriever goes before fusion (default 3x top_k, "
                "capped at 60). Raise it when the caller reranks the result: a "
                "reranker can only reorder the pool it is given."
            ),
            ge=1,
            le=500,
        ),
    ] = None,
    rerank: Annotated[
        bool,
        Query(
            description=(
                "Reorder the fused pool with a cross-encoder before returning. "
                "Costs ~one CPU pass over the candidates; buys precision that RRF "
                "cannot, because neither retriever ever reads the query and a "
                "passage together."
            )
        ),
    ] = False,
) -> dict:
    """Hybrid retrieval, query passed as a QUERY PARAMETER.

    This is the correct form and the one callers should use. The path-parameter
    variant below cannot carry arbitrary text: a query containing a slash — and
    "BAFF/APRIL" is a central term in this corpus — is decoded as a path
    separator and returns 404 even when percent-encoded. That silently broke
    fused search for a whole class of biomedical queries; the agent received
    "returned nothing" and correctly reported the graph had no such information,
    when in fact the same query without the slash returns 15 graph hits.
    """
    logger.info(
        f"fusion search (q) query='{q}' top_k={top_k} candidates={candidates} rerank={rerank}"
    )
    return _fusion.search(query=q, top_k=top_k, candidates=candidates, rerank=rerank)


@router.get("/fusion/{query}")
async def fusion_search(
    query: str,
    top_k: Annotated[
        int,
        Query(description="Number of fused evidence items to return", ge=1, le=50),
    ] = 10,
) -> dict:
    """Hybrid retrieval — Neo4j graph hits fused with Milvus vector hits.

    Both retrievers run concurrently and are merged with reciprocal rank fusion,
    so the caller gets ONE ranked, deduplicated evidence list with per-item
    provenance (`retrievers`, `ranks`, `rrf_score`) instead of two incomparable
    result sets. Items found by both retrievers are counted in `corroborated`.

    Degrades rather than fails: if the vector corpus is missing or Milvus is
    unavailable, this returns graph-only results.
    """
    logger.info(f"fusion search query='{query}' top_k={top_k}")
    return _fusion.search(query=query, top_k=top_k)
