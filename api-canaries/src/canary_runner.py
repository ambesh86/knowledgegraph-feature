import logging

from canaries.canary_base import CanaryBase
from metrics.canary_metrics_provider import CanaryMetricsProvider
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class CanaryRunner:

    def __init__(
        self,
        endpoint_host: str,
        runners: list[CanaryBase],
        metrics_provider: CanaryMetricsProvider,
    ):
        self.endpoint_host = endpoint_host
        self.runners = runners
        self.metrics_provider = metrics_provider

    @log_time
    def execute_runners(self) -> bool:
        fail_endpoints = []
        success_endpoints = []
        for runner in self.runners:
            logger.info(f"testing endpoint {runner.endpoint_name()}")
            is_success = runner.run()
            logger.info(
                f"test endpoint {runner.endpoint_name()} was successful: {is_success}"
            )

            if is_success:
                success_endpoints.append(runner.endpoint_name())
            else:
                fail_endpoints.append(runner.endpoint_name())

        logger.info(f"{len(success_endpoints)} endpoint canaries succeeded")
        logger.info(f"{len(fail_endpoints)} endpoint canaries failed")

        self._write_metrics(
            success_endpoints=success_endpoints, fail_endpoints=fail_endpoints
        )
        return len(fail_endpoints) <= 0

    @log_time
    def _write_metrics(
        self, success_endpoints: list[str], fail_endpoints: list[str]
    ) -> None:
        for success_endpoint in success_endpoints:
            self.metrics_provider.update_success_metrics_count(
                endpoint_name=success_endpoint
            )

        for fail_endpoint in fail_endpoints:
            self.metrics_provider.update_failed_metrics_count(
                endpoint_name=fail_endpoint
            )

        logger.info(
            f"wrote {len(success_endpoints)} success metrics and {len(fail_endpoints)} failure metrics"
        )
