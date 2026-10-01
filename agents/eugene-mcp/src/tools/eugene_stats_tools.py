import logging
from typing import Any

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneStatsTools:
    """Tools exposing overall Eugene knowledge-graph size and composition."""

    @staticmethod
    async def fetch_graph_stats() -> dict[str, Any] | str:
        """Return the overall SIZE and COMPOSITION of the Eugene knowledge graph.

        Use this for questions about how big the graph is or how much data it
        holds — e.g. "how many nodes and edges are in Eugene", "how big is the
        knowledge graph", "how many drugs / diseases / gene-proteins does the
        graph contain", "what's the total count of data in Eugene".

        Returns a dict including:
            - node_count: total number of nodes (entities)
            - relationship_count: total number of relationships (edges)
            - drug_count, disease_count, gene_protein_count, clinical_trial_count,
              uspto_count, pubmed_count, organization_count, therapeutic_area_count
              and other per-type counts.
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/stats"
        data = await make_eugene_request(token=token, url=url)
        logger.info(f"graph stats: {data}")

        if not data:
            return "Unable to fetch Eugene knowledge-graph statistics."

        # /stats returns a single stats object; normalize if wrapped in a list.
        if isinstance(data, list):
            data = data[0] if data else None
        if not isinstance(data, dict):
            return "Unable to fetch Eugene knowledge-graph statistics."

        return data

    @staticmethod
    async def fetch_top_connected_proteins(limit: int = 20) -> dict[str, Any] | str:
        """Return the MOST-CONNECTED gene/proteins across the WHOLE graph, ranked
        by total degree, with a breakdown of how many diseases, other proteins,
        and drugs each connects to.

        Use this for graph-wide "which are the most connected / central / hub"
        questions — e.g. "which proteins are connected to the most genes,
        diseases, and drugs overall", "what are the biggest hubs in the graph",
        "top proteins by connectivity". This is a global aggregation, not scoped
        to a single seed entity.

        Args:
            limit: how many proteins to return (1-100, default 20).
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/stats/top-proteins"
        data = await make_eugene_request(
            token=token, url=url, params={"limit": str(limit)}
        )
        if not data:
            return "Unable to compute the most-connected proteins."
        return data if isinstance(data, dict) else {"results": data}

    @staticmethod
    async def fetch_shared_gene_diseases(
        min_shared: int = 3, limit: int = 25
    ) -> dict[str, Any] | str:
        """Return pairs of DISEASES that SHARE at least `min_shared` associated
        genes (a graph-wide common-neighbour aggregation over disease↔gene links).

        Use this for questions like "are there diseases that share three or more
        of the same associated genes", "which diseases have the most genes in
        common", "find disease pairs with overlapping gene associations". This is
        a global aggregation across the whole disease set, not scoped to one seed.

        Args:
            min_shared: minimum number of shared genes for a pair (default 3).
            limit: how many pairs to return (1-100, default 25).
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/stats/shared-gene-diseases"
        data = await make_eugene_request(
            token=token,
            url=url,
            params={"min_shared": str(min_shared), "limit": str(limit)},
        )
        if not data:
            return "Unable to compute diseases with shared genes."
        return data if isinstance(data, dict) else {"results": data}
