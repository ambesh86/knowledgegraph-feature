import logging

from pubmed.model.article import Article

logger = logging.getLogger(__name__)


class ArticleMapper:

    def map_article(self, record) -> Article:
        logger.debug(f"record={record}")
        front = record["front"]
        article_metadata = front["article-meta"]
        title_node = article_metadata["title-group"]["article-title"]
        title = str(title_node)
        logger.debug(f"title: {title}")

        (pmcid, pmid, doi) = self._parse_ids(article_metadata)
        pub_date = self._parse_pub_date(article_metadata)
        logger.debug(f"found pub_date={pub_date}")
        pdf_uri = self._parse_for_pdf(article_metadata)
        return Article(
            pmcid=pmcid,
            pmid=pmid,
            doi=doi,
            title=title,
            pub_date=pub_date,
            pdf_uri=pdf_uri,
        )

    def _parse_ids(self, article_metadata) -> tuple:
        pmc = ""
        pmid = ""
        doi = ""
        ids = article_metadata["article-id"]
        for id in ids:
            logger.debug(f"article id: {id}")
            id_type = id.attributes.get("pub-id-type")
            match id_type:
                case "pmc":
                    pmc = str(id)
                case "pmid":
                    pmid = str(id)
                case "doi":
                    doi = str(id)
        return (pmc, pmid, doi)

    def _parse_pub_date(self, article_metadata) -> str:
        """
        parse pubdate from the article metadata
        """

        pub_date_nodes = article_metadata["pub-date"]
        pub_date = ""
        logger.debug("parsing for pub_date...")
        for node in pub_date_nodes:
            logger.debug(f"node: {node}")
            match node.attributes.get("pub-type"):
                case "epub":
                    pub_date = f"{node[1]}-{node[0]}-{node[2]}"
        return pub_date

    def _parse_for_pdf(self, article_metadata) -> str:
        uri_elements = article_metadata["self-uri"]
        logger.debug(f"uris={uri_elements}")
        for uri_element in uri_elements:
            pdf_uri = self._parse_pdf_keys(uri_element)
            if pdf_uri is not None:
                return pdf_uri
        return None

    def _parse_pdf_keys(self, uri_element) -> str | None:
        keys = ["content-type", "http://www.w3.org/1999/xlink title"]
        for key in keys:
            if (
                key in uri_element.attributes
                and uri_element.attributes.get(key) == "pdf"
            ):
                return uri_element.attributes.get("http://www.w3.org/1999/xlink href")
