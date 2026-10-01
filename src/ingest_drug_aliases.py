from argparse import Namespace
import logging

from dotenv import load_dotenv

from foundation.conf.conf import (
    drug_aliases_update_orchestrator,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    args = arg_parser()
    load_dotenv()

    drug_update_orchestrator = drug_aliases_update_orchestrator()
    drug_update_orchestrator.update(
        product_names_csv=args.product_names_csv, synonyms_csv=args.synynoms_csv
    )


def arg_parser() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Add drug alias data to euGENE")
    parser.add_argument(
        "--product-names-csv",
        default="resources/data/drug/eugene_drug_productnames.csv",
        required=False,
        help="drug product names csv",
    )
    parser.add_argument(
        "--synynoms-csv",
        default="resources/data/drug/eugene_drug_synonyms.csv",
        required=False,
        help="drug synonym csv",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
