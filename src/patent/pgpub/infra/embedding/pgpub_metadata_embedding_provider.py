import logging
from numpy import ndarray

from infra.embedding.embedding_provider import EmbeddingProvider
from patent.pgpub.model.pgpub import Pgpub

logger = logging.getLogger(__name__)


class PgpubEmbeddingProvider(EmbeddingProvider):
    def to_embedding(self, pgpub: Pgpub) -> ndarray:
        chunks = self.to_chunks(pgpub=pgpub)
        model = self.init_model()
        embeddings = model.encode(chunks)
        logger.info(
            f"generated embeddings with dim: {embeddings.ndim} shape: {embeddings.shape}"
        )
        return embeddings

    def to_chunks(self, pgpub: Pgpub) -> list[str]:
        # todo: improve chunking using a text/paragraph splitter
        chunks = []

        if pgpub.organizations is not None:
            for org in pgpub.organizations:
                chunks.append(org)

        if pgpub.abstract is not None:
            chunks.append(pgpub.abstract)

        # todo: rethink join all claims
        #   at the moment the claims list has fragmentation in splitting
        # For example, claims elements sometimes have bullet numbers by them selves
        # I do not want to overindex on these bullet number which might match on non relevant docs
        if pgpub.claims is not None:
            all_claims = " ".join(pgpub.claims)
            chunks.append(all_claims)

        return chunks
