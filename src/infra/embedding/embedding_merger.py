import logging
import numpy as np
from numpy import ndarray


logger = logging.getLogger(__name__)


class EmbeddingMerger:
    """
    Class to merge embeddings
    """

    def merge(
        self,
        embeddings: list[ndarray],
        exclusion_embeddings: list[ndarray] | None = None,
    ) -> ndarray:
        are_common_dims = self._common_dimensions(embeddings)
        if not are_common_dims:
            raise Exception("embeddings must be common dimensions to merge!")

        if exclusion_embeddings is not None:
            negated_embeddings = self.negate_embedding(exclusion_embeddings)
            embeddings = self._extend_list(
                embeddings1=embeddings, embeddings2=negated_embeddings
            )

        self._log(embeddings)
        embedding_rows = np.array([embeddings])
        # axis=0 means sum along the vertical axis (rows)
        total = embedding_rows.sum(axis=0)
        merged = total / len(embedding_rows)
        return merged

    def negate_embedding(self, embeddings: list[ndarray]) -> list[ndarray]:
        """
        negate embeddings to be used as exclusions in a embedding/search space
        """
        negated = []
        for embedding in embeddings:
            logger.debug(f"negated embedding len: {len(negated)}")
            negated_embedding = np.negative(embedding)
            negated.append(negated_embedding)
        return negated

    def _extend_list(
        self, embeddings1: list[ndarray], embeddings2: list[ndarray]
    ) -> list[ndarray]:
        """
        contatenate two lists of embeddings
        """
        concatenated = []
        for embedding in embeddings1:
            concatenated.extend(embedding)

        for embedding in embeddings2:
            concatenated.extend(embedding)

        logger.debug(f"concat: {len(concatenated)}")
        return concatenated

    def _common_dimensions(self, embeddings: list[ndarray]) -> bool:
        """
        embeddings need to have the same dimensions to merge them
        """
        if embeddings is None or len(embeddings) == 0:
            return True

        all_same = True
        common_shape = embeddings[0].shape
        for embedding in embeddings:
            if embedding.shape != common_shape:
                common_shape = False
                break
        return all_same

    def _log(self, embeddings: list[ndarray]) -> None:
        logger.debug(f"embedding dimensions:")
        for embedding in embeddings:
            logger.debug(f"embedding len: {len(embedding)}")
            logger.debug(f"{embedding}")
