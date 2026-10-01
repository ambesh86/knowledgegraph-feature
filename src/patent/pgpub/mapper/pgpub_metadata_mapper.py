from datetime import datetime
import logging
import json

from patent.pgpub.model.pgpub_metadata import PgpubMetadata

logger = logging.getLogger(__name__)


class PgpubMetadataMapper:
    DTG_FORMAT = "%Y-%m-%dT%H:%M:%S"

    """
    map responses from listing pgpub associated documents
    https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
    """

    def map(self, json_payload: str | None) -> list[PgpubMetadata] | None:
        if json_payload is None:
            return None

        pgpubs = []
        try:
            parsed = json.loads(json_payload)
            items = parsed["patentFileWrapperDataBag"]
            for item in items:
                pgpub_metadata = self._map_pgpub_metadata(item)
                if pgpub_metadata is not None:
                    pgpubs.append(pgpub_metadata)
        except json.JSONDecodeError as e:
            logger.warning(f"ignoring json parse error: {e}")
            raise e

        return pgpubs

    def _map_pgpub_metadata(self, patent_file_wrapper) -> PgpubMetadata | None:
        application_number_text = patent_file_wrapper["applicationNumberText"]
        metadata_key = "pgpubDocumentMetaData"
        if metadata_key not in patent_file_wrapper:
            logger.warning(
                f"no metadata associated documents found for {application_number_text}"
            )
            return None
        pgpub_document_metadata = patent_file_wrapper["pgpubDocumentMetaData"]
        file_location_uri = pgpub_document_metadata["fileLocationURI"]
        file_create_dtg = datetime.strptime(
            pgpub_document_metadata["fileCreateDateTime"], self.DTG_FORMAT
        )
        return PgpubMetadata(
            application_number_text=application_number_text,
            file_create_dtg=file_create_dtg,
            file_location_uri=file_location_uri,
        )
