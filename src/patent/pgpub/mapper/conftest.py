from datetime import datetime
from pathlib import Path
import pytest

from patent.pgpub.mapper.pgpub_metadata_mapper import PgpubMetadataMapper
from patent.pgpub.mapper.pgpub_mapper import PgpubMapper
from patent.pgpub.model.pgpub_metadata import PgpubMetadata

PATENT_PGPUBMETADATA_TEST_DATA = "tests/data/patent/application/pgpub_metadata"


@pytest.fixture(scope="class")
def patent_application_associated_documents_json() -> str:
    return """{
  "count": 1,
  "patentFileWrapperDataBag": [
    {
      "applicationNumberText": "18045436",
      "grantDocumentMetaData": {
        "productIdentifier": "PTGRXML",
        "zipFileName": "ipg240604.zip",
        "fileCreateDateTime": "2024-09-30T17:48:45",
        "xmlFileName": "18045436_12000000.xml",
        "fileLocationURI": "https://api.uspto.gov/api/v1/datasets/products/files/PTGRXML-SPLT/2024/ipg240604/18045436_12000000.xml"
      },
      "pgpubDocumentMetaData": {
        "productIdentifier": "APPXML",
        "zipFileName": "ipa231116.zip",
        "fileCreateDateTime": "2024-09-30T11:13:08",
        "xmlFileName": "18045436_20230366018.xml",
        "fileLocationURI": "https://api.uspto.gov/api/v1/datasets/products/files/APPXML-SPLT/2023/ipa231116/18045436_20230366018.xml"
      }
    }
  ],
  "requestIdentifier": "a0020348-2715-4696-a931-05042ae94be6"
}"""


@pytest.fixture(scope="class")
def pgpub_us18045436() -> bytes:
    doc_name = "us18045436.xml"
    doc_path = Path(PATENT_PGPUBMETADATA_TEST_DATA) / doc_name
    return Path(doc_path).read_bytes()


@pytest.fixture(scope="class")
def pgpub_metadata_us18045436() -> PgpubMetadata:
    return PgpubMetadata(
        application_number_text="18045436",
        file_location_uri="https://api.uspto.gov/api/v1/datasets/products/files/APPXML-SPLT/2023/ipa231116/18045436_20230366018.xml",
        file_create_dtg=datetime.strptime("20221010", "%Y%m%d"),
    )


@pytest.fixture(scope="class")
def pgpub_metadata_mapper() -> PgpubMetadataMapper:
    return PgpubMetadataMapper()


@pytest.fixture(scope="class")
def pgpub_mapper() -> PgpubMapper:
    return PgpubMapper()
