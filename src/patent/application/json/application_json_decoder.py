import datetime
import json
import logging
from typing import Any


from patent.application.model.application import Application

logger = logging.getLogger(__name__)


class ApplicationJsonDecoder(json.JSONDecoder):

    def default(self, contents: dict[str, Any]) -> Application:
        logger.info("in application decoder")
        application_number_text = (
            contents["application_number_text"]
            if "application_number_text" in contents
            else ""
        )
        invention_title = (
            contents["invention_title"] if "invention_title" in contents else ""
        )
        first_applicant_name = (
            contents["first_applicant_name"]
            if "first_applicant_name" in contents
            else None
        )
        applicants = contents["applicants"] if "applicants" in contents else None
        application_status_description_text = (
            contents["application_status_description_text"]
            if "application_status_description_text" in contents
            else ""
        )
        application_status_code = (
            contents["application_status_code"]
            if "application_status_code" in contents
            else -1
        )
        customer_number = (
            contents["customer_number"] if "customer_number" in contents else None
        )
        application_type_code = (
            contents["application_type_code"]
            if "application_type_code" in contents
            else ""
        )
        application_type_label_name = (
            contents["application_type_label_name"]
            if "application_type_label_name" in contents
            else ""
        )
        cpc_classifications = (
            contents["cpc_classifications"]
            if "cpc_classifications" in contents
            else set()
        )
        application_status_date = (
            contents["application_status_date"]
            if "application_status_date" in contents
            else datetime.datetime.now()
        )
        effective_filing_date = (
            contents["effective_filing_date"]
            if "effective_filing_date" in contents
            else datetime.datetime.now()
        )
        filing_date = (
            contents["filing_date"]
            if "filing_date" in contents
            else datetime.datetime.now()
        )
        patent_number = (
            contents["patent_number"] if "patent_number" in contents else None
        )
        grant_date = contents["grant_date"] if "grant_date" in contents else None

        return Application(
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
