import datetime
import json
import logging
from typing import Any


from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.model.pgpub_metadata import PgpubMetadata

logger = logging.getLogger(__name__)


class PgpubJsonDecoder(json.JSONDecoder):

    def default(self, contents: dict[str, Any]) -> Pgpub:
        logger.info("in pgpub decoder")
        # application_number_text: str,
        # abstract: str,
        # pgpub_metadata: PgpubMetadata,
        # description: list[str] | None,
        # claims: list[str] | None,
        # organizations: set[str] | None,
        # chemical_compound_synonyms: set[str] | None = None,
        # embeddings: ndarray | None = None,
        application_number_text = (
            contents["application_number_text"]
            if "application_number_text" in contents
            else ""
        )
        abstract = contents["abstract"] if "abstract" in contents else ""
        claims = contents["claims"] if "claims" in contents else []
        chemical_compound_synonyms = (
            contents["chemical_compound_synonyms"]
            if "chemical_compound_synonyms" in contents
            else None
        )
        description = contents["description"] if "description" in contents else []
        organizations = (
            contents["organizations"] if "organizations" in contents else None
        )
        pgpub_metadata = (
            contents["pgpub_metadata"] if "pgpub_metadata" in contents else {}
        )
        metadata_application_number = (
            pgpub_metadata["application_number_text"]
            if "application_number_text" in pgpub_metadata in pgpub_metadata
            else ""
        )
        file_create_dtg = (
            pgpub_metadata["file_create_dtg"]
            if "file_create_dtg" in pgpub_metadata in pgpub_metadata
            else datetime.datetime.now()
        )
        file_location_uri = (
            pgpub_metadata["file_location_uri"]
            if "file_location_uri" in pgpub_metadata in pgpub_metadata
            else ""
        )

        return Pgpub(
            application_number_text=application_number_text,
            abstract=abstract,
            claims=claims,
            chemical_compound_synonyms=chemical_compound_synonyms,
            description=description,
            pgpub_metadata=PgpubMetadata(
                application_number_text=metadata_application_number,
                file_location_uri=file_location_uri,
                file_create_dtg=file_create_dtg,
            ),
            organizations=organizations,
        )
