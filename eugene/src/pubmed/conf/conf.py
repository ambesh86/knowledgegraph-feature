from pathlib import Path
from pubmed.helper.const import DEFAULT_BIO_EMAIL
from pubmed.mapper.article_mapper import ArticleMapper
from pubmed.provider.pubmed_download_provider import PubmedDownloadProvider
from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from pubmed.provider.pubmed_orchestrator import PubmedOrchestrator
from pubmed.provider.pubmed_search_provider import PubmedSearchProvider


def _default_bio_email():
    return DEFAULT_BIO_EMAIL


def _article_mapper():
    return ArticleMapper()


def _pubmed_fetch_provider(article_mapper=_article_mapper()):
    return PubmedFetchProvider(article_mapper=article_mapper, email=_default_bio_email())


def _pubmed_search_provider():
    return PubmedSearchProvider(email=_default_bio_email())


def _pubmed_download_provider():
    return PubmedDownloadProvider(download_dest=Path("./tmp"))


def _pubmed_orchestrator(
    pubmed_search_provider=_pubmed_search_provider(), 
    pubmed_fetch_provider=_pubmed_fetch_provider(),
    pubmed_download_provider=_pubmed_download_provider()
):
    return PubmedOrchestrator(
            pubmed_search_provider=pubmed_search_provider,
            pubmed_fetch_provider=pubmed_fetch_provider,
            pubmed_download_provider=pubmed_download_provider,
    )
