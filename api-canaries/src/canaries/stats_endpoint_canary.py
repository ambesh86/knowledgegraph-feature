import logging
from typing import Any

from canaries.canary_base import CanaryBase
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class StatsEndpointCanary(CanaryBase):

    def __init__(self, host_and_protocol: str):
        url = f"{host_and_protocol}/stats"
        super().__init__(endpoint_name="Stats Endpoint", endpoint=url)
        self.expected_min = {
            "node_count": 400_000,
            "relationship_count": 7_000_000,
            "drug_count": 4_600,
            "disease_count": 17_000,
            "gene_protein_count": 27_000,
        }

    @log_time
    def run(self) -> bool:
        try:
            payload = self.get_request()
            if payload is None:
                return False
            return self._verify(payload)
        except Exception as e:
            logger.info("An error occurred:", e)
            return False

    def _verify(self, payload: dict[str, Any]) -> bool:
        if payload is None:
            return False
        all_present = self._verify_all_present(set(self.expected_min.keys()), payload)
        if not all_present:
            return False

        all_counts_pass = self._verify_all_min(
            expected_minimums=self.expected_min, payload=payload
        )
        return all_counts_pass

    def _verify_all_min(
        self, expected_minimums: dict[str, int], payload: dict[str, Any]
    ) -> bool:
        for key in expected_minimums.keys():
            expected_min = expected_minimums[key]
            is_success = self._verify_expected_min(
                key=key, expected_min=expected_min, payload=payload
            )
            if not is_success:
                return False

        return True
