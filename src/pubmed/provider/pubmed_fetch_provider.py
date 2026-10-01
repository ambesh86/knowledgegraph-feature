import logging
from Bio import Entrez

from lxml import etree
from pubmed.helper.util import apply_bio_email
from pubmed.mapper.article_mapper import ArticleMapper
from pubmed.model.article import Article


logger = logging.getLogger(__name__)


class PubmedFetchProvider:

    def __init__(self, article_mapper: ArticleMapper, email: str = ""):
        apply_bio_email(email)
        self.article_mapper = article_mapper

    def fetch_by_ids(self, pmcids: list[str]) -> list[Article]:
        """
        fetch options - https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.EFetch

        sample response - https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=212403
        """
        articles = []
        for pmcid in pmcids:
            article = self.fetch_by_id(pmcid)
            articles.append(article)

        logger.info(f"fetched {len(articles)} article(s)")
        return articles

    def fetch_by_id(self, pmcid: str) -> Article | None:
        """
        fetch options - https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.EFetch

        sample response - https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=212403

        to fetch by multiple ids use the history server

        This will automatically use an HTTP POST rather than HTTP GET if there are over 200 identifiers as recommended by the NCBI.
        """
        db = "pmc"
        handle = None
        try:
            logger.info(f"fetch pmcid: '{pmcid}'")
            handle = Entrez.efetch(db=db, id=pmcid, retmode="xml")
            # records = Entrez.read(handle)
            xml_content = handle.read()
            logger.debug(f"doc: {xml_content}")
            root = etree.fromstring(xml_content)
            article = root[0]
            return self.article_mapper.map_article(article)
        except IndexError as ie:
            logger.warning(ie)
            raise ie
        finally:
            if handle is not None:
                handle.close()
