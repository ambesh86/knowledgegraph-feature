import logging
from typing import Any

from canaries.canary_base import CanaryBase
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class NodeDetailsEndpointCanary(CanaryBase):

    def __init__(self, host_and_protocol: str):
        url = f"{host_and_protocol}/node/details"
        super().__init__(endpoint_name="Node Details Endpoint", endpoint=url)
        self.expected_fields = {"labels", "id", "value", "source"}
        self.request_ids = ["C031180"]

    @log_time
    def run(self) -> bool:
        is_success = self._fetch_request(
            endpoint=self._endpoint, request={"ids": self.request_ids}
        )
        if not is_success:
            return False

        return True

    def _fetch_request(self, endpoint: str, request: dict[str, Any]) -> bool:
        try:
            payload = self.post_request_for_list(endpoint, args=request)
            if payload is None:
                return False
            return self._verify(payload=payload)
        except Exception as e:
            logger.info("An error occurred:", e)
            return False

    def _verify(self, payload: list[dict[str, Any]]) -> bool:
        if payload is None:
            return False

        response0 = payload[0]
        all_present = self._verify_all_present(self.expected_fields, response0)
        if not all_present:
            return False

        has_valid_label = "exposure" in response0["labels"]
        has_valid_id = self.request_ids[0] == response0["id"]
        has_valid_source = "CTD" == response0["source"]
        has_valid_value = "chrysene" == response0["value"]
        return has_valid_label and has_valid_id and has_valid_source and has_valid_value
