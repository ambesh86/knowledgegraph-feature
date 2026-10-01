import datetime


class Application:

    def __init__(
        self,
        application_number_text: str | None,
        invention_title: str,
        first_applicant_name: str | None,
        applicants: set[str] | None,
        application_status_description_text: str,
        application_status_code: int,
        customer_number: int | None,
        application_type_code: str,
        application_type_label_name: str,
        cpc_classifications: set[str],
        application_status_date: datetime.date,
        effective_filing_date: datetime.date | None,
        filing_date: datetime.date,
        patent_number: int | None,
        grant_date: datetime.date | None,
    ):
        self.application_number_text = application_number_text
        self.invention_title = invention_title
        self.first_applicant_name = first_applicant_name
        self.applicants = applicants
        self.application_status_description_text = application_status_description_text
        self.application_status_code = application_status_code
        self.customer_number = customer_number
        self.application_type_code = application_type_code
        self.application_type_label_name = application_type_label_name
        self.cpc_classifications = cpc_classifications
        self.application_status_date = application_status_date
        self.effective_filing_date = effective_filing_date
        self.filing_date = filing_date
        self.patent_number = patent_number
        self.grant_date = grant_date

    def __eq__(self, other):
        return self is other or (
            self.application_number_text == other.application_number_text
            and self.application_type_code == other.application_type_code
            and self.first_applicant_name == other.first_applicant_name
        )

    def __hash__(self):
        return hash(
            (
                self.application_number_text,
                self.application_type_code,
                self.first_applicant_name,
            )
        )

    def __repr__(self):
        return "application_number_text={} application_type_code={} first_application_name={} invention_title={}".format(
            self.application_number_text,
            self.application_type_code,
            self.first_applicant_name,
            self.invention_title,
        )

    def __str__(self):
        return repr(self)
