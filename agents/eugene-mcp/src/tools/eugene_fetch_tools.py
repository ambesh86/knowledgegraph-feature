import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request, post_eugene_request

logger = logging.getLogger(__name__)


class EugeneFetchTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def fetch_by_label(
        label: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any] | str:
        """List the known names of the given label
        e.g. drug, disease

        Args:
            label: the type to fetch, either 'drug' or 'disease'
            page: page number for pagination
            page_size: number of results per page
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/labels/{label}"
        params = {"page": str(page), "page_size": str(page_size)}
        data = await make_eugene_request(token=token, url=url, params=params)
        logger.info(f"{data}")

        if not data or "count" not in data:
            return f"Unable to fetch {label} values"

        if data["count"] < 1:
            return f"No {label} values found"

        return data

    @staticmethod
    async def fetch_similar(label: str, values: list[str]) -> dict[str, Any] | str:
        """List the names of nodes similar to the given label type and value

        Args:
            label: the type to fetch, either 'drug' or 'disease'
            values: a list drugs or disease in which match similar values based on their common relationships, e.g. 'Prednisone'
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/similarity/{label}"
        data = await post_eugene_request(token=token, url=url, body={"values": values})

        if not data or "count" not in data:
            return f"Unable to fetch similar {label} matches"

        if data["count"] < 1:
            return f"No similar {label} matches found"

        return data
