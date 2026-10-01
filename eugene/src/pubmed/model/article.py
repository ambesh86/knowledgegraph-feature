class Article:

    def __init__(
        self,
        pmcid: int,
        pmid: str,
        doi: str,
        title: str | None = "",
        pub_date: str | None = "",
        pdf_uri: str | None = "",
    ):
        # todo: add authors and affiliated institutions among other things
        self.pmcid = pmcid
        self.pmid = pmid
        self.doi = doi
        self.title = title
        self.pub_date = pub_date
        self.pdf_uri = pdf_uri

    def __eq__(self, other):
        return self is other or (
            self.pmcid == other.pmcid
            and self.pmid == other.pmid
            and self.doi == other.doi
        )

    def __hash__(self):
        return hash((self.pmcid, self.pmid, self.doi))

    def __repr__(self):
        return "pmcid={} doi={} pmid={} pub_date=".format(
            self.pmcid, self.doi, self.pmid, self.pub_date
        )

    def __str__(self):
        return repr(self)
