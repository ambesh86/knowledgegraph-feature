"""Cross-encoder reranking of the fused evidence list.

Fusion maximises RECALL — it asks two stores with different strengths and merges
what they return. Nothing in it ever reads the question and a passage together:
Milvus compares two independently-embedded vectors, and Neo4j's full-text index
scores term overlap. Both are bi-encoders in effect, and both are blind to
whether a passage actually answers the question rather than merely resembling it.

A cross-encoder does read them together, which is what buys the precision. On the
table-cell evaluation set the correct passage sat in the fused pool for every
question, at a mean rank near 100 — present, but far below the top-10 window an
answer is actually built from. Recall was never the problem there; ordering was.

So this runs AFTER fusion, not instead of it. Fusion decides what is in the pool;
this decides what reaches the model.

Degrades rather than fails. If the model cannot load — no weights cached, no
network on a cold start — reranking is skipped and the RRF order stands. A
missing optional model must never take retrieval offline.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ms-marco MiniLM is the small end of the cross-encoder range: ~80 MB, trained on
# exactly this task (rank passages for a query), and fast enough to score a few
# hundred candidates on CPU. The container has no GPU, so a larger reranker would
# cost more latency than the accuracy is worth.
#
# NOT an MS MARCO cross-encoder, which is the obvious default and is wrong here.
# MS MARCO is web prose, and a pipe-delimited grid is out of its distribution: on
# the question "what p value is reported for D4A1J3", ms-marco-MiniLM-L-6-v2
# scored the table actually containing D4A1J3 at -7.49 and the paper's abstract —
# which contains no p values at all — at -1.46, so it promoted topical prose over
# the answer. Applied to the whole evaluation set it drove retrieval@10 DOWN, from
# 43.5% to 6.5%. bge-reranker scores the same pair 0.99 to 0.20.
#
# Most of the evidence worth reranking in this corpus is tabular, so a reranker
# that mishandles tables is worse than none.
_MODEL_NAME = os.environ.get("EUGENE_RERANK_MODEL", "BAAI/bge-reranker-base")
_ENABLED = os.environ.get("EUGENE_RERANK_ENABLED", "true").lower() != "false"
# Scoring is quadratic in nothing but linear in candidates, and the tail of a
# 500-deep pool is noise. This bounds worst-case latency.
# On CPU this model costs ~0.46s per candidate, so the cap IS the latency budget:
# 200 candidates measured 91s, which no interactive caller can absorb. 60 keeps a
# reranked query near ~28s and still covers the answer, because the candidate list
# is ordered by best-rank-in-any-retriever rather than by fused score — the gold
# passage sits near the head of it instead of around position 100.
_MAX_CANDIDATES = int(os.environ.get("EUGENE_RERANK_MAX_CANDIDATES", "60"))
# Deliberately generous. The obvious latency win is to truncate passages harder,
# but the token that decides relevance for a table lookup is the row label, and
# that can sit anywhere in the grid — cutting a table at 1000 characters halves
# the cost by hiding the thing being searched for.
_MAX_DOC_CHARS = 2000
# The sentence-transformers default. Raising it does not help here — measured on
# 200 full-length candidates, batch 32 took 16.3s against 23.1s at 64 and 22.0s
# at 128, because larger CPU batches lose more to memory traffic than they win
# in per-batch overhead.
_BATCH_SIZE = int(os.environ.get("EUGENE_RERANK_BATCH", "32"))
# Window size is set by the WORST tokenizer case in this corpus — table Markdown,
# which runs roughly 1.5 tokens per character against ~0.25 for prose. 600
# characters of table stays inside 512 tokens; prose windows are far under.
_WINDOW_CHARS = int(os.environ.get("EUGENE_RERANK_WINDOW", "600"))
# Enough that a row is never split across two windows without appearing whole in
# one of them.
_WINDOW_OVERLAP = 150
# Bounds the cost of one very long passage. Beyond this the tail is not what the
# retrievers matched on anyway.
_MAX_WINDOWS = 6


class RerankService:
    _instance: "RerankService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._failed = False

    @classmethod
    def instance(cls) -> "RerankService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def available(self) -> bool:
        return _ENABLED and not self._failed

    def _get_model(self):
        if self._model is None and not self._failed:
            with self._lock:
                if self._model is None and not self._failed:
                    try:
                        from sentence_transformers import CrossEncoder

                        logger.info(f"loading cross-encoder {_MODEL_NAME} on cpu")
                        self._model = CrossEncoder(_MODEL_NAME, device="cpu", max_length=512)
                    except Exception as e:
                        # Marked permanently failed: retrying the download on every
                        # request would turn a missing model into a latency bug.
                        self._failed = True
                        logger.warning(f"cross-encoder unavailable, reranking disabled: {e}")
        return self._model

    @staticmethod
    def _windows(text: str) -> list[str]:
        """Split a passage into overlapping windows, each small enough to survive.

        The model's 512-token limit is not a 2000-character limit for this corpus.
        A Markdown table tokenizes far worse than prose — `| --- | --- |` is all
        separators, and accession codes fragment into pieces — so a 1422-character
        table is silently cut around the 850th character. Every row below that
        point becomes invisible to the reranker, which is why questions about the
        first rows of a table scored fine and questions about the later rows of
        the SAME table were never retrieved.

        Scoring each window and keeping the best (MaxP) means a passage is judged
        by its most relevant part instead of by whatever fits in the first 512
        tokens.
        """
        text = text.strip()
        if len(text) <= _WINDOW_CHARS:
            return [text]
        step = _WINDOW_CHARS - _WINDOW_OVERLAP
        windows = [text[i : i + _WINDOW_CHARS] for i in range(0, len(text), step)]
        return windows[:_MAX_WINDOWS]

    @staticmethod
    def _passage(hit: dict[str, Any]) -> str:
        """What the cross-encoder actually reads for a hit — the body, nothing else.

        Prepending the paper title looks helpful and is actively harmful. Questions
        routinely name the paper, so every chunk of that paper then carries a span
        matching the question, and the reranker scores them all alike: with the
        title attached, ten passages from one paper came back at 0.9994–0.9999 and
        the table holding the answer did not make the top ten. Scoring the bare
        body separates them — the same table scores 0.9948 against 0.1336 for a
        prose passage from the same paper.

        The passage has to earn its rank on what it says, not on which document it
        came from; the retrievers already established the document.
        """
        return (hit.get("text") or hit.get("name") or "").strip()[:_MAX_DOC_CHARS]

    def rerank(self, query: str, hits: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Reorder `hits` by cross-encoder relevance. Returns at most `top_k`."""
        if not self.available() or not hits:
            return hits[:top_k]
        model = self._get_model()
        if model is None:
            return hits[:top_k]

        scored = hits[:_MAX_CANDIDATES]
        tail = hits[_MAX_CANDIDATES:]

        # One flat batch across every window of every candidate, with an index
        # back to the candidate each window came from. Predicting per candidate
        # would give up the batching that makes this affordable at all.
        pairs: list[tuple[str, str]] = []
        owner: list[int] = []
        for i, hit in enumerate(scored):
            for window in self._windows(self._passage(hit)):
                pairs.append((query, window))
                owner.append(i)
        try:
            scores = model.predict(pairs, show_progress_bar=False, batch_size=_BATCH_SIZE)
        except Exception as e:
            logger.warning(f"rerank scoring failed, keeping fused order: {e}")
            return hits[:top_k]

        best: dict[int, float] = {}
        for idx, score in zip(owner, scores):
            value = float(score)
            if value > best.get(idx, float("-inf")):
                best[idx] = value
        for i, hit in enumerate(scored):
            hit["rerank_score"] = round(best.get(i, float("-inf")), 6)
        scored.sort(key=lambda h: h["rerank_score"], reverse=True)
        # Un-scored tail keeps its fused order behind everything scored: it was
        # already ranked lower by RRF, and inventing a score for it would be a lie.
        return (scored + tail)[:top_k]


def rerank_service() -> RerankService:
    return RerankService.instance()
