"""Semantic vector search over PubMed-style summaries (Milvus / milvus-lite).

Container-safe: embeddings run on CPU (the SummaryEmbeddingProvider hardcodes
device='mps', which only exists on macOS, so we load the SentenceTransformer
directly here with device='cpu').

The 'pubmed' collection is created and seeded lazily on first use so the vector
store is usable on a fresh local stack without the offline store_summaries.py
checkpoint pipeline.
"""
import logging
import os
import threading

from pymilvus import MilvusClient

from foundation.vector.seed_summaries import SEED_SUMMARIES

logger = logging.getLogger(__name__)

_COLLECTION = "pubmed"
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim
_DIM = 384


class VectorSearchService:
    _instance: "VectorSearchService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # EUGENE_-prefixed on purpose: pymilvus reads a bare `MILVUS_URI` into
        # its own global Config at import time and demands an http(s):// address,
        # so pointing that variable at a milvus-lite file path makes `import
        # pymilvus` raise and silently disables the whole vector subsystem.
        # milvus-lite additionally requires the path to end in `.db`.
        self._uri = os.environ.get(
            "EUGENE_MILVUS_URI", "/app/.db/eugene_vectors.db"
        )
        if not self._uri.startswith(("http://", "https://")) and not self._uri.endswith(".db"):
            logger.warning(
                f"milvus-lite uri must end in '.db' — appending to {self._uri!r}"
            )
            self._uri = f"{self._uri}.db"
        self._token = os.environ.get("EUGENE_MILVUS_TOKEN", "")
        # Ensure the parent dir exists for the embedded milvus-lite file.
        parent = os.path.dirname(self._uri)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._client: MilvusClient | None = None
        self._model = None
        self._seeded = False

    @classmethod
    def instance(cls) -> "VectorSearchService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- lazy resources ----------------------------------------------------
    def _get_client(self) -> MilvusClient:
        if self._client is None:
            logger.info(f"connecting milvus-lite uri={self._uri}")
            self._client = MilvusClient(uri=self._uri, token=self._token)
        return self._client

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(f"loading embedding model {_MODEL_NAME} on cpu")
            self._model = SentenceTransformer(_MODEL_NAME, device="cpu")
        return self._model

    def _embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vecs = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    # -- seeding -----------------------------------------------------------
    def ensure_seeded(self) -> None:
        if self._seeded:
            return
        client = self._get_client()
        try:
            exists = client.has_collection(_COLLECTION)
            count = 0
            if exists:
                try:
                    count = client.get_collection_stats(_COLLECTION).get("row_count", 0)
                except Exception:
                    count = 0
            if exists and count and int(count) > 0:
                logger.info(f"collection '{_COLLECTION}' already populated ({count} rows)")
                self._seeded = True
                return

            if exists:
                client.drop_collection(_COLLECTION)
            logger.info(f"creating + seeding collection '{_COLLECTION}' (dim={_DIM})")
            client.create_collection(
                collection_name=_COLLECTION,
                dimension=_DIM,
                metric_type="IP",  # normalized embeddings -> IP == cosine
                auto_id=False,
                # dynamic fields keep title/summary/url alongside the vector
            )
            texts = [f"{s['title']}. {s['summary']}" for s in SEED_SUMMARIES]
            vectors = self._embed(texts)
            rows = []
            for i, (s, v) in enumerate(zip(SEED_SUMMARIES, vectors)):
                rows.append(
                    {
                        "id": i,
                        "vector": v,
                        "summary_id": s["summary_id"],
                        "title": s["title"],
                        "summary": s["summary"],
                        "url": s["url"],
                    }
                )
            client.insert(collection_name=_COLLECTION, data=rows)
            logger.info(f"seeded {len(rows)} summaries into '{_COLLECTION}'")
            self._seeded = True
        except Exception as e:
            logger.error(f"vector seed failed: {e}")
            raise

    # -- search ------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> dict:
        self.ensure_seeded()
        client = self._get_client()
        qvec = self._embed([query])[0]
        res = client.search(
            collection_name=_COLLECTION,
            data=[qvec],
            limit=max(1, min(int(top_k), 20)),
            output_fields=["summary_id", "title", "summary", "url"],
        )
        hits = []
        for h in (res[0] if res else []):
            ent = h.get("entity", {})
            hits.append(
                {
                    "summary_id": ent.get("summary_id"),
                    "title": ent.get("title"),
                    "summary": ent.get("summary"),
                    "url": ent.get("url"),
                    "score": round(float(h.get("distance", 0.0)), 4),
                }
            )
        return {"query": query, "count": len(hits), "results": hits, "source": "Eugene vector store (Milvus)"}

    def health(self) -> dict:
        client = self._get_client()
        ok = client.has_collection(_COLLECTION)
        rows = 0
        if ok:
            try:
                rows = int(client.get_collection_stats(_COLLECTION).get("row_count", 0))
            except Exception:
                rows = 0
        return {"ready": bool(ok and rows > 0), "collection": _COLLECTION, "rows": rows, "uri": self._uri}


def vector_search_service() -> VectorSearchService:
    return VectorSearchService.instance()
