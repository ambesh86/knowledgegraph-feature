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
    from router import root_router, health_router
    from query.router import chat_query_agent_router

    routers = [auth_router, root_router, health_router, chat_query_agent_router]
    for router in routers:
        app.include_router(router.router)


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "EUGENE_CORS_ORIGINS",
        "http://localhost:18502,http://localhost:3000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


# --- boot sequence --------------------------------------------------------
configure_json_logging("eugene-agent-ws")  # OBS-01
logging.getLogger("strands").setLevel(logging.INFO)
load_env()

app = FastAPI(
    root_path="/agent/api",
    title="Eugene Agent WS",
    version="2.0.0",
)

# SEC-03: rate limiting
limiter = make_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# Phase 1j: CORS for Next.js UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# OBS-01: request-id + access log
app.middleware("http")(request_id_middleware)

add_routers(app)
