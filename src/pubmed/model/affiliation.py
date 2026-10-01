class Affiliation:

    def __init__(
        self,
        location: str,
        emails: list[str] | None,
        affiliation_id: str | None = "",
    ):
        self.location = location
        self.emails = emails
        self.affiliation_id = affiliation_id

    def __eq__(self, other):
        return self is other or (
            self.affiliation_id == other.affiliation_id
            and self.location == other.location
        )

    def __hash__(self):
        return hash((self.affiliation_id, self.location))

    def __repr__(self):
        return "affiliation_id={} location={} emails={}".format(
            self.affiliation_id, self.location, self.emails
        )

    def __str__(self):
        return repr(self)
