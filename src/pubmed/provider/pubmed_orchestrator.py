import logging
from time import sleep
from pubmed.model.article import Article
from pubmed.provider.pubmed_download_provider import PubmedDownloadProvider
from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from pubmed.provider.pubmed_search_provider import PubmedSearchProvider
from pubmed.infra.db.neo4j_article_adapter import Neo4jArticleAdapter

logger = logging.getLogger(__name__)


class PubmedOrchestrator:
    FETCH_THROTTLE_SECS = 10

    def __init__(
        self,
        pubmed_search_provider: PubmedSearchProvider,
        pubmed_fetch_provider: PubmedFetchProvider,
        pubmed_download_provider: PubmedDownloadProvider,
        neo4j_article_adapter: Neo4jArticleAdapter,
    ):
        self.pubmed_search_provider = pubmed_search_provider
        self.pubmed_fetch_provider = pubmed_fetch_provider
        self.pubmed_download_provider = pubmed_download_provider
        self.neo4j_article_adapter = neo4j_article_adapter

    def search_and_download(self, term: str) -> None:
        logger.info(f"searching for term={term}...")
        pmcids = self.pubmed_search_provider.search_recently_modified(
            term, max_results=10
        )
        return self.fetch_and_download(pmcids=pmcids)

    def fetch_and_download(self, pmcids: list[str]) -> None:
        logger.info(f"fetching articles for {len(pmcids)} pmc ids")
        failed_download_count = 0
        download_count = 0
        for pmcid in pmcids:
            logger.info(f"fetching {pmcid}")
            try:
                sleep(PubmedOrchestrator.FETCH_THROTTLE_SECS)
                article = self.pubmed_fetch_provider.fetch_by_id(pmcid=pmcid)
                if article is None:
                    logger.warning(f"failed to fetch article for pmcid: {pmcid}")
                    failed_download_count += 1
                    continue
                pdf = self._pick_pdf_name(article)
                self.pubmed_download_provider.download(
                    pmcid=str(article.pmcid), pdf_name=pdf
                )
                self.neo4j_article_adapter.upsert_article(article=article)
                download_count += 1
            except Exception as e:
                logger.exception(f"failed to download/upsert pmcid {pmcid}: {e}")
                failed_download_count += 1

        logger.info(
            f"downloaded {download_count}/{download_count+failed_download_count} pmcid(s)"
        )
        logger.info(f"download finished for {len(pmcids)} ids")

    def _pick_pdf_name(self, article: Article) -> str:
        # use the pdf_uri is provided, otherwise use the doi
        # the doi will work but sometimes requires a redirect
        pdf = article.pdf_uri if article.pdf_uri is not None else article.doi
        return pdf
