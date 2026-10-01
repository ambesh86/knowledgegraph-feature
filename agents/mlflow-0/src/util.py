from argparse import Namespace
import argparse
import logging

logger = logging.getLogger(__name__)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        description="Run specific processing tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available items:
  organization_resolution - Resolve organization information
  organization_verification - Verify organization details
  on_topic                 - Process on-topic content

Examples:
  %(prog)s --items organization_resolution ontopic
  %(prog)s --items organization_resolution organization_verification on_topic
  %(prog)s --items all
        """,
    )
    parser.add_argument(
        "--items",
        nargs="+",
        choices=[
            "organization_resolution",
            "organization_verification",
            "on_topic",
            "all",
        ],
        required=True,
        help='Specify one or more items to run (use "all" to run all items)',
        metavar="ITEM",
    )
    return parser.parse_args()


def parse_items_to_run(args: Namespace) -> list[str]:
    if "all" in args.items:
        items_to_run = [
            "organization_resolution",
            "organization_verification",
            "on_topic",
        ]
    else:
        items_to_run = args.items

    logger.info("Running the following items:")
    for item in items_to_run:
        logger.info(f"  - {item}")
    return items_to_run
