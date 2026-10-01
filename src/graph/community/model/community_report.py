class CommunityReport:
    def __init__(
        self,
        title: str = "",
        summary: str = "",
        rating: str = "",
        rating_explanation: str = "",
        findings: list = [],
    ):
        self.title = title
        self.summary = summary
        self.rating = rating
        self.rating_explanation = rating_explanation
        self.findings = findings
