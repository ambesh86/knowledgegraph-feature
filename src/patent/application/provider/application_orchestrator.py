import logging
from time import sleep
from typing import Callable

from patent.application.infra.db.neo4j_application_adapter import (
    Neo4jApplicationAdapter,
)
from patent.application.provider.application_provider import ApplicationProvider
from patent.application.model.application import Application

logger = logging.getLogger(__name__)


class ApplicationOrchestator:
    def __init__(
        self,
        application_adapter: Neo4jApplicationAdapter,
        application_provider: ApplicationProvider,
    ):
        self.application_adapter = application_adapter
        self.application_provider = application_provider

    def fetch_theraputic_areas(
        self, max_applications_per_area: int = 25
    ) -> list[Application]:
        applications = []
        hematology_applications = self._download_hematology(max_applications_per_area)
        if hematology_applications is not None:
            applications.extend(hematology_applications)

        sleep(45)
        cardio_applications = self._download_cardio(max_applications_per_area)
        if cardio_applications is not None:
            applications.extend(cardio_applications)

        sleep(45)
        transplant_applications = self._download_transplant(max_applications_per_area)
        if transplant_applications is not None:
            applications.extend(transplant_applications)

        sleep(45)
        immunoglobulin_applications = self._download_immunoglobulin(
            max_applications_per_area
        )
        if immunoglobulin_applications is not None:
            applications.extend(immunoglobulin_applications)

        if applications is None or len(applications) < 1:
            logger.info(f"no applications found to ingest. Moving on...")
            return []
        return applications

    def fetch_and_store_theraputic_areas(
        self, max_applications_per_area: int = 25
    ) -> list[Application]:
        applications = self.fetch_theraputic_areas(
            max_applications_per_area=max_applications_per_area
        )
        self._ingest(applications=applications)
        return applications

    def load(self, max_applications: int = 25) -> list[Application]:
        applications = self._download(max_applications=max_applications)
        if applications is None:
            logger.info(f"no applications found to ingest. Moving on...")
            return []
        self._ingest(applications=applications)
        return applications

    def _ingest(self, applications: list[Application]) -> None:
        error_count = 0
        for application in applications:
            try:
                self.application_adapter.upsert(application=application)
            except Exception as e:
                logger.warning(
                    f"Error upserting {application.application_number_text} error: {e}"
                )
                error_count += 1

        num_applications = len(applications)
        logger.info(f"upserted {(num_applications - error_count)}/{num_applications}")

    def _download(self, max_applications: int) -> list[Application] | None:
        return self._step(
            max_applications=max_applications,
            work=self.application_provider.search_medical_patent_applications,
        )

    def _download_hematology(self, max_applications: int) -> list[Application] | None:
        return self._step(
            max_applications=max_applications,
            work=self.application_provider.search_hematology_threaputic_area_applications,
        )

    def _download_transplant(self, max_applications: int) -> list[Application] | None:
        return self._step(
            max_applications=max_applications,
            work=self.application_provider.search_transplant_threaputic_area_applications,
        )

    def _download_cardio(self, max_applications: int) -> list[Application] | None:
        return self._step(
            max_applications=max_applications,
            work=self.application_provider.search_cardiovascular_threaputic_area_applications,
        )

    def _download_immunoglobulin(
        self, max_applications: int
    ) -> list[Application] | None:
        return self._step(
            max_applications=max_applications,
            work=self.application_provider.search_immunoglobulin_threaputic_area_applications,
        )

    def _step(
        self,
        max_applications: int,
        work: Callable[[int | None, int | None], list[Application] | None],
    ) -> list[Application]:
        DEFAULT_STEP_SIZE = 10
        step_size = (
            DEFAULT_STEP_SIZE
            if max_applications > DEFAULT_STEP_SIZE
            else max_applications
        )
        logger.info(f"max_apps = {max_applications}")
        stepper = range(0, max_applications, step_size)
        applications = []
        sleep_secs = 10
        for step in stepper:
            limit = (
                (step + step_size)
                if (step + step_size) < stepper.stop
                else stepper.stop
            )
            logger.info(f"step={step} limit={limit}")
            logger.info(f"sleeping for {sleep_secs} secs")
            sleep(sleep_secs)
            current_batch = work(limit, step)
            if current_batch is not None:
                applications.extend(current_batch)
        return applications
