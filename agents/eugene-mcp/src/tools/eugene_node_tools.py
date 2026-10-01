import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request, post_eugene_request

logger = logging.getLogger(__name__)


class EugeneNodeTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def lookup_node_by_value(
        value: str, fuzzy_match: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """find node by value

        Lookup a node id for any type of node, including; drug, disease, gene protein, exposure, pathway, anatomy, molecular function

        The value may be case sensitive try upper and lower case values

        Args:
            value: for example a drug or disease e.g. 'Prednisone' for drug, 'lupus' for disease
            fuzzy_match: for a fuzzy case insensitve match
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/node/find/{value}"
        params = {"fuzzy_match": str(fuzzy_match)}
        data = await make_eugene_request(token=token, url=url, params=params)

        if not data:
            return f"Unable to fetch node with {value}"

        return data

    @staticmethod
    async def fetch_node_details(
        ids: list[str],
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """find node by ids

        Lookup node details by id. Lookup details for any type of node, including; drug, disease, gene protein, exposure, pathway, anatomy, molecular function

        Use the lookup_node_id method to translate from node value to node id

        Args:
            ids: list of ids
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/node/details"
        data = await post_eugene_request(token=token, url=url, body={"ids": ids})

        if not data:
            return f"Unable to fetch node details with {ids}"

        return data
