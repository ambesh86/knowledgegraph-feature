import logging
from typing import Any
import boto3
import datetime

logger = logging.getLogger(__name__)


class CanaryMetricsProvider:
    NAMESPACE = "CSL/euGENE"
    SUCCESS_METRIC_NAME = "SuccessfulCanaries"
    UNSUCCESSFUL_METRIC_NAME = "UnsuccessfulCanaries"
    METRIC_UNIT = "Count"

    def __init__(self, system_name: str, env: str):
        self.client = boto3.client("cloudwatch")
        self.system_name = system_name
        self.env = env

    def update_failed_metrics_count(self, endpoint_name: str, value: int = 1):
        metrics_data = self._build_metrics_data(
            value=value, endpoint_name=endpoint_name, is_success_count=False
        )
        self._put_metric(metrics_data=metrics_data)

    def update_success_metrics_count(self, endpoint_name: str, value: int = 1):
        metrics_data = self._build_metrics_data(
            value=value, endpoint_name=endpoint_name, is_success_count=True
        )
        self._put_metric(metrics_data=metrics_data)

    def _build_metrics_data(
        self, value: int, endpoint_name: str, is_success_count: bool = False
    ) -> dict[str, Any]:
        metric_data = self._build_metrics(
            value=value, is_success_count=is_success_count
        )
        metric_data["Dimensions"] = self._build_dimensions(endpoint_name=endpoint_name)
        return metric_data

    def _build_metrics(
        self, value: int, is_success_count: bool = False
    ) -> dict[str, Any]:
        metric_name = (
            CanaryMetricsProvider.SUCCESS_METRIC_NAME
            if is_success_count
            else CanaryMetricsProvider.UNSUCCESSFUL_METRIC_NAME
        )
        metric_data = {
            "MetricName": metric_name,
            "Timestamp": datetime.datetime.now(datetime.timezone.utc),
            "Value": value,
            "Unit": CanaryMetricsProvider.METRIC_UNIT,
        }
        return metric_data

    def _build_dimensions(self, endpoint_name: str) -> list[dict[str, str]]:
        return [
            {"Name": "EndpointName", "Value": endpoint_name},
            {"Name": "SystemName", "Value": self.system_name},
            {"Name": "Environment", "Value": self.env},
        ]

    def _put_metric(self, metrics_data: dict[str, str | int]) -> None:
        try:
            response = self.client.put_metric_data(
                Namespace=CanaryMetricsProvider.NAMESPACE, MetricData=[metrics_data]
            )
            logger.info(f"Successfully put metric data: {response}")
        except Exception as e:
            logger.warning(f"Error putting metric data: {e}")
