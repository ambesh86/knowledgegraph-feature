import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneFactTools:
    """
    This class hold tools for euGENE to be registered w/ MCP
    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def fetch_facts(node_id: str) -> dict[str, Any] | str:
        """Fetch facts about a given node

        For drugs the facts include; indications, contraindication and off label uses
        For diseases the facts include; genes, proteins, drugs

        Args:
            node_id: a drug, disease, gene protein, anatomy, molecular function node id. Use the lookup_node_id method to translate node value to node id
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        # has relationship is too generic
        ignore_fact = "has relationship"
        facts = []
        page_number = 1
        page_size = 50
        MAX_PAGES = 50
        has_more_pages = True
        while has_more_pages:
            url = f"{EUGENE_API_BASE}/graph/facts/start/{node_id}?page={page_number}&page_size={page_size}"
            data = await make_eugene_request(token=token, url=url)
            if (
                not data
                or "count" not in data
                or data["count"] < 1
                or page_number > MAX_PAGES
            ):
                break

            fact_batch = data["results"]
            logger.debug(f"{fact_batch}")
            filtered_facts = [fact for fact in fact_batch if fact.find(ignore_fact) < 0]
            facts.extend(filtered_facts)
            page_number += 1

        logging.info(f"found {len(facts)} facts")
        return "\n".join(facts)
