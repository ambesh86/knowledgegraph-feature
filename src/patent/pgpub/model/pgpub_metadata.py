from datetime import datetime


class PgpubMetadata:
    """
    uspto associated document for a patent application and its analyzed contents
    See, https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
    """

    def __init__(
        self,
        application_number_text: str,
        file_location_uri: str,
        file_create_dtg: datetime,
    ):
        self.application_number_text = application_number_text
        self.file_location_uri = file_location_uri
        self.file_create_dtg = file_create_dtg

    def __eq__(self, other):
        return self is other or (
            self.application_number_text == other.application_number_text
            and self.file_location_uri == other.file_location_uri
            and self.file_create_dtg == other.file_create_dtg
        )

    def __hash__(self):
        return hash(
            (
                self.application_number_text,
                self.file_location_uri,
                self.file_create_dtg,
            )
        )

    def __repr__(self):
        return (
            "application_number_text={} file_location_uri={} file_create_dtg={}".format(
                self.application_number_text,
                self.file_location_uri,
                self.file_create_dtg,
            )
        )

    def __str__(self):
        return repr(self)
