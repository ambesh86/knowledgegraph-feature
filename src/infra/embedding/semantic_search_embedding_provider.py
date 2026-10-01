import logging
from numpy import ndarray

from infra.embedding.embedding_provider import EmbeddingProvider
from infra.embedding.embedding_merger import EmbeddingMerger

logger = logging.getLogger(__name__)


class SemanticSearchEmbeddingProvider(EmbeddingProvider):
    """
    generic embedding provider to be used in a semantic search
    """

    def __init__(self, embedding_merger: EmbeddingMerger, model_cache_dir: str | None):
        super().__init__(model_cache_dir=model_cache_dir)
        self.embedding_merger = embedding_merger
        self.model = self._model_from_pretrained()

    def to_embedding(
        self, include_terms: str, exclude_terms: str | None = None
    ) -> ndarray:
        positive_embeddings = self.model.encode([include_terms])
        if exclude_terms is None:
            return positive_embeddings

        negative_embeddings = self.model.encode([include_terms])
        return self.embedding_merger.merge(
            embeddings=[positive_embeddings], exclusion_embeddings=[negative_embeddings]
        )
