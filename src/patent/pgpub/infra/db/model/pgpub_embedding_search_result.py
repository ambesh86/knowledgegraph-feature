class PgpubEmbeddingSearchResult:

    def __init__(
        self,
        score: float | None = None,
        application_no: str | None = None,
    ):
        self.score = score
        self.application_no = application_no

    def __eq__(self, other):
        return self is other or (
            self.score == other.score and self.application_no == other.application_no
        )

    def __hash__(self):
        return hash(
            (
                self.score,
                self.application_no,
            )
        )

    def __repr__(self):
        return "score={} application_no={}".format(
            self.score,
            self.application_no,
        )

    def __str__(self):
        return repr(self)
