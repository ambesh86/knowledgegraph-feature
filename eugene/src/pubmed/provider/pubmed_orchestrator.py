import logging
from time import sleep
from pubmed.helper.util import apply_bio_email
from pubmed.model.article import Article
from pubmed.provider.pubmed_download_provider import PubmedDownloadProvider
from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from pubmed.provider.pubmed_search_provider import PubmedSearchProvider

logger = logging.getLogger(__name__)


class PubmedOrchestrator:

    def __init__(
        self,
        pubmed_search_provider: PubmedSearchProvider,
        pubmed_fetch_provider: PubmedFetchProvider,
        pubmed_download_provider: PubmedDownloadProvider,
    ):
        self.pubmed_search_provider = pubmed_search_provider
        self.pubmed_fetch_provider = pubmed_fetch_provider
        self.pubmed_download_provider = pubmed_download_provider

    def search_and_download(self, term: str) -> str:
        logger.info(f"searching for term={term}...")
        pmcids = self.pubmed_search_provider.search_recently_modified(
            term, max_results=10
        )
        logger.info(f"fetching articles for {len(pmcids)} pmc ids for term={term}")
        for pmcid in pmcids:
            sleep(2)
            article = self.pubmed_fetch_provider.fetch_by_id(pmcid=pmcid)
            pdf = self._pick_pdf_name(article)
            self.pubmed_download_provider.download(pmcid=article.pmcid, pdf_name=pdf)

        logger.info(f"download finished for {len(pmcids)} ids found for term={term}")

    def _pick_pdf_name(self, article: Article) -> str:
        # use the pdf_uri is provided, otherwise use the doi
        # the doi will work but sometimes requires a redirect
        pdf = article.pdf_uri if article.pdf_uri is not None else article.doi
        return pdf
