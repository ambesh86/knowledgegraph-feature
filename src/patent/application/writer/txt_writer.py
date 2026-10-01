import datetime
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TxtWriter:

    def write(self, applications: list[dict[str, Any]], out_path_base: Path) -> None:
        """
        Writes txt representation of application docs
        """
        if applications is None:
            logger.warning("no application files to write. moving on...")

        num_applications = len(applications)
        logger.info(f"writing {num_applications} file(s)")

        for application in applications:
            logger.debug(f"{application}")
            application_number_text = application["application_number_text"]
            with open(
                out_path_base / f"{application_number_text}.txt",
                "w",
                newline="",
            ) as file:
                logger.debug(f"writing {file.name}")
                lines = self._map_to_lines(application=application)
                file.writelines(lines)

        logger.info("done writing files")

    def _map_to_lines(self, application: dict[str, Any]) -> list[str]:
        if application is None:
            return []

        application_number_text = application["application_number_text"]
        invention_title = (
            application["invention_title"] if "invention_title" in application else ""
        )
        first_applicant_name = (
            application["first_applicant_name"]
            if "first_applicant_name" in application
            else ""
        )
        applicants = application["applicants"] if "applicants" in application else set()
        application_status_description_text = (
            application["application_status_description_text"]
            if "application_status_description_text" in application
            else ""
        )
        application_status_code = (
            application["application_status_code"]
            if "application_status_code" in application
            else None
        )
        customer_number = (
            application["customer_number"] if "customer_number" in application else None
        )
        application_type_code = (
            application["application_type_code"]
            if "application_type_code" in application
            else ""
        )
        application_type_label_name = (
            application["application_type_label_name"]
            if "application_type_label_name" in application
            else ""
        )
        cpc_classifications = (
            application["cpc_classifications"]
            if "cpc_classifications" in application
            else set()
        )
        application_status_date = (
            application["application_status_date"]
            if "application_status_date" in application
            else datetime.datetime.now()
        )
        effective_filing_date = (
            application["effective_filing_date"]
            if "effective_filing_date" in application
            else datetime.datetime.now()
        )
        filing_date = (
            application["filing_date"]
            if "filing_date" in application
            else datetime.datetime.now()
        )
        patent_number = (
            application["patent_number"] if "patent_number" in application else None
        )
        grant_date = application["grant_date"] if "grant_date" in application else None

        lines = [
            f"application_number_text: {application_number_text}",
            f"invention title: {invention_title}",
            f"first applicant name: {first_applicant_name}",
            f"applications: {applicants}",
            f"application status description text: {application_status_description_text}",
            f"application status code: {application_status_code}",
            f"customer_number: {customer_number}",
            f"application type code: {application_type_code}",
            f"application type label name: {application_type_label_name}",
            f"cpc_classifications: {cpc_classifications}",
            f"application status date: {application_status_date}",
            f"effective filing date: {effective_filing_date}",
            f"filing date: {filing_date}",
            f"patent number: {patent_number}",
            f"grant_date: {grant_date}",
        ]

        return [line + "\n" for line in lines]
