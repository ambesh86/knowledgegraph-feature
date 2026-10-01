from graph.model.finding import Finding


class Summary:
    def __init__(
        self,
        title: str,
        summary: str,
        rating: float,
        rating_explanation: str,
        findings: list[Finding],
        id: str = "",
        level: str = "",
    ):
        self.id = id
        self.title = title
        self.summary = summary
        self.rating = rating
        self.rating_explanation = rating_explanation
        self.findings = findings
        self.level = level

    def __eq__(self, other):
        return self is other or (
            self.id == other.id
            and self.level == other.level
            and self.title == other.title
        )

    def __hash__(self):
        return hash((self.id, self.title))

    def __repr__(self):
        return "{}:{}".format(self.id, self.title)

    def __str__(self):
        return repr(self)
