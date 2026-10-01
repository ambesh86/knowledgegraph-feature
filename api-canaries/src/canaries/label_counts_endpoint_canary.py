import logging
from typing import Any

from canaries.canary_base import CanaryBase
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class LabelCountsEndpointCanary(CanaryBase):

    def __init__(self, host_and_protocol: str):
        url = f"{host_and_protocol}/count"
        super().__init__(endpoint_name="Label Count Endpoint", endpoint=url)
        self.expected_minimums = {
            "anatomy": 14_000,
            "molecular_function": 10_000,
            "pathway": 2_500,
        }

    @log_time
    def run(self) -> bool:
        for label in self.expected_minimums.keys():
            endpoint = f"{self._endpoint}/{label}"
            expected_min = self.expected_minimums[label]
            is_success = self._run_label(endpoint=endpoint, expected_min=expected_min)
            if not is_success:
                return False

        return True

    def _run_label(self, endpoint: str, expected_min: int) -> bool:
        try:
            payload = self.get_request(endpoint)
            if payload is None:
                return False
            return self._verify(expected_min=expected_min, payload=payload)
        except Exception as e:
            logger.info("An error occurred:", e)
            return False

    def _verify(self, expected_min: int, payload: dict[str, Any]) -> bool:
        if payload is None:
            return False
        all_present = self._verify_all_present({"count", "label"}, payload)
        if not all_present:
            return False

        all_counts_pass = self._verify_expected_min(
            key="count", expected_min=expected_min, payload=payload
        )
        return all_counts_pass
