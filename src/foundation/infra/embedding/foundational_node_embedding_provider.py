import logging
from model2vec import StaticModel
from numpy import ndarray
from sentence_transformers import SentenceTransformer

from infra.embedding.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class FoundationalNodeEmbeddingProvider(EmbeddingProvider):

    def __init__(
        self,
        model: SentenceTransformer | StaticModel | None = None,
        model_cache_dir: str | None = None,
    ):
        super().__init__(model_cache_dir=model_cache_dir)
        self._model = model
        if self._model is None:
            self._model = self.init_model()

    def to_embedding(self, value: str) -> ndarray:
        """
        return the embedding for the given value
        """
        if value is None:
            return None

        logger.debug(f"generating embeddings for value {value}")
        embedding = self._model.encode([value])

        logger.debug(
            f"generated embeddings with dim: {embedding.ndim} shape: {embedding.shape}"
        )
        return embedding
