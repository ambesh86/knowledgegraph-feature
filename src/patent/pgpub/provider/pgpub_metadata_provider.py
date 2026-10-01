import logging

import requests

from patent.application.conf.const import build_list_assoc_docs_uri
from patent.application.provider.util import raise_error
from patent.pgpub.model.pgpub_metadata import PgpubMetadata
from patent.pgpub.mapper.pgpub_metadata_mapper import PgpubMetadataMapper

logger = logging.getLogger(__name__)


class PgpubMetadataProvider:

    def __init__(self, pgpub_metadata_mapper: PgpubMetadataMapper, api_key: str):
        self.pgpub_metadata_mapper = pgpub_metadata_mapper
        self.base_headers = {
            "Accept": "application/json",
            "x-api-key": api_key,
        }

    def list_assoc_documents(
        self, application_number_text: str
    ) -> list[PgpubMetadata] | None:
        """
        List pgpub metadata of the given application's associated files
        See, https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
        """
        if application_number_text is None:
            return None

        assoc_doc_uri = build_list_assoc_docs_uri(application_number_text)
        logger.info(f"{assoc_doc_uri}")
        response = requests.get(assoc_doc_uri, headers=self.base_headers)

        if response.status_code == 200:
            content = response.content.decode("utf-8")
            pgpub_metadata = self.pgpub_metadata_mapper.map(content)
            if pgpub_metadata is None:
                return None
            logger.info(
                f"found {len(pgpub_metadata)} associated document pgpub metadata"
            )
            return pgpub_metadata
        else:
            content = response.content.decode("utf-8")
            raise_error(response.status_code, response.reason, content)
