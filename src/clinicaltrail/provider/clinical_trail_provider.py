import datetime
import logging
import pytz
import requests
import json

from clinicaltrail.mapper.clinical_trail_mapper import ClinicalTrailMapper

logger = logging.getLogger(__name__)


class ClinicalTrailProvider:
    """
    Class responsible for interacting with the ClinicalTrials.gov API.
    Try
    curl -X GET "https://clinicaltrials.gov/api/v2/version" -H "accept: application/json" | jq .
    """

    def __init__(self, clinical_trial_mapper: ClinicalTrailMapper):
        self.base_url = "https://clinicaltrials.gov/api/v2"
        self.base_headers = {"accept": "application/json"}
        # csv headers are different than json keys
        # see mapping, https://clinicaltrials.gov/data-api/about-api/csv-download
        self.csv_fields = "NCT Number,Start Date,Study URL,Study Title,Conditions,Interventions,Primary Outcome Measures"
        self.response_fields = (
            "NCTId,BriefTitle,Condition,InterventionName,OutcomeMeasure"
        )
        self.clinical_trial_mapper = clinical_trial_mapper

    def find_studies_by_disease_as_csv(
        self, disease: str, min_start_date: datetime = None
    ) -> list[dict]:
        """
        Fetches clinical trial studies based on disease (condition).
        Returns API response as csv.
        """
        params = self._base_csv_params(min_start_date)
        params["query.cond"] = disease
        return self._find_studies_as_csv(params)

    def find_studies_by_drug_as_csv(
        self, drug: str, min_start_date: datetime = None
    ) -> list[dict]:
        """
        Fetches clinical trial studies based on drug (intervention).
        Returns API response as csv.
        """
        params = self._base_csv_params(min_start_date)
        params["query.intr"] = drug
        return self._find_studies_as_csv(params)

    def find_studies_by_disease_as_json(self, disease: str) -> list[dict]:
        """
        Fetches clinical trial studies based on disease (condition).
        Returns API response as json.
        """
        if min_start_date is None:
            min_start_date = self._default_start_date()
        params = {
            "query.cond": disease,
            "fields": self.response_fields,
        }

        return self.find_studies(params)

    def find_studies_by_drug_as_json(self, drug: str) -> list[dict]:
        """
        Fetches clinical trial studies based on drug (intervention).
        Returns API response as json.
        """
        params = {
            "query.intr": drug,
            "fields": self.response_fields,
        }

        return self.find_studies(params)

    def find_studies(self, params: dict) -> list[dict]:
        """
        Fetches clinical trial studies based on given params.
        See, https://clinicaltrials.gov/data-api/api
        Returns API response as json.
        """

        response = requests.get(
            f"{self.base_url}/studies", params=params, headers=self.base_headers
        )

        if response.status_code == 200:
            return self.clinical_trial_mapper.map_studies_json(response.content)
        else:
            self._raise_error(response.status_code, response.reason)

    def _find_studies_as_csv(self, params: dict) -> list[str]:
        """
        Fetches clinical trial studies based on given params.
        See, https://clinicaltrials.gov/data-api/api
        Returns API response as csv.
        """

        # headers = {"accept": "text/csv; charset=utf-8"}
        csv_params = params.copy()
        csv_params["format"] = "csv"
        studies_url = f"{self.base_url}/studies"
        logger.info(f"{studies_url} {csv_params}")
        response = requests.get(
            studies_url, params=csv_params, headers=self.base_headers
        )

        all_rows = []
        if response.status_code == 200:
            csv = response.content.decode("utf-8")
            all_rows.extend(csv.splitlines())
        else:
            self._raise_error(response.status_code, response.reason)

        next_page_token_key = "x-next-page-token"
        if next_page_token_key in response.headers:
            next_page_token = response.headers[next_page_token_key]
            logger.debug(f"found next token {next_page_token}")
            next_params = params.copy()
            next_params["pageToken"] = next_page_token
            csv = self._find_studies_as_csv(next_params)
            all_rows.extend(csv)

        return all_rows

    def get_version(self) -> dict:
        """
        Fetches clinical trial api version
        """

        response = requests.get(f"{self.base_url}/version", headers=self.base_headers)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            self._raise_error(response.status_code)

    def _base_csv_params(self, min_start_date) -> dict:
        today = datetime.date.today()
        if min_start_date is None:
            min_start_date = today - datetime.timedelta(days=30)
        # "filter.advanced": f"AREA[StartDate]RANGE[MAX, {min_start_date}]",
        # AREA[StartDate]RANGE[MIN,2025-02-26] AND AREA[StartDate]RANGE[2025-01-03,MAX]
        params = {
            "fields": self.csv_fields,
            "filter.advanced": f"AREA[StartDate]RANGE[MIN,{today}] AND AREA[StartDate]RANGE[{min_start_date},MAX]",
            "pageSize": 25,
        }
        return params

    def _raise_error(self, status_code: int, reason: str) -> None:
        logger.warning(f"HTTP {status_code} {reason}")
        raise ValueError(
            f"API request failed with status code {status_code} Reason: {reason}"
        )
