import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneIdentityTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def fetch_identity() -> list[dict[str, Any]] | dict[str, Any] | str:
        """Fetch current user identity as seen by the server

        Uses the authenticated JWT token from the request context
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/auth/whoami"
        data = await make_eugene_request(token=token, url=url)

        if not data:
            return f"Unable to fetch the current users identity"

        return data
