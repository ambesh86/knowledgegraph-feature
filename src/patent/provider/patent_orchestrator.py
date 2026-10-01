import logging
from pathlib import Path

from patent.application.provider.application_orchestrator import ApplicationOrchestator
from patent.pgpub.provider.pgpub_orchestrator import PgpubOrchestrator
from patent.pgpub.writer.json_writer import JsonWriter as PgpubJsonWriter
from patent.application.writer.json_writer import JsonWriter


logger = logging.getLogger(__name__)


class PatentOrchestrator:

    def __init__(
        self,
        application_orchestrator: ApplicationOrchestator,
        pgpub_orchestrator: PgpubOrchestrator,
        application_json_writer: JsonWriter,
        pgpub_json_writer: PgpubJsonWriter,
    ):
        self.application_orchestrator = application_orchestrator
        self.pgpub_orchestrator = pgpub_orchestrator
        self.application_json_writer = application_json_writer
        self.pgpub_json_writer = pgpub_json_writer

    def download(
        self, max_applications: int = 25, prefix_path: Path = Path("/tmp")
    ) -> None:
        applications = self.application_orchestrator.fetch_theraputic_areas(
            max_applications
        )

        if applications is None:
            logger.warning(f"found no applications. moving on...")

        self.application_json_writer.write(applications=applications, path=prefix_path)

        application_numbers = [
            application.application_number_text
            for application in applications
            if application.application_number_text is not None
        ]
        pgpubs = self.pgpub_orchestrator.fetch(
            application_numbers=application_numbers,
        )

        if pgpubs is None:
            logger.warning(f"no pgpubs found")

        self.pgpub_json_writer.write(pgpubs=pgpubs, path=prefix_path)

    def process(
        self, max_applications: int = 25, with_analysis_and_linking: bool = True
    ) -> None:
        applications = self.application_orchestrator.fetch_and_store_theraputic_areas(
            max_applications
        )

        if applications is None:
            logger.warning(f"found no applications. moving on...")
        self.pgpub_orchestrator.process(
            applications=applications,
            with_analysis_and_linking=with_analysis_and_linking,
        )
