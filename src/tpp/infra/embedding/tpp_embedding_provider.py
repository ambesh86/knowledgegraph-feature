import logging
from numpy import ndarray

from infra.embedding.embedding_provider import EmbeddingProvider
from infra.embedding.embedding_merger import EmbeddingMerger
from tpp.model.tpp_question import TppQuestion
from tpp.model.tpp import Tpp

logger = logging.getLogger(__name__)


class TppEmbeddingProvider(EmbeddingProvider):

    def __init__(self, model_cache_dir: str | None, embedding_merger: EmbeddingMerger):
        super().__init__(model_cache_dir=model_cache_dir)
        self.embedding_merger = embedding_merger
        self.model = self.init_model()

    def apply_embeddings(self, tpp: Tpp) -> Tpp:
        """
        generate an embedding for a target product profile and apply it to the given object
        """
        if tpp is None:
            return tpp

        embeddings = self.to_embeddings(tpp)
        logger.info(
            f"generated embeddings with dim: {embeddings.ndim} shape: {embeddings.shape}"
        )
        tpp.embeddings = embeddings

        return tpp

    def to_embeddings(self, tpp: Tpp) -> ndarray:
        """
        generate embeddings for a target product profile
        """
        base_embeddings = self._to_base_embeddings(tpp)
        all_embeddings = []
        all_embeddings.extend(base_embeddings)
        if tpp.questions is not None:
            for question in tpp.questions:
                question.embeddings = self._question_to_embedding(question)
                all_embeddings.extend(question.embeddings)
                logger.info(
                    f"generated question embeddings with dim: {question.embeddings.ndim} shape: {question.embeddings.shape}"
                )

        logger.info("merging tpp embeddings...")
        merged_embeddings = self.embedding_merger.merge(embeddings=all_embeddings)

        return merged_embeddings

    def _to_base_embeddings(self, tpp: Tpp) -> ndarray:
        """
        generate embeddings for the base fields in the given tpp
        """
        chunks = []
        if tpp.product_description is not None:
            chunks.append(tpp.product_description)

        if tpp.threaputic_area is not None:
            chunks.append(tpp.threaputic_area.name)

        base_embeddings = self.model.encode(chunks, show_progress_bar=False)

        return base_embeddings

    def _question_to_embedding(self, tpp_question: TppQuestion) -> ndarray:
        """
        generate embeddings for the tpp question, take into account the exclusion section as a negative embedding
        """
        positive_embeddings = self._question_to_include_embeddings(tpp_question)
        negative_embeddings = self._question_to_exclude_embeddings(tpp_question)

        logger.info("merging tpp question embeddings...")
        return self.embedding_merger.merge(
            embeddings=[positive_embeddings], exclusion_embeddings=[negative_embeddings]
        )

    def _question_to_include_embeddings(self, tpp_question: TppQuestion) -> ndarray:
        chunks = []
        chunks.append(tpp_question.question_type.name)
        chunks.append(tpp_question.acceptable)
        chunks.append(tpp_question.ideal)
        embeddings = self.model.encode(chunks, show_progress_bar=False)

        return embeddings

    def _question_to_exclude_embeddings(self, tpp_question: TppQuestion) -> ndarray:
        chunks = []
        chunks.append(tpp_question.excluded)
        embeddings = self.model.encode(chunks, show_progress_bar=False)

        return embeddings
