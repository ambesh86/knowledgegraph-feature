import logging
import unittest

import pytest

from patent.pgpub.mapper.pgpub_metadata_mapper import PgpubMetadataMapper


logger = logging.getLogger(__name__)


class PgpubMetadataMapperTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _list_pgpub_mapper(self, pgpub_metadata_mapper: PgpubMetadataMapper):
        self.pgpub_metadata_mapper = pgpub_metadata_mapper

    @pytest.fixture(autouse=True)
    def _patent_application_associated_documents_json(
        self, patent_application_associated_documents_json: str
    ):
        self.list_assoc_doc_json = patent_application_associated_documents_json

    def test_sanity(self):
        assert self.pgpub_metadata_mapper is not None
        assert self.list_assoc_doc_json is not None

    def test_when_map_then_return(self):
        pgpub_metadata = self.pgpub_metadata_mapper.map(self.list_assoc_doc_json)
        assert pgpub_metadata is not None
        assert len(pgpub_metadata) > 0
        logger.info(f"{pgpub_metadata}")
        head = pgpub_metadata[0]
        assert head.application_number_text == "18045436"
        assert head.file_create_dtg.isoformat() == "2024-09-30T11:13:08"
        assert (
            head.file_location_uri
            == "https://api.uspto.gov/api/v1/datasets/products/files/APPXML-SPLT/2023/ipa231116/18045436_20230366018.xml"
        )
