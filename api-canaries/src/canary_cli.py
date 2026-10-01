import argparse
import logging
import sys

from const import DIFFLABS_HOSTNAME, URL_BASE_MAP
from canary_runner import CanaryRunner
from canaries.canary_base import CanaryBase
from canaries.health_endpoint_canary import HealthEndpointCanary
from canaries.stats_endpoint_canary import StatsEndpointCanary
from canaries.label_counts_endpoint_canary import LabelCountsEndpointCanary
from canaries.node_find_endpoint_canary import NodeFindEndpointCanary
from canaries.node_details_endpoint_canary import NodeDetailsEndpointCanary
from metrics.canary_metrics_provider import CanaryMetricsProvider

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = _args_parser()
    args = parser.parse_args()
    url_base = _determine_endpoint(args)
    runners = _build_runners(url_base)
    metrics_provider = CanaryMetricsProvider(
        system_name=_args_to_system_name(args), env=_args_to_env(args)
    )
    canary_runner = CanaryRunner(
        endpoint_host=DIFFLABS_HOSTNAME,
        runners=runners,
        metrics_provider=metrics_provider,
    )
    is_run_success = canary_runner.execute_runners()
    logger.info(f"run was successful: {is_run_success}")
    exit_code = 0 if is_run_success else 1
    sys.exit(exit_code)


def _determine_endpoint(args: argparse.Namespace) -> str:
    environment = _args_to_env(args)
    endpoint = _args_to_system_name(args)
    url_base = URL_BASE_MAP[f"{environment}_{endpoint}"]
    return url_base


def _args_to_env(args: argparse.Namespace) -> str:
    environment = str(args.env).upper()
    return environment


def _args_to_system_name(args: argparse.Namespace) -> str:
    endpoint = "DIFFLABS" if args.difflabs else "AIA"
    return endpoint


def _build_runners(url_base: str) -> list[CanaryBase]:
    return [
        HealthEndpointCanary(url_base),
        StatsEndpointCanary(url_base),
        LabelCountsEndpointCanary(url_base),
        NodeFindEndpointCanary(url_base),
        NodeDetailsEndpointCanary(url_base),
    ]


def _args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="euGENE API Canaries",
    )

    endpoint_action_group = parser.add_mutually_exclusive_group(required=True)
    endpoint_action_group.add_argument(
        "--difflabs", action="store_true", help="Test diffusionlabs endpoints"
    )
    endpoint_action_group.add_argument(
        "--aia", action="store_true", help="Test AI accelerator endpoints"
    )

    parser.add_argument(
        "--env",
        type=str,
        default="staging",
        choices=["staging", "prod"],
        help="Specify the application environment (staging or prod).",
    )
    return parser


if __name__ == "__main__":
    main()
