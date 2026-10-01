import logging
from typing import Any
from urllib.parse import quote

from conf.conf import EUGENE_API_BASE
from const import CONTEXT_TOKEN_ERROR_MSG
from util.context import extract_token
from util.request import make_eugene_request

logger = logging.getLogger(__name__)


class EugeneVectorTools:
    """Semantic (vector) search tools over Eugene's internal summary store.

    See decorating methods
    https://gofastmcp.com/patterns/decorating-methods
    """

    @staticmethod
    async def search_summaries(
        query: str, top_k: int = 5
    ) -> dict[str, Any] | list[dict[str, Any]] | str:
        """Semantic search over Eugene's internal PubMed-style summary vector store.

        Use this for conceptual / "find summaries about X" questions where an exact
        graph lookup is not enough — it returns the most semantically similar
        curated summaries (with a source URL and similarity score) from Eugene's
        own Milvus vector store. This is INTERNAL Eugene data, not the live PubMed
        website.

        Args:
            query: a natural-language topic, e.g. "emicizumab prophylaxis in hemophilia A"
            top_k: number of nearest summaries to return (1-20)
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        url = f"{EUGENE_API_BASE}/vector/search/{quote(query, safe='')}"
        data = await make_eugene_request(
            token=token, url=url, params={"top_k": str(top_k)}
        )
        if not data:
            return f"No summaries found in the Eugene vector store for: {query}"
        return data

    @staticmethod
    async def search_fused(
        query: str, top_k: int = 10
    ) -> dict[str, Any] | list[dict[str, Any]] | str:
        """HYBRID search — the Eugene graph AND the vector store, fused into one ranked list.

        THIS IS THE BEST FIRST TOOL for almost any question about entities Eugene
        knows (drugs, diseases, genes/proteins, clinical trials). It runs two
        retrievers concurrently and merges them with reciprocal rank fusion:

          * Neo4j full-text — exact/lexical entity matching, structurally true.
          * Milvus vectors  — semantic similarity, finds conceptually related
            items even when the user's wording differs from the canonical name.

        Prefer this over calling `lookup_node_by_value` or `search_summaries`
        alone: neither retriever sees what the other sees, and this returns one
        deduplicated, provenance-tagged evidence list instead of two.

        Each result carries:
          - `name`, `label`, `node_id`, `node_index` — use `node_index`/`node_id`
            with `fetch_node_relationships` / `fetch_facts` to go deeper.
          - `retrievers` — which retriever(s) found it. Items listing BOTH
            ("graph" and "vector") are the strongest evidence: independent
            lexical and semantic agreement. Lead your answer with those.
          - `rrf_score` — the fused rank score (higher is better).
          - for trials: `nct_id`, `status`, `phase`, `sponsor`, `url`.
          - for `paper_chunk` results (passages extracted from research PDFs):
            `doc_id`, `chunk_id`, `page`, `paper_title` and the passage `text`.
            These are VERIFIABLE evidence — the exact region of the original PDF
            can be rendered on demand. When you use one, quote or paraphrase the
            passage and name the paper and page, so the user can check it.

        The response's `evidence_available` count tells you how many results are
        passages backed by a source PDF.

        The response's `corroborated` count tells you how many items both
        retrievers agreed on.

        Args:
            query: natural-language topic or entity, e.g. "rituximab lymphoma trial"
            top_k: number of fused evidence items to return (1-50)
        """
        token = extract_token()
        if not token:
            return CONTEXT_TOKEN_ERROR_MSG

        # Query goes in a QUERY PARAMETER, not the path. A path parameter cannot
        # carry arbitrary text: "BAFF/APRIL" percent-encodes to %2F, which is
        # decoded back to a path separator and 404s. That failure was silent —
        # the tool reported "returned nothing" and the agent faithfully told the
        # user the graph had no such information.
        url = f"{EUGENE_API_BASE}/vector/fusion"
        data = await make_eugene_request(
            token=token, url=url, params={"q": query, "top_k": str(top_k)}
        )
        if not data:
            return f"Fused search returned nothing for: {query}"
        return data
