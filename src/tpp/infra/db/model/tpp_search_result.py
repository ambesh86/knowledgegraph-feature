from pydantic import BaseModel


class TppSearchResult(BaseModel):
    score: float | None = None
    application_no: str | None = None
    product_description: str | None = None
    abstract: str | None = None
    claims: list[str] | None = None

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
