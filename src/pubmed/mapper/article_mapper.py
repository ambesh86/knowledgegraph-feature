import logging

from pubmed.model.article import Article
from pubmed.model.affiliation import Affiliation

logger = logging.getLogger(__name__)


class ArticleMapper:

    def map_article(self, root) -> Article | None:
        if root is None:
            return None
        logger.debug(f"root={root}")
        front = root.find("front")
        if front is None:
            logger.warning(
                f"xml is missing the front element, cannot extract many fields. Moving on..."
            )
            return None
        article_metadata = front.find("article-meta")
        title_node = article_metadata.find("title-group/article-title")
        title = title_node.text
        (pmcid, pmid, doi) = self._parse_ids(article_metadata)
        pub_date = self._parse_pub_date(article_metadata)
        pdf_uri = self._parse_for_pdf(article_metadata)
        keywords = self._parse_for_keywords(article_metadata)
        affiliations = self._parse_for_affiliations(article_metadata)
        body = root.find("body")
        if body is not None:
            nct_ids = self._parse_for_clinicaltrail_ids(body)
        else:
            logger.warning(f"body not found in doc pmcid {pmcid}")
            nct_ids = set()
        if not pmcid:
            logger.warning(f"PMCID not found. PMID={pmid}, DOI={doi}")
            return None
        return Article(
            pmcid = int(pmcid),
            pmid=pmid,
            doi=doi,
            title=title,
            keywords=keywords,
            nct_ids=nct_ids,
            affiliations=affiliations,
            pub_date=pub_date,
            pdf_uri=pdf_uri,
        )

    def _parse_ids(self, article_metadata) -> tuple[str, str, str]:
        pmc = ""
        pmid = ""
        doi = ""
        ids = article_metadata.findall("article-id")
        for id in ids:
            logger.debug(f"article id: {id}")
            id_type = id.get("pub-id-type")
            match id_type:
                # pmc holds the numeric id; pmcid is PMC-prefixed and only used as a fallback
                case "pmc" | "pmcaid":
                    pmc = id.text
                case "pmcid" if not pmc:
                    pmc = id.text.removeprefix("PMC")
                case "pmid":
                    pmid = id.text
                case "doi":
                    doi = id.text
        return (pmc, pmid, doi)

    def _parse_pub_date(self, article_metadata) -> str:
        """
        parse pubdate from the article metadata
        """

        logger.debug("parsing for pub_date...")
        epub_date_el = article_metadata.find("pub-date[@pub-type='epub']")
        if epub_date_el is None:
            return ""

        day = epub_date_el.find("day")
        month = epub_date_el.find("month")
        year = epub_date_el.find("year")
        pub_date = f"{month.text}-{day.text}-{year.text}"
        return pub_date

    def _parse_for_pdf(self, article_metadata) -> str | None:
        uri_elements = article_metadata.findall("self-uri")
        if uri_elements is None:
            return None
        logger.debug(f"uris={uri_elements}")
        for uri_element in uri_elements:
            pdf_uri = self._parse_pdf_keys(uri_element)
            if pdf_uri is not None:
                return pdf_uri
        return None

    def _parse_pdf_keys(self, uri_element) -> str | None:
        keys = ["content-type", "http://www.w3.org/1999/xlink title"]
        for key in keys:
            if key in uri_element.keys() and uri_element.get(key) == "pdf":
                return uri_element.get("http://www.w3.org/1999/xlink href")

    def _parse_for_keywords(self, article_metadata) -> list[str]:
        # //text() at the end will get nested text e.g BRCC3 in this example
        # pmcid 11790519
        # https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=pmcid=11790519
        # <kwd id="cge14650-kwd-0001">
        #   <italic toggle="no">BRCC3</italic>
        # </kwd>
        keywords_el = article_metadata.xpath("./kwd-group/kwd//text()")
        if keywords_el is None:
            return []
        keywords = []
        for current_el in keywords_el:
            keywords.append(current_el)

        logger.info(f"found {len(keywords)} keywords")
        logger.debug(f"keywords: {keywords}")
        return keywords

    def _parse_for_clinicaltrail_ids(self, article_body) -> set[str]:
        """
        Sample link:
        <ext-link ext-link-type="ClinicalTrials.gov" xlink:href="NCT03336996" id="intref0040">NCT03336996</ext-link>
        """
        ext_links_el = article_body.xpath(
            ".//ext-link[@ext-link-type='ClinicalTrials.gov']"
        )
        if ext_links_el is None:
            logger.warning(f"no ext-link elements found in doc body...")
            return set()
        nct_ids = set()
        for ext_link_el in ext_links_el:
            nct_id = ext_link_el.text
            if nct_id is not None:
                nct_ids.add(nct_id)

        logger.info(f"found {len(nct_ids)} clinical trial id(s)")
        logger.debug(f"nct_ids: {nct_ids}")
        return nct_ids

    def _parse_for_affiliations(self, article_metadata) -> list[Affiliation]:
        affiliation_elements = article_metadata.findall("./aff")
        affiliations = []
        for affiliation_element in affiliation_elements:
            affiliation = self.map_affiliation(affiliation_element)
            if affiliation is not None:
                affiliations.append(affiliation)

        logger.info(f"found {len(affiliations)} affiliation(s)")
        return affiliations

    def map_affiliation(self, affiliation) -> Affiliation:
        location_parts = affiliation.xpath("./text()")
        location = " ".join([t.strip() for t in location_parts if t.strip() != ""])
        emails = affiliation.xpath("./email/text()")
        return Affiliation(location=location, emails=emails)
