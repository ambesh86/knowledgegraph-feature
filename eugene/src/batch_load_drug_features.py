import csv
import logging
import time
from dotenv import load_dotenv
from adapter.drug_feature_neo4j_adapter import DrugFeatureNeo4jAdapter
from helper.driver_helper import new_driver_from_env
from model.drug_feature import DrugFeature

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    csv_path = "./resources/data/drug_features.csv"
    features = _load_features(csv_path)

    start_ingest_time = time.time()
    adapter = DrugFeatureNeo4jAdapter(driver=new_driver_from_env())
    adapter.update_drug_features(features, step=1_000, batch_commit_size=20)
    end_ingest_time = time.time()
    elapsed_ingest_time = end_ingest_time - start_ingest_time
    logger.info(f"ingest finished, elapsed time: {elapsed_ingest_time} seconds...")


def _load_features(csv_path: str) -> list[DrugFeature]:
    start_load_time = time.time()
    features = _load_csv(csv_path)
    for feature in features:
        logger.debug(f"{feature}")
    end_load_time = time.time()
    elapsed_load_time = end_load_time - start_load_time
    logger.info(
        f"loaded {len(features)} features for ingest, elapsed time: {elapsed_load_time}..."
    )
    return features


def _load_csv(path) -> list[DrugFeature]:
    features = []
    with open(path, mode="r") as csv_in:
        reader = csv.DictReader(csv_in)
        # node_index,description,half_life,indication,mechanism_of_action,protein_binding,
        #   pharmacodynamics,state,atc_1,atc_2,atc_3,atc_4,category,group,
        #   pathway,molecular_weight,tpsa,clogp
        for row in reader:
            feature = DrugFeature(
                row["node_index"],
                row["description"],
                row["half_life"],
                row["indication"],
                row["mechanism_of_action"],
                row["protein_binding"],
                row["pharmacodynamics"],
                row["state"],
                row["atc_1"],
                row["atc_2"],
                row["atc_3"],
                row["atc_4"],
                row["category"],
                row["group"],
                row["pathway"],
                row["molecular_weight"],
                row["tpsa"],
                row["clogp"],
            )
            features.append(feature)
    return features


if __name__ == "__main__":
    main()
