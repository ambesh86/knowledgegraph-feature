from numpy import ndarray
from patent.pgpub.model.pgpub_metadata import PgpubMetadata


class Pgpub:
    """
    uspto associated document for a patent application and its analyzed contents
    See, https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
    """

    def __init__(
        self,
        application_number_text: str,
        pgpub_metadata: PgpubMetadata,
        abstract: str,
        description: list[str] | None,
        claims: list[str] | None,
        organizations: set[str] | None,
        chemical_compound_synonyms: set[str] | None = None,
        embeddings: ndarray | None = None,
    ):
        self.application_number_text = application_number_text
        self.pgpub_metadata = pgpub_metadata
        self.abstract = abstract
        self.description = description
        self.claims = claims
        self.organizations = organizations
        self.chemical_compound_synonyms = chemical_compound_synonyms
        self.embeddings = embeddings

    def __eq__(self, other):
        file_location_uri = (
            self.pgpub_metadata.file_location_uri
            if self.pgpub_metadata is not None
            else ""
        )
        file_create_dtg = (
            self.pgpub_metadata.file_create_dtg
            if self.pgpub_metadata is not None
            else ""
        )
        other_file_location_uri = (
            other.pgpub_metadata.file_location_uri
            if other.pgpub_metadata is not None
            else ""
        )
        other_file_create_dtg = (
            other.pgpub_metadata.file_create_dtg
            if other.pgpub_metadata is not None
            else ""
        )
        return self is other or (
            self.application_number_text == other.application_number_text
            and file_location_uri == other_file_location_uri
            and file_create_dtg == other_file_create_dtg
        )

    def __hash__(self):
        return hash(
            (
                self.application_number_text,
                self.pgpub_metadata.file_location_uri,
                self.pgpub_metadata.file_create_dtg,
            )
        )

    def __repr__(self):
        return "application_number_text={} file_location_uri={} file_create_date_time={}".format(
            self.application_number_text,
            self.pgpub_metadata.file_location_uri,
            self.pgpub_metadata.file_create_dtg,
        )

    def __str__(self):
        return repr(self)
