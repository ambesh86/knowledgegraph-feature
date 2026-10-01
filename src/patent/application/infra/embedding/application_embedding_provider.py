import logging
from numpy import ndarray

from infra.embedding.embedding_provider import EmbeddingProvider
from patent.application.model.application import Application

logger = logging.getLogger(__name__)


class ApplicationEmbeddingProvider(EmbeddingProvider):
    def to_embedding(self, application: Application) -> ndarray:
        chunks = self.to_chunks(application=application)
        model = self._model_from_sentence_transformer()
        embeddings = model.encode(chunks)
        logger.info(
            f"generated embeddings with dim: {embeddings.ndim} shape: {embeddings.shape}"
        )
        return embeddings

    def to_chunks(self, application: Application) -> list[str]:
        # todo: improve chunking using a text/paragraph splitter
        chunks = []
        if application.first_applicant_name is not None:
            chunks.append(application.first_applicant_name)
        chunks.append(application.application_type_code)
        chunks.append(application.invention_title)
        chunks.append(application.application_status_description_text)
        for cpc in application.cpc_classifications:
            chunks.append(cpc)

        return chunks
