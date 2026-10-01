import logging
from typing import Any

from canaries.canary_base import CanaryBase
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class NodeFindEndpointCanary(CanaryBase):

    def __init__(self, host_and_protocol: str):
        url = f"{host_and_protocol}/node/find"
        super().__init__(endpoint_name="Node Find Endpoint", endpoint=url)
        self.expected_fields = {"results", "count", "query", "fuzzy_match"}
        self.expected_minimums = {
            "count": 2,
        }
        self.term = "Flurandrenolide"

    @log_time
    def run(self) -> bool:
        fuzzy_match = False
        fuzzy = "true" if fuzzy_match else "false"
        endpoint = f"{self._endpoint}/{self.term}?fuzzy_match={fuzzy}"
        is_success = self._fetch_request(endpoint=endpoint)
        if not is_success:
            return False

        return True

    def _fetch_request(self, endpoint: str) -> bool:
        try:
            payload = self.get_request(endpoint)
            if payload is None:
                return False
            return self._verify(payload=payload)
        except Exception as e:
            logger.info("An error occurred:", e)
            return False

    def _verify(self, payload: dict[str, Any]) -> bool:
        if payload is None:
            return False
        all_present = self._verify_all_present(self.expected_fields, payload)
        if not all_present:
            return False

        count_field = "count"
        all_counts_pass = self._verify_expected_min(
            key=count_field,
            expected_min=self.expected_minimums[count_field],
            payload=payload,
        )
        if not all_counts_pass:
            return False

        is_valid_query = payload["query"] == self.term
        is_valid_fuzzy_match = payload["fuzzy_match"] == False
        results = payload["results"]
        result_0 = results[0]
        is_valid_result_0 = (
            result_0["id"] == "DB00846" and result_0["value"] == self.term
        )
        return is_valid_query and is_valid_fuzzy_match and is_valid_result_0
