import logging
from typing import Any
import httpx

from const import USER_AGENT

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECS = 30

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


async def make_eugene_request(
    token: str, url: str, params: dict[str, str] | None = None
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Make a request to the Eugene API with proper error handling."""

    _ensure_token_or_raise(token)
    headers = DEFAULT_HEADERS
    headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(verify=False) as client:
        try:
            logger.info(f"url: {url} params: {params} headers: {headers}")
            response = await client.get(
                url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT_SECS
            )
            response.raise_for_status()
            logger.info(f"{response}")
            return response.json()
        except Exception:
            return None


async def post_eugene_request(
    token: str, url: str, body: dict[str, Any]
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Make a request to the Eugene API with proper error handling."""

    _ensure_token_or_raise(token)
    headers = {
        "Content-Type": "application/json",
        **DEFAULT_HEADERS,
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(verify=False) as client:
        try:
            logger.info(f"url: {url} body: {body} headers: {headers}")
            response = await client.post(
                url, headers=headers, timeout=DEFAULT_TIMEOUT_SECS, json=body
            )
            response.raise_for_status()
            logger.info(f"{response}")
            return response.json()
        except Exception:
            return None


def _ensure_token_or_raise(token: str):
    if not token or len(token) == 0:
        raise ValueError(f"Missing jwt token to pass in the request header!")
