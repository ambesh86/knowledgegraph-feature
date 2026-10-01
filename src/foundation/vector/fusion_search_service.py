"""Hybrid retrieval: fuse Neo4j graph hits with Milvus vector hits.

The two stores answer different questions and each is weak where the other is
strong:

  * Neo4j is exact and structural — it knows that Rituximab IS a drug node and
    which trials it links to, but a lexical name match misses "anti-CD20 therapy".
  * Milvus is semantic and fuzzy — it retrieves conceptually related documents
    regardless of wording, but has no notion of graph structure or truth.

Running them separately and concatenating produces two incomparable score
scales. Instead we fuse with **Reciprocal Rank Fusion** (RRF):

    score(d) = Σ_retrievers  weight / (K + rank_in_that_retriever)

RRF operates on RANKS, not scores, which is exactly what we need: cosine
similarity from Milvus and a Neo4j lexical match have no common unit, but
"was ranked 3rd" is comparable across both. It is also robust to one retriever
returning garbage — a document only ranked by one retriever still surfaces, just
lower. K=60 is the value from the original Cormack et al. paper and is the de
facto default.

The fused evidence set is what gets handed to the LLM, so the model reasons over
ONE ranked, deduplicated, provenance-tagged list rather than two disjoint blobs.
"""
from __future__ import annotations

import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from foundation.vector import intent as intent_mod

logger = logging.getLogger(__name__)

# RRF constant — dampens the influence of the very top ranks so a single
# retriever cannot dominate the fused ordering.
RRF_K = 60
# Asymmetric source weights (M6). RRF was designed assuming sources are
# interchangeable; we invert that deliberately. The graph gets a 12% boost —
# enough that a structurally important passage isn't buried under generically
# similar prose, small enough that it can't override strong textual evidence.
WEIGHT_GRAPH = intent_mod.SOURCE_WEIGHT_GRAPH   # 1.12
WEIGHT_VECTOR = intent_mod.SOURCE_WEIGHT_VECTOR  # 1.00

_SEARCHABLE_LABELS = ("clinical_trial", "drug", "disease", "gene_protein", "paper_chunk")


class FusionSearchService:
    """Fuses graph and vector retrieval into a single ranked evidence list."""

    def __init__(self) -> None:
        self._driver = None
        self._index_ready = False
        self._df_cache: dict[str, int] = {}
        self._corpus_size: int | None = None

    def _get_driver(self):
        if self._driver is None:
            from foundation.conf.conf import _neo4j_driver

            self._driver = _neo4j_driver()
        return self._driver

    # -- retrievers --------------------------------------------------------
    def _ensure_fulltext_index(self) -> None:
        """Create the fusion full-text index once, if it isn't there yet.

        The pre-existing `entity_names` full-text index does NOT cover
        `clinical_trial`, so trials were invisible to lexical retrieval. Rather
        than drop and recreate a shared index other code may depend on, this adds
        a dedicated one.
        """
        if self._index_ready:
            return
        try:
            self._get_driver().execute_query(
                "CREATE FULLTEXT INDEX eugene_fusion_fulltext IF NOT EXISTS "
                "FOR (n:clinical_trial|drug|disease|gene_protein) ON EACH [n.node_name]"
            )
            # Passages are indexed on `text`, not `node_name` — the name is only
            # a 200-char preview, so indexing it would make most of a paper
            # unsearchable.
            self._get_driver().execute_query(
                "CREATE FULLTEXT INDEX paper_chunk_fulltext IF NOT EXISTS "
                "FOR (n:paper_chunk) ON EACH [n.text]"
            )
            self._index_ready = True
        except Exception as e:
            logger.warning(f"could not ensure fulltext index: {e}")

    # Terms this common in the corpus carry no retrieval signal here — every
    # nephrology paper says "kidney" — and including them only adds score to
    # whichever chunk repeats them most.
    _DF_STOP_RATIO = 0.30
    _DF_CACHE_MAX = 20000

    def _corpus_count(self) -> int:
        if self._corpus_size is None:
            try:
                recs, _, _ = self._get_driver().execute_query(
                    "MATCH (c:paper_chunk) RETURN count(c) AS n"
                )
                self._corpus_size = int(recs[0]["n"]) if recs else 0
            except Exception:
                self._corpus_size = 0
        return self._corpus_size or 0

    def _doc_freq(self, term: str) -> int:
        """How many passages contain `term`. Cached — df changes only on ingest."""
        if term in self._df_cache:
            return self._df_cache[term]
        try:
            recs, _, _ = self._get_driver().execute_query(
                "CALL db.index.fulltext.queryNodes('paper_chunk_fulltext', $t) "
                "YIELD node RETURN count(node) AS n",
                t=term,
            )
            df = int(recs[0]["n"]) if recs else 0
        except Exception:
            df = 0
        if len(self._df_cache) < self._DF_CACHE_MAX:
            self._df_cache[term] = df
        return df

    def _boosted_query(self, safe: str) -> str:
        """Rewrite a term list as Lucene terms boosted by inverse document frequency.

        BM25 already weights a term by its IDF, but it SUMS those weights across
        every matching term. A natural question carries the paper's whole title,
        so a passage that happens to repeat fifteen ordinary title words outscores
        the one passage containing the single identifier the user actually asked
        about. Measured on the table-cell set: asking for accession "D4A1J3" by
        itself ranks the right table 2nd; asking the same thing inside a full
        sentence ranks it 133rd, far below where any reranker would look.

        Boosting each term by its IDF a second time restores the rare term's
        dominance, which is the behaviour the question implies — the identifier is
        the query, the surrounding sentence is context.
        """
        n = self._corpus_count()
        if not n:
            return safe
        parts = []
        for term in dict.fromkeys(t for t in safe.split() if len(t) > 1):
            df = self._doc_freq(term)
            if df <= 0 or df / n > self._DF_STOP_RATIO:
                continue
            idf = math.log(1 + n / (1 + df))
            parts.append(f"{term}^{idf:.2f}")
        # Every term was either absent or a corpus stopword: fall back rather
        # than search for nothing.
        return " ".join(parts) if parts else safe

    def _graph_search(self, query: str, top_k: int, boost: bool = False) -> list[dict[str, Any]]:
        """Lucene full-text retrieval over entity names, ranked by BM25-ish score.

        A plain `CONTAINS` match tests the WHOLE query string against each name,
        so a natural-language query like "rituximab lymphoma trial" matched
        nothing. Full text tokenizes the query, which is what a lexical retriever
        has to do to be useful — and it returns a relevance score, giving us a
        meaningful rank to feed into RRF.
        """
        self._ensure_fulltext_index()
        # Escape Lucene special characters so user text can't break the parser
        # (or inject query syntax) — everything is treated as plain terms.
        safe = re.sub(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)', r" ", query).strip()
        if not safe:
            return []
        # Only when the caller is going to rerank.
        #
        # IDF boosting sharpens the LEXICAL ordering, and RRF then folds that
        # ordering in with the vector retriever's, which dilutes the sharpening
        # again — measured on this evaluation set, boosting without reranking
        # moved fused retrieval@10 from 38.5% to 28.3%, because it also displaces
        # hits that RRF happened to rank well. Paired with a reranker that reads
        # the candidates properly it is worth 4.3% -> 100%.
        #
        # So it is not a free improvement to the default path, and it is not
        # turned on there.
        if boost:
            safe = self._boosted_query(safe)
        # Two full-text indexes, unioned: entities are indexed on `node_name`,
        # paper passages on `text`. Neo4j cannot span both from one index, so we
        # query both and let RRF rank across them.
        cypher = (
            "CALL { "
            "  CALL db.index.fulltext.queryNodes('eugene_fusion_fulltext', $q) "
            "  YIELD node AS n, score RETURN n, score "
            "  UNION "
            "  CALL db.index.fulltext.queryNodes('paper_chunk_fulltext', $q) "
            "  YIELD node AS n, score RETURN n, score "
            "} "
            "WITH n, score WHERE any(l IN labels(n) WHERE l IN $labels) "
            "RETURN n.node_id AS node_id, n.node_index AS node_index, "
            "       n.node_name AS name, labels(n)[0] AS label, "
            "       n.url AS url, n.status AS status, n.phase AS phase, "
            "       n.sponsor AS sponsor, n.nct_id AS nct_id, "
            "       n.doc_id AS doc_id, n.chunk_id AS chunk_id, n.page AS page, "
            "       n.text AS text, n.centrality_composite AS centrality_composite, "
            "       round(score, 4) AS lexical_score "
            "ORDER BY score DESC LIMIT $limit"
        )
        try:
            records, _, _ = self._get_driver().execute_query(
                cypher, q=safe, labels=list(_SEARCHABLE_LABELS), limit=top_k
            )
        except Exception as e:  # degrade, never fail the whole request
            logger.warning(f"graph retriever failed: {e}")
            return []
        out = []
        for r in records:
            d = {k: v for k, v in dict(r).items() if v is not None}
            d["retriever"] = "graph"
            out.append(d)
        return out

    def _vector_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Semantic nearest neighbours from the Milvus corpus collection."""
        try:
            from foundation.vector.corpus_ingest_service import CORPUS_COLLECTION
            from foundation.vector.vector_search_service import vector_search_service

            svc = vector_search_service()
            client = svc._get_client()
            if not client.has_collection(CORPUS_COLLECTION):
                logger.warning(
                    f"'{CORPUS_COLLECTION}' missing — run corpus_ingest_service; "
                    "fusion degrades to graph-only"
                )
                return []
            qvec = svc._embed([query])[0]
            res = client.search(
                collection_name=CORPUS_COLLECTION,
                data=[qvec],
                limit=top_k,
                output_fields=[
                    "doc_id", "node_index", "label", "name", "text", "url",
                    "ade_doc_id", "page", "paper_title",
                ],
            )
        except Exception as e:
            logger.warning(f"vector retriever failed: {e}")
            return []
        out = []
        for h in (res[0] if res else []):
            ent = h.get("entity", {}) or {}
            hit = {
                "node_id": ent.get("doc_id"),
                "node_index": ent.get("node_index"),
                "name": ent.get("name"),
                "label": ent.get("label"),
                "text": ent.get("text"),
                "url": ent.get("url"),
                "similarity": round(float(h.get("distance", 0.0)), 4),
                "retriever": "vector",
            }
            # Paper passages carry the pointers the evidence renderer needs.
            if ent.get("ade_doc_id"):
                hit["doc_id"] = ent["ade_doc_id"]
                hit["chunk_id"] = ent.get("node_index")
                hit["page"] = ent.get("page")
                hit["paper_title"] = ent.get("paper_title")
            out.append(hit)
        return out

    # -- fusion ------------------------------------------------------------
    @staticmethod
    def _key(hit: dict) -> str:
        """Identity for dedup across retrievers.

        node_index is the graph's primary key and is carried into the vector
        payload at ingest, so the same entity found by both retrievers collapses
        to one fused row (and gets both contributions added to its score).
        """
        return str(hit.get("node_index") or hit.get("node_id") or hit.get("name") or "")

    def fuse(
        self, graph_hits: list[dict], vector_hits: list[dict], top_k: int
    ) -> list[dict]:
        fused: dict[str, dict] = {}
        for hits, weight in ((graph_hits, WEIGHT_GRAPH), (vector_hits, WEIGHT_VECTOR)):
            for rank, hit in enumerate(hits, start=1):
                key = self._key(hit)
                if not key:
                    continue
                contribution = weight / (RRF_K + rank)
                if key in fused:
                    entry = fused[key]
                    entry["rrf_score"] += contribution
                    # Merge provenance and fill any fields the other retriever
                    # had but this one didn't.
                    if hit["retriever"] not in entry["retrievers"]:
                        entry["retrievers"].append(hit["retriever"])
                    entry["ranks"][hit["retriever"]] = rank
                    for k, v in hit.items():
                        if k not in ("retriever",) and v and not entry.get(k):
                            entry[k] = v
                else:
                    entry = {k: v for k, v in hit.items() if k != "retriever"}
                    entry["rrf_score"] = contribution
                    entry["retrievers"] = [hit["retriever"]]
                    entry["ranks"] = {hit["retriever"]: rank}
                    fused[key] = entry

        ordered = sorted(fused.values(), key=lambda e: e["rrf_score"], reverse=True)
        for e in ordered:
            e["rrf_score"] = round(e["rrf_score"], 6)
        return ordered[:top_k]

    # -- public ------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 10,
        candidates: int | None = None,
        rerank: bool = False,
    ) -> dict:
        """Run both retrievers concurrently and return the fused evidence set.

        `candidates` sets how deep each retriever goes before fusion. The default
        (3x top_k, capped at 60) is right for a caller that renders the fused list
        directly. It is wrong for a caller that reranks: a cross-encoder can only
        reorder what it is handed, so the candidate pool — not the reranker — is
        what bounds recall, and the 60-deep default silently caps it.

        `top_k` therefore allows a much larger ceiling than a UI would ever ask
        for, because a reranking client legitimately wants the pool rather than a
        page of it.
        """
        top_k = max(1, min(int(top_k), 500))
        fetch = min(int(candidates), 500) if candidates else min(top_k * 3, 60)
        fetch = max(fetch, top_k)

        with ThreadPoolExecutor(max_workers=2) as pool:
            g_future = pool.submit(self._graph_search, query, fetch, rerank)
            v_future = pool.submit(self._vector_search, query, fetch)
            graph_hits = g_future.result()
            vector_hits = v_future.result()

        # M6 — pre-rank the graph list by intent BEFORE fusing. RRF consumes rank
        # position, so re-ordering here is what actually changes the fused result;
        # doing it afterwards would have no effect at all.
        intent = intent_mod.classify(query)
        # Keep the retriever's OWN ordering before intent reshapes it. Intent
        # pre-ranking is right for the list a user reads and wrong for the
        # shortlist handed to a cross-encoder: its `text` term is unweighted
        # query-term overlap, so a long prose passage that shares ordinary words
        # outscores a compact table that shares only the one identifier being
        # asked about. That moved the table holding "D4A1J3" from lexical rank 2
        # to 89 — out of reach of a bounded reranker.
        for i, h in enumerate(graph_hits, start=1):
            h["lexical_rank"] = i
        for h in graph_hits:
            h["priority_score"] = intent_mod.priority_score(h, query, intent)
        graph_hits.sort(key=lambda h: h["priority_score"], reverse=True)

        # Reranking needs the POOL, not the page: fuse to the full candidate
        # depth, let the cross-encoder choose the top_k out of it, and only then
        # trim. Fusing to top_k first would hand the reranker the very ordering
        # it exists to correct.
        if rerank:
            from foundation.vector.rerank_service import rerank_service

            pooled = self.fuse(graph_hits, vector_hits, max(top_k, fetch))
            # Order the RERANKER's input by each item's best rank in ANY single
            # retriever, not by its fused score.
            #
            # RRF is the right way to produce a final list, and the wrong way to
            # produce a shortlist. It rewards agreement, so an item one retriever
            # is certain about and the other has never heard of gets averaged
            # down. That is exactly the shape of a rare-identifier lookup: the
            # table containing accession "D4A1J3" was 2nd lexically and 97th
            # after fusion, because two hundred semantically-similar passages
            # sat between them. A cross-encoder capped at N candidates would
            # never have seen it.
            #
            # Taking the best-rank-anywhere keeps each retriever's confident head
            # intact and lets the cross-encoder — which reads the query and the
            # passage together, unlike either retriever — settle the order.
            def _best_rank(e: dict) -> int:
                return min(
                    int(e.get("lexical_rank") or 10**6),
                    int(e.get("ranks", {}).get("vector") or 10**6),
                )

            pooled.sort(key=_best_rank)
            results = rerank_service().rerank(query, pooled, top_k)
            # False when the model could not load — the caller must be able to
            # tell "reranked" from "asked for reranking and silently didn't get it".
            reranked = any("rerank_score" in r for r in results)
        else:
            results = self.fuse(graph_hits, vector_hits, top_k)
            reranked = False

        # M7 — the backend issues the citation label. The model may reference
        # "[Evidence 3]" but has no mechanism for emitting a URL, so it cannot
        # emit a false one. Prevention rather than after-the-fact detection.
        for i, r in enumerate(results, start=1):
            r["evidence_label"] = f"Evidence {i}"

        both = sum(1 for r in results if len(r["retrievers"]) > 1)
        logger.info(
            f"fusion query={query!r} graph={len(graph_hits)} vector={len(vector_hits)} "
            f"fused={len(results)} corroborated={both}"
        )
        return {
            "query": query,
            "count": len(results),
            "results": results,
            "retrievers": {
                "graph": {"hits": len(graph_hits), "store": "Neo4j"},
                "vector": {"hits": len(vector_hits), "store": "Milvus"},
            },
            # Documents found by BOTH retrievers are the strongest evidence —
            # independent structural and semantic agreement.
            "corroborated": both,
            # A passage result carries doc_id + chunk_id, which is the exact pair
            # the evidence renderer needs — so any claim built on one can be
            # traced back to the highlighted region of the original PDF.
            "evidence_available": sum(1 for r in results if r.get("doc_id") and r.get("chunk_id")),
            "intent": {
                "name": intent.name,
                "reason": intent.reason,
                "weights": intent.weights,
            },
            "fusion": (
                f"intent-conditioned pre-rank + weighted RRF "
                f"(K={RRF_K}, vector={WEIGHT_VECTOR}, graph={WEIGHT_GRAPH})"
                + (" + cross-encoder rerank" if reranked else "")
            ),
            "source": "Eugene fused retrieval (Neo4j + Milvus)",
        }

    def health(self) -> dict:
        from foundation.vector.corpus_ingest_service import CORPUS_COLLECTION
        from foundation.vector.vector_search_service import vector_search_service

        out: dict[str, Any] = {"graph": False, "vector": False, "corpus_rows": 0}
        try:
            recs, _, _ = self._get_driver().execute_query("RETURN 1 AS ok")
            out["graph"] = bool(recs)
        except Exception as e:
            out["graph_error"] = str(e)[:200]
        try:
            client = vector_search_service()._get_client()
            if client.has_collection(CORPUS_COLLECTION):
                out["corpus_rows"] = int(
                    client.get_collection_stats(CORPUS_COLLECTION).get("row_count", 0)
                )
                out["vector"] = out["corpus_rows"] > 0
        except Exception as e:
            out["vector_error"] = str(e)[:200]
        out["ready"] = bool(out["graph"] and out["vector"])
        return out


_instance: FusionSearchService | None = None


def fusion_search_service() -> FusionSearchService:
    global _instance
    if _instance is None:
        _instance = FusionSearchService()
    return _instance
