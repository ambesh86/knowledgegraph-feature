import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from dotenv import find_dotenv, load_dotenv

from util.observability import (
    configure_json_logging,
    make_limiter,
    request_id_middleware,
)


logger = logging.getLogger(__name__)


def load_env() -> None:
    dotenv_path = find_dotenv(raise_error_if_not_found=False)
    if dotenv_path:
        load_dotenv(dotenv_path, verbose=True)
        logger.info(f".env file loaded: {dotenv_path}")
    else:
        logger.warning(".env file not found")


def add_routers(app: FastAPI) -> None:
    from router.auth import auth_router
    from router import root_router, health_router, release_notes_router
    from stats.router import database_stats_router
    from foundation.router import label_router as foundation_label_router
    from foundation.router import count_router as foundation_count_router
    from foundation.router import n_hop_router as foundation_n_hop_router
    from foundation.router import search_path_router as foundation_search_path_router
    from foundation.router import (
        digest_router,
        node_id_lookup_router as foundation_node_id_lookup_router,
    )
    from foundation.router import (
        node_details_router as foundational_node_details_router,
    )
    from foundation.router import facet_router as foundation_facet_router
    from foundation.router import similarity_router as foundation_similarity_router
    from foundation.router import drug_alias_search_router
    from foundation.router import patent_search_router
    from foundation.router import patent_count_router
    from foundation.router import pubmed_search_router
    from foundation.router import pubmed_count_router
    from foundation.router import facts_router as foundation_facts_router
    from organization.router import organization_search_router

    routers = [
        auth_router,
        root_router,
        health_router,
        release_notes_router,
        database_stats_router,
        foundation_count_router,
        foundation_label_router,
        foundation_node_id_lookup_router,
        foundational_node_details_router,
        foundation_n_hop_router,
        foundation_search_path_router,
        foundation_facet_router,
        foundation_similarity_router,
        drug_alias_search_router,
        patent_search_router,
        patent_count_router,
        pubmed_search_router,
        pubmed_count_router,
        foundation_facts_router,
        organization_search_router,
        digest_router,
    ]
    for router in routers:
        app.include_router(router.router)

    # Vector search is OPTIONAL: it depends on a Milvus/milvus-lite backend
    # (pymilvus). A bad/unset MILVUS_URI makes pymilvus raise at *import*, so
    # we import it here, guarded, and skip the routes rather than letting a
    # misconfigured vector store take down the entire core API.
    try:
        from foundation.router import (
            vector_search_router as foundation_vector_search_router,
        )

        app.include_router(foundation_vector_search_router.router)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logging.getLogger("eugene-ws").warning(
            "vector search disabled (Milvus unavailable): %s", exc
        )


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "EUGENE_CORS_ORIGINS",
        "http://localhost:18502,http://localhost:3000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


# --- boot sequence --------------------------------------------------------
configure_json_logging("eugene-ws")  # OBS-01
load_env()

app = FastAPI(title="Eugene Core API", version="2.0.0")

# SEC-03
limiter = make_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# CORS for Next.js UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.middleware("http")(request_id_middleware)

add_routers(app)
