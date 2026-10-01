import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneDrugTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def fetch_drug_aliases(
        drug_name: str,
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """Fetch aliases used for a drug
        Drugs can be named as the generics, branch name or chemical synonymn

        For a drug the relationships include; indications contraindication and off label uses
        For disease the relationships include; genes, proteins, drugs

        The value may be case sensitive try upper and lower case values

        Args:
            drug_name: the generic name or drug bank name for a drug to find aliases e.g. 'Prednisone'
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/drugs/aliases/{drug_name}"
        data = await make_eugene_request(token=token, url=url)

        if not data or "count" not in data:
            return f"Unable to drug aliases for {drug_name}"

        return data
