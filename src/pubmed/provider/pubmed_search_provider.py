import logging
from Bio import Entrez

from pubmed.helper.util import apply_bio_email

logger = logging.getLogger(__name__)


class PubmedSearchProvider:
    """
    this class will search and return pmc ids

    pub med has several indexes
    pubmed central (pmc) and pubmed
    pmc has full free text articles e.g. pdfs

    pub med articles have several ids depending on the datasource
    pmcid (pub med central id)
    pmid (pubmed id)
    digital object identifier (doi)
    plus other journal specific ids depending on the article source
    """

    def __init__(self, email: str = ""):
        apply_bio_email(email)

    def search_recently_modified(
        self, term: str, relative_date: int = 120, max_results=10_000
    ) -> list[str]:
        """
        search options - https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch

        sample term "stem cells AND free fulltext[filter]"

        sample response https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term=stem+cells+AND+free+fulltext%5bfilter%5d

        return list of pmcids

        pubmed search can return up to 10k results in one request
        """
        # mdat = modification date
        # pdat = publication date
        modification_date = "mdat"
        sort_by_date = "pub_date"
        # pmc has free full text
        db = "pmc"  # "pubmed" or "pmc"
        handle = None
        try:
            logger.info(
                f"search for recently modified documents related to terms '{term}'"
            )
            handle = Entrez.esearch(
                db=db,
                term=term,
                datetype=modification_date,
                reldate=relative_date,
                retmax=max_results,
                # sort=sort_by_date,
            )
            data = Entrez.read(handle)
            logger.info(f"{data}")
            warning_key = "WarningList"
            id_key = "IdList"
            if warning_key in data:
                logger.warning(f"search returned warnings: {data[warning_key]}")
            ids = data[id_key] if id_key in data else []
            if ids is None:
                logger.warning(f"no ids found in response")

            logger.info(f"found {len(ids)} pmcid(s)")

            pmcids = []
            for id in ids:
                pmcids.append(id)
            return pmcids
        except IndexError as ie:
            logger.warning(ie)
            raise ie
        finally:
            if handle is not None:
                handle.close()
