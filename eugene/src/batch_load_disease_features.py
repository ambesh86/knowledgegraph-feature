import csv
import logging
import time
from dotenv import load_dotenv
from adapter.disease_feature_neo4j_adapter import DiseaseFeatureNeo4jAdapter
from helper.driver_helper import new_driver_from_env
from model.disease_feature import DiseaseFeature
from model.drug_feature import DrugFeature

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    csv_path = "./resources/data/disease_features.csv"
    features = _load_features(csv_path)

    start_ingest_time = time.time()
    adapter = DiseaseFeatureNeo4jAdapter(driver=new_driver_from_env())
    adapter.update_disease_features(features, step=1_000, batch_commit_size=40)
    end_ingest_time = time.time()
    elapsed_ingest_time = end_ingest_time - start_ingest_time
    logger.info(f"ingest finished, elapsed time: {elapsed_ingest_time} seconds")


def _load_features(csv_path: str) -> list[DrugFeature]:
    start_load_time = time.time()
    features = _load_csv(csv_path)
    for feature in features:
        logger.debug(f"{feature}")
    end_load_time = time.time()
    elapsed_load_time = end_load_time - start_load_time
    logger.info(
        f"loaded {len(features)} features for ingest, elapsed time: {elapsed_load_time} seconds"
    )
    return features


def _load_csv(path) -> list[DrugFeature]:
    features = []
    with open(path, mode="r") as csv_in:
        reader = csv.DictReader(csv_in)
        # node_index,mondo_id,mondo_name,group_id_bert,group_name_bert,mondo_definition,
        # umls_description,orphanet_definition,orphanet_prevalence,orphanet_epidemiology,
        # orphanet_clinical_description,orphanet_management_and_treatment,mayo_symptoms,
        # mayo_causes,mayo_risk_factors,mayo_complications,mayo_prevention,mayo_see_doc
        for row in reader:
            feature = DiseaseFeature(
                row["node_index"],
                row["mondo_id"],
                row["mondo_name"],
                row["group_id_bert"],
                row["group_name_bert"],
                row["mondo_definition"],
                row["umls_description"],
                row["orphanet_definition"],
                row["orphanet_prevalence"],
                row["orphanet_epidemiology"],
                row["orphanet_clinical_description"],
                row["orphanet_management_and_treatment"],
                row["mayo_symptoms"],
                row["mayo_causes"],
                row["mayo_risk_factors"],
                row["mayo_complications"],
                row["mayo_prevention"],
                row["mayo_see_doc"],
            )
            features.append(feature)
    return features


if __name__ == "__main__":
    main()
