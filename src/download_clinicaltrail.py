import json
import logging
from clinicaltrail.provider.clinical_trail_provider import ClinicalTrailProvider
from clinicaltrail.mapper.clinical_trail_mapper import ClinicalTrailMapper

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Download clinical trial data")
    parser.add_argument("--drug", required=False, help="Drug name to search for")
    parser.add_argument(
        "--disease", required=False, help="Disease/condition to search for"
    )
    parser.add_argument(
        "--output", default="clinical_trials.csv", help="Output CSV file path"
    )

    args = parser.parse_args()

    provider = ClinicalTrailProvider(clinical_trial_mapper=ClinicalTrailMapper())

    # version_dict = provider.get_version()
    # logger.info(type(version_dict))
    # logger.info(f"{version_dict}")

    # drug_studies = provider.find_studies_by_drug_as_json(args.drug)
    # logger.info("---- drug studies")
    # print_studies_resp(drug_studies)

    # disease_studies = provider.find_studies_by_disease_as_json(args.disease)
    # logger.info("---- disease studies")
    # print_studies_resp(disease_studies)

    # drug_csv = provider.find_studies_by_drug_as_csv(args.drug)
    # logger.info("---- drug csv")
    # logger.info(type(drug_csv))
    # logger.info(f"{len(drug_csv)}")
    # logger.info(f"{drug_csv[0]}")

    disease_csv = provider.find_studies_by_disease_as_csv(args.disease)
    logger.info("---- disease csv")
    logger.info(type(disease_csv))
    logger.info(f"{len(disease_csv)}")
    for row in disease_csv[0:5]:
        logger.info(f"{row}")


def print_studies_resp(studies: list[dict]) -> None:
    logger.info(type(studies))
    logger.info("---- studies")
    logger.info(f"{len(studies)} studies")
    logger.info(f"first study {json.dumps(studies[0], indent=4)}")


if __name__ == "__main__":
    main()
