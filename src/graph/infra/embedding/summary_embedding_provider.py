import logging
from torch import Tensor

from graph.model.summary import Summary
from infra.embedding.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class SummaryEmbeddingProvider(EmbeddingProvider):

    def __init__(self, model_cache_dir: str | None):
        super().__init__(model_cache_dir=model_cache_dir)

    def summary_to_embedding(self, summary: Summary) -> Tensor:
        chunks = self.to_chunks(summary=summary)
        model = self._model_from_sentence_transformer()
        embeddings = model.encode(chunks)
        logger.info(
            f"generated embeddings with dim: {embeddings.ndim} shape: {embeddings.shape}"
        )
        return embeddings

    def to_chunks(self, summary: Summary) -> str:
        # todo: improve chunking using a text/paragraph splitter
        chunks = []
        chunks.append(summary.title)
        chunks.append(summary.summary)
        for finding in summary.findings:
            chunks.append(finding.summary)
            chunks.append(finding.explanation)

        # todo: undo join, when i learn how to store and search n dimension vectors in milvus
        return "\n".join(chunks)
