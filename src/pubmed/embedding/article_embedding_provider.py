import logging
from model2vec import StaticModel
from numpy import ndarray
from sentence_transformers import SentenceTransformer

from infra.embedding.embedding_provider import EmbeddingProvider
from pubmed.model.article import Article

logger = logging.getLogger(__name__)


class ArticleEmbeddingProvider(EmbeddingProvider):

    def __init__(self, model: SentenceTransformer | StaticModel | None = None):
        self._model = model
        if self._model is None:
            self._model = self._model_from_pretrained()

    def to_embedding(self, article: Article) -> tuple[ndarray, ndarray, ndarray]:
        """
        return the title, keywords and merged embeddings
        """
        if article is None:
            return (None, None, None)

        logger.debug(f"generating embeddings for article pmcid {article.pmcid}")

        title = article.title
        keywords = article.keywords
        title_embeddings = self._to_title_embeddings(title)
        keywords_embeddings = self._to_keywords_embeddings(keywords)
        merged_embeddings = self._to_merged_embeddings(title, keywords)

        logger.debug(
            f"generated embeddings with dim: {merged_embeddings.ndim} shape: {merged_embeddings.shape}"
        )
        return (title_embeddings, keywords_embeddings, merged_embeddings)

    def _to_title_embeddings(self, title: str | None) -> ndarray | None:
        if title is None:
            return None
        return self._model.encode([title])

    def _to_keywords_embeddings(self, keywords: list[str] | None) -> ndarray | None:
        if self._is_empty(keywords):
            return None
        logger.info(f"encoding keywords {keywords}")
        return self._model.encode(keywords)

    def _to_merged_embeddings(self, title: str, keywords: list[str]) -> ndarray | None:
        if title is None and self._is_empty(keywords):
            return None
        all_fields = [title] if title is not None else []
        if keywords is not None and len(keywords) > 0:
            all_fields.extend(keywords)
        merged_embeddings = self._model.encode(all_fields)
        return merged_embeddings

    def _is_empty(self, arr: list[str] | None) -> bool:
        return arr is None or len(arr) == 0
