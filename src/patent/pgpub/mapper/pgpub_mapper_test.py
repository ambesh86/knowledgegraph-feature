import logging
import unittest

import pytest

from patent.pgpub.mapper.pgpub_mapper import PgpubMapper
from patent.pgpub.model.pgpub_metadata import PgpubMetadata


logger = logging.getLogger(__name__)


class PgpubMapperTest(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def _pgpub_us18045436(self, pgpub_us18045436: bytes) -> None:
        self.pgpub_us18045436 = pgpub_us18045436

    @pytest.fixture(autouse=True)
    def _pgpub_metadata(self, pgpub_metadata_us18045436: PgpubMetadata) -> None:
        self.pgpub_metadata = pgpub_metadata_us18045436

    @pytest.fixture(autouse=True)
    def _pgpub_mapper(self, pgpub_mapper: PgpubMapper):
        self.pgpub_mapper = pgpub_mapper

    def test_sanity(self):
        assert self.pgpub_mapper is not None
        assert self.pgpub_us18045436 is not None
        assert self.pgpub_metadata is not None

    def test_when_map_then_return(self):
        pgpub = self.pgpub_mapper.map(self.pgpub_metadata, self.pgpub_us18045436)
        logger.info(f"{pgpub}")

        assert pgpub is not None
        metadata = pgpub.pgpub_metadata
        assert metadata is not None
        assert metadata.application_number_text == "18045436"
        assert metadata.file_create_dtg.isoformat() == "2022-10-10T00:00:00"
        assert (
            metadata.file_location_uri
            == "https://api.uspto.gov/api/v1/datasets/products/files/APPXML-SPLT/2023/ipa231116/18045436_20230366018.xml"
        )

        assert pgpub.abstract.startswith(
            "Labeled nucleotide analogs comprising at least one avidin protein"
        )
        assert pgpub.description is not None
        found_last_description = -1 != pgpub.description[-1].find(
            "The scope of the invention should, therefore, be determined by reference"
        )
        assert found_last_description
        assert len(pgpub.description) == 1858
        assert pgpub.claims is not None and len(pgpub.claims) == 229

        assert pgpub.organizations is not None
        assert len(pgpub.organizations) == 1
        assert "Pacific Biosciences of California, Inc." in pgpub.organizations

        assert pgpub.chemical_compound_synonyms == None
