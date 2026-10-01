import logging

import requests

from patent.application.conf.const import USPTO_SEARCH_URI
from patent.application.mapper.application_mapper import ApplicationMapper
from patent.application.model.application import Application
from patent.application.provider.util import raise_error

logger = logging.getLogger(__name__)


class ApplicationProvider:

    def __init__(self, application_mapper: ApplicationMapper, api_key: str):
        self.application_mapper = application_mapper
        # step size 25 seems to work, a number too large will cause API fetch errors
        self.pagination = {"offset": 0, "limit": 25}
        self.sort_defaults = {
            "field": "applicationMetaData.filingDate",
            "order": "Desc",
        }
        self.base_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        self.pharam_query_terms = (
            '(drug OR pharmaceutical OR "therapeutic agent" OR biologic OR antibody)'
        )

    def search_vaccines_threaputic_area_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query theraptic area of vaccines
        """
        scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f"(vaccines) AND {self.pharam_query_terms} AND {scoped_clause}"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_transplant_threaputic_area_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query transplant and immunology area of vaccines
        """
        # reducing scope, since the query comes back empty
        # scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f"(transplant AND antigens) OR (transplant AND antibodies) OR (transplant AND lymphocytes) OR (transplant AND 'organ rejection')"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_cardiovascular_threaputic_area_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query cardiovascular area of vaccines
        """
        scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f"(cardiovascular OR renal) AND {scoped_clause}"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_immunoglobulin_threaputic_area_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query immunoglobulin area of vaccines
        """
        scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f"(immunoglobulin) AND {scoped_clause}"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_hematology_threaputic_area_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query hematology area of vaccines
        """
        scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f'(hematology OR anemia OR "blood cancers" OR hemoglobin OR "sickle cell disease" OR "von willebrand" OR hemophilia OR leukemia OR lymphoma OR myeloma) AND {scoped_clause}'
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_medical_patent_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query biomedical applications
        """
        scoped_clause = self._build_biomedical_code_clause()
        scoped_query = f"{self.pharam_query_terms} AND {scoped_clause}"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_pregrant_medical_patent_applications(
        self, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Query biomedical applications with pregranted status
        """
        scoped_clause = self._build_scoped_query()
        scoped_query = f"{self.pharam_query_terms} AND {scoped_clause}"
        return self.search_patent_applications(scoped_query, limit=limit, offset=offset)

    def search_patent_applications(
        self, query: str, limit: int | None, offset: int | None = 0
    ) -> list[Application] | None:
        """
        Search for applications with a pregrant application code
        See, https://www.uspto.gov/sites/default/files/documents/Appendix%20A.pdf
        """
        if query is None:
            return None

        post_params = self._build_post_params_with_defaults(
            query=query, limit=limit, offset=offset
        )
        logger.info(f"{USPTO_SEARCH_URI} {post_params}")
        response = requests.post(
            USPTO_SEARCH_URI, json=post_params, headers=self.base_headers
        )

        if response.status_code == 200:
            content = response.content.decode("utf-8")
            applications = self.application_mapper.map(content)
            logger.info(f"found {len(applications)} application(s)")
            return applications
        else:
            content = response.content.decode("utf-8")
            raise_error(response.status_code, response.reason, content)

    def _build_post_params_with_defaults(
        self, query: str, limit: int | None, offset: int | None = 0
    ) -> dict:
        pagination = self.pagination.copy()
        if offset is not None and offset > 0:
            logger.info(f"setting offset {offset}")
            pagination["offset"] = offset
        if limit is not None and limit > 0:
            logger.info(f"setting limit {limit}")
            pagination["limit"] = limit
        return {
            "q": query,
            "filters": [],
            "rangeFilters": [],
            "pagination": pagination,
            "sort": [self.sort_defaults.copy()],
        }

    def _build_scoped_query(self) -> str:
        biomedical_clause = self._build_biomedical_code_clause()
        pre_grant_clause = self._build_pre_grant_clause()
        return " AND ".join([biomedical_clause, pre_grant_clause])

    def _build_biomedical_code_clause(self) -> str:
        biomedical_classification_filter = (
            f"applicationMetaData.cpcClassificationBag:A61*"
        )
        return f"({biomedical_classification_filter})"

    def _build_pre_grant_clause(self) -> str:
        # grant code is 150
        pregrant_codes = [30, 17, 19]
        fragments = []
        for code in pregrant_codes:
            fragments.append(f"applicationMetaData.applicationStatusCode:{code}")
        all_codes = " OR ".join(fragments)
        return f"({all_codes})"
