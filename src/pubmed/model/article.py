from numpy import ndarray

from pubmed.model.affiliation import Affiliation


class Article:

    def __init__(
        self,
        pmcid: int,
        pmid: str,
        doi: str,
        keywords: list[str] | None,
        nct_ids: set[str] | None,
        affiliations: list[Affiliation] | None,
        title_embeddings: ndarray | None = None,
        keywords_embeddings: ndarray | None = None,
        merged_embeddings: ndarray | None = None,
        title: str | None = "",
        pub_date: str | None = "",
        pdf_uri: str | None = "",
    ):
        # todo: add authors among other things
        self.pmcid = pmcid
        self.pmid = pmid
        self.doi = doi
        self.title = title
        self.pub_date = pub_date
        self.pdf_uri = pdf_uri
        self.keywords = keywords
        self.nct_ids = nct_ids
        self.affiliations = affiliations
        self.title_embeddings = title_embeddings
        self.keywords_embeddings = keywords_embeddings
        self.merged_embeddings = merged_embeddings

    def __eq__(self, other):
        return self is other or (
            self.pmcid == other.pmcid
            and self.pmid == other.pmid
            and self.doi == other.doi
        )

    def __hash__(self):
        return hash((self.pmcid, self.pmid, self.doi))

    def __repr__(self):
        return "pmcid={} doi={} pmid={} pub_date={}".format(
            self.pmcid, self.doi, self.pmid, self.pub_date
        )

    def __str__(self):
        return repr(self)
