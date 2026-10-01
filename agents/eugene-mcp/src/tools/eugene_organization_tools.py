import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneOrganizationTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def find_organization_names(name_pattern: str) -> list[dict[str, Any]] | str:
        """Fetch organization names

        Args:
            name_pattern: a name pattern, can accept * and ? regex characters, but no other regex chars
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        base_url = f"{EUGENE_API_BASE}/organizations/{name_pattern}"
        names = await EugeneOrganizationTools._collect_pages(
            token=token, base_url=base_url
        )

        num_found = len(names)
        logging.info(f"found {num_found} names")
        if num_found < 1:
            return f"No results for found!"

        return names

    @staticmethod
    async def find_organization_assets(
        organization_id: str,
    ) -> list[dict[str, Any]] | str:
        """Fetch organization assets. Assets include clinical trials, drug and disease an organization has known intellectual property

        Args:
            organization_id: an organization id. e.g. C010405
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        base_url = f"{EUGENE_API_BASE}/organizations/assets/{organization_id}"
        names = await EugeneOrganizationTools._collect_pages(
            token=token, base_url=base_url
        )

        num_found = len(names)
        logging.info(f"found {len(names)} assets for org: {organization_id}")
        if num_found < 1:
            return f"No results for found!"

        return names

    @staticmethod
    async def _collect_pages(token: str, base_url: str) -> list[dict[str, Any]]:
        pages = []
        page_number = 1
        page_size = 50
        # todo: maybe allow the agent to request a human feedback to continue fetching data
        MAX_PAGES = 10
        has_more_pages = True
        while has_more_pages and page_number < MAX_PAGES:
            current_url_page = f"{base_url}"
            params = {"page": str(page_number), "page_size": str(page_size)}
            data = await make_eugene_request(
                token=token, url=current_url_page, params=params
            )
            if not data or "count" not in data or data["count"] < 1:
                has_more_pages = False
                break

            current_batch = data["results"]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{current_batch}")
            pages.extend(current_batch)
            page_number += 1

        logger.info(f"found {page_number} pages of results")
        return pages
