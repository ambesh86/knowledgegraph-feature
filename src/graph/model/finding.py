class Finding:
    def __init__(self, summary: str, explanation: str, id: str = ""):
        self.summary = summary
        self.explanation = explanation
        self.id = id

    def __eq__(self, other):
        return self is other or (self.id == other.id and self.summary == other.summary)

    def __hash__(self):
        return hash((self.summary))

    def __repr__(self):
        return "{}".format(self.summary)

    def __str__(self):
        return repr(self)
