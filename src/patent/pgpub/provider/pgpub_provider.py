import logging

import requests

from patent.application.conf.const import USPTO_FILES_BASE_URI
from patent.application.provider.util import raise_error
from patent.pgpub.mapper.pgpub_mapper import PgpubMapper
from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.model.pgpub_metadata import PgpubMetadata

logger = logging.getLogger(__name__)


class PgpubProvider:

    def __init__(self, pgpub_mapper: PgpubMapper, api_key: str):
        self.pgpub_mapper = pgpub_mapper
        self.base_headers = {
            "Accept": "application/json",
            "x-api-key": api_key,
        }

    def fetch_pgpub(self, pgpub_metadata: PgpubMetadata) -> Pgpub | None:
        """
        Download and pgpub xml given a pgpub metadata
        See, https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
        """
        if pgpub_metadata is None or pgpub_metadata.file_location_uri is None:
            return None

        file_location_uri = pgpub_metadata.file_location_uri
        if not file_location_uri.startswith(USPTO_FILES_BASE_URI):
            raise ValueError(
                "Expected {flie_location_uri} to start with the uspto files base uri: {USPTO_FILES_BASE_URI}"
            )

        logger.info(f"fetching {file_location_uri}")
        response = requests.get(file_location_uri, headers=self.base_headers)

        if response.status_code == 200:
            pgpub_doc = self.pgpub_mapper.map(
                pgpub_metadata=pgpub_metadata, xml_response=response.content
            )
            logger.info(f"found {pgpub_doc} pgpub doc")
            return pgpub_doc
        else:
            content = response.content.decode("utf-8")
            raise_error(response.status_code, response.reason, content)
