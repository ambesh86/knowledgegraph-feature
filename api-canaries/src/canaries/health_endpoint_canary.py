import logging
from typing import Any

from canaries.canary_base import CanaryBase
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class HealthEndpointCanary(CanaryBase):

    def __init__(self, host_and_protocol: str):
        url = f"{host_and_protocol}/health"
        super().__init__(endpoint_name="Health Endpoint", endpoint=url)

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
        logger.debug(f"payload: {payload}")
        if "status" not in payload:
            return False

        status_msg = payload["status"]
        if status_msg == "OK":
            return True
        return False
