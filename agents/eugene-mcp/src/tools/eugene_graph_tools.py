import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request, post_eugene_request

logger = logging.getLogger(__name__)


class EugeneGraphTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def fetch_node_relationships(
        node_id: str, n_hop: int = 2
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """Fetch relationships for a node

        e.g.
        For a drug the relationships include; indications contraindication and off label uses
        For disease the relationships include; genes, proteins, drugs

        The value may be case sensitive try upper and lower case values

        Args:
            node_id: a drug, disease, gene protein, anatomy, molecular function node id. Use the lookup_node_id method to translate node value to node id
            n_hop: how many neighbors to retrieve. Select 1 for a faster search but less results Select 2 for more results but slow query
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/graph/relationship/start/{node_id}"
        params = {"n_hop": str(n_hop)}
        data = await make_eugene_request(token=token, url=url, params=params)

        if not data:
            return f"Unable to fetch a relationships start at node {node_id}"

        return data

    @staticmethod
    async def fetch_paths(
        start_id: str, end_id: str, n_hop: int = 2
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """Fetch search paths from a node with start id to a node with end id

        Args:
            start_id: node id
            end_id: node id
            n_hop: max hops to find a path from start to end node
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/graph/path/start/{start_id}/end/{end_id}"
        params = {"n_hop": str(n_hop)}
        data = await make_eugene_request(token=token, url=url, params=params)

        if not data:
            return f"Unable to fetch a path from {start_id} to {end_id}"

        return data

    @staticmethod
    async def has_reachable_path(
        start_id: str, end_id: str, n_hop: int = 2
    ) -> list[dict[str, Any]] | dict[str, Any] | str:
        """Determine if a path exists from a node with start id to a node with end id with in the contained number of hops

        Args:
            start_id: node id
            end_id: node id
            n_hop: max hops to find a path from start to end node
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/graph/reachability/start/{start_id}/end/{end_id}"
        params = {"n_hop": str(n_hop)}
        data = await make_eugene_request(token=token, url=url, params=params)

        if not data:
            return f"Unable to fetch a path from {start_id} to {end_id}"

        return data
