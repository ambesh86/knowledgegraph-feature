import logging

logger = logging.getLogger(__name__)


def extract_token() -> str | None:
    from fastmcp.server.dependencies import get_http_request

    request = get_http_request()
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]

    if token:
        logger.info(f"found token {token[0: 8]}...")
    else:
        logger.warning("no token found in request Authorization header: {auth_header}")
    return token
