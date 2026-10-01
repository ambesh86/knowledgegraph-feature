from datetime import datetime
import json
import logging
from typing import Any

from patent.application.model.application import Application

logger = logging.getLogger(__name__)


class ApplicationMapper:
    """
    Class will parse the response of the uspto patent payload
    """

    def map(
        self,
        json_payload: str,
    ) -> list[Application]:
        if json_payload is None:
            return None

        applications = []
        try:
            parsed = json.loads(json_payload)
            items = parsed["patentFileWrapperDataBag"]
            for item in items:
                application = self.map_application(item)
                applications.append(application)
        except json.JSONDecodeError as e:
            logger.warning(f"ignoring json parse error: {e}")
            raise e

        return applications

    def map_application(
        self,
        payload: dict[str, Any],
    ) -> Application | None:
        if payload is None:
            return None

        logger.debug(f"payload = {payload}")
        metadata = (
            payload["applicationMetaData"] if "applicationMetaData" in payload else None
        )
        if metadata is None:
            return None

        application_number_text = self._map_or_default(payload, "applicationNumberText")
        patent_number = (
            int(metadata["patentNumber"]) if "patentNumber" in metadata else None
        )
        invention_title = metadata["inventionTitle"]
        first_applicant_name = self._map_or_default(metadata, "firstApplicantName")
        application_status_description_text = metadata[
            "applicationStatusDescriptionText"
        ]
        application_status_code = int(metadata["applicationStatusCode"])
        customer_number = (
            int(metadata["customerNumber"]) if "customerNumber" in metadata else None
        )
        application_type_code = metadata["applicationTypeCode"]
        application_type_label_name = metadata["applicationTypeLabelName"]
        cpc_classifications_bag = (
            metadata["cpcClassificationBag"]
            if "cpcClassificationBag" in metadata
            else ""
        )
        cpc_classifications = self._map_cpc_classifications(cpc_classifications_bag)
        applicants = self._map_applications(
            self._map_list_or_default(metadata, "applicantBag")
        )
        application_status_date = self._map_datetime(metadata["applicationStatusDate"])
        effective_filing_date = (
            self._map_datetime(metadata["effectiveFilingDate"])
            if "effectiveFilingDate" in metadata
            else None
        )
        filing_date = self._map_datetime(metadata["filingDate"])
        grant_date = (
            self._map_datetime(metadata["grantDate"])
            if "grantDate" in metadata
            else None
        )
        application = Application(
            application_number_text=application_number_text,
            invention_title=invention_title,
            first_applicant_name=first_applicant_name,
            applicants=applicants,
            application_status_description_text=application_status_description_text,
            application_status_code=application_status_code,
            customer_number=customer_number,
            application_type_code=application_type_code,
            application_type_label_name=application_type_label_name,
            cpc_classifications=cpc_classifications,
            application_status_date=application_status_date,
            effective_filing_date=effective_filing_date,
            filing_date=filing_date,
            patent_number=patent_number,
            grant_date=grant_date,
        )
        logger.debug(f"Mapped application: {application}")

        return application

    def _map_applications(self, applicants: list[dict] | None) -> set[str] | None:
        if applicants is None:
            return None
        applicationNames = set()
        for applicantItem in applicants:
            applicantName = self._map_or_default(applicantItem, "applicantNameText")
            applicationNames.add(applicantName)

        return applicationNames

    def _map_cpc_classifications(self, json: str) -> set[str]:
        return self._map_to_set(json)

    def _map_or_default(
        self, json: dict[str, Any], key: str, default_value=None
    ) -> str | None:
        return json[key] if key in json else default_value

    def _map_list_or_default(
        self, json: dict[str, Any], key: str, default_value=None
    ) -> list[Any] | None:
        return json[key] if key in json else default_value

    def _map_to_set(self, items) -> set[str]:
        uniq = set()
        for item in items:
            uniq.add(item)
        return uniq

    def _map_datetime(self, datetime_str: str) -> datetime:
        return datetime.strptime(datetime_str, "%Y-%m-%d")
