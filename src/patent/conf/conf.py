import os

from infra.embedding.embedding_merger import EmbeddingMerger
from infra.embedding.semantic_search_embedding_provider import (
    SemanticSearchEmbeddingProvider,
)
from patent.pgpub.loader.pgpub_loader import PgpubLoader
from patent.pgpub.provider.pgpub_converter_provider import PgpubConverterProvider
from patent.pgpub.writer.txt_writer import TxtWriter
from patent.application.loader.application_loader import ApplicationLoader
from patent.application.writer.txt_writer import TxtWriter as ApplicationTxtWriter
from patent.application.provider.application_converter_provider import (
    ApplicationConverterProvider,
)


def patent_application_api_key() -> str:
    api_key = os.environ.get("USPTO_API_KEY")
    if api_key is None:
        raise ValueError("USPTO api key is missing from the environment...")
    return api_key


def embedding_merger() -> EmbeddingMerger:
    return EmbeddingMerger()


def semantic_search_embedding_provider() -> SemanticSearchEmbeddingProvider:
    return _semantic_search_embedding_provider(embedding_merger=embedding_merger())


def _semantic_search_embedding_provider(
    embedding_merger: EmbeddingMerger,
) -> SemanticSearchEmbeddingProvider:
    return SemanticSearchEmbeddingProvider(embedding_merger)


def pgpub_loader() -> PgpubLoader:
    return PgpubLoader()


def pgpub_writer() -> TxtWriter:
    return TxtWriter()


def _pgpub_converter_provider(
    loader: PgpubLoader, writer: TxtWriter
) -> PgpubConverterProvider:
    return PgpubConverterProvider(loader=loader, writer=writer)


def pgpub_converter_provider() -> PgpubConverterProvider:
    return _pgpub_converter_provider(loader=pgpub_loader(), writer=pgpub_writer())


def application_loader() -> ApplicationLoader:
    return ApplicationLoader()


def application_writer() -> ApplicationTxtWriter:
    return ApplicationTxtWriter()


def _application_converter_provider(
    loader: ApplicationLoader, writer: ApplicationTxtWriter
) -> ApplicationConverterProvider:
    return ApplicationConverterProvider(loader=loader, writer=writer)


def application_converter_provider() -> ApplicationConverterProvider:
    return _application_converter_provider(
        loader=application_loader(), writer=application_writer()
    )
