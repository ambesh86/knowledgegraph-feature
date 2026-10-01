import logging
from argparse import Namespace
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from pandas import Series

from foundation.conf.conf import (
    _neo4j_driver,
    _neo4j_foundational_node_count_adapter,
    _neo4j_patent_export_adapter,
    patent_id_export_writer,
)
from foundation.infra.db.adapter.neo4j_patent_export_adapter import (
    Neo4jPatentExportAdapter,
)
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.writer.patent_id_export_writer import PatentIdExportWriter
from annotation.timer_annotation import log_time

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


DEFAULT_PAGE_SIZE = 20_000

logger = logging.getLogger(__name__)


def main():
    """
    export patent ids to a specified csv file
    """
    load_dotenv()

    args = build_args()
    out_file = Path(args.out)
    _export(relationship_label=args.relationship, out_file=out_file)


@log_time
def _export(relationship_label: str, out_file: Path) -> None:
    driver = _neo4j_driver()
    count_adapter = _neo4j_foundational_node_count_adapter(driver)
    export_adapter = _neo4j_patent_export_adapter(driver)
    writer = patent_id_export_writer()

    label = _verify_label(relationship_label)
    count = count_adapter.count_all_by_label(label)
    logger.info(f"Counted {count} {label} elements")
    if count == 0:
        return
    logger.info(f"paginating for patent relationships")
    _export_pages(
        export_adapter=export_adapter,
        writer=writer,
        output_path=out_file,
        label=label,
        count=count,
    )


def _export_pages(
    export_adapter: Neo4jPatentExportAdapter,
    writer: PatentIdExportWriter,
    output_path: Path,
    label: str,
    count: int,
) -> None:
    page_size = DEFAULT_PAGE_SIZE if count > DEFAULT_PAGE_SIZE else count
    even_pages = int(count / page_size)
    # 1 based page indexes
    # num_pages = even_pages + 1 if count % page_size == 0 else even_pages + 2

    # logger.info(f"fetching {num_pages} pages, page_size: {page_size}")
    current_page = 0
    while True:
        current_page += 1
        page = current_page
        logger.info(f"fetching page {page}...")
        rows = _fetch_page(
            export_adapter=export_adapter, label=label, page=page, page_size=page_size
        )
        if rows is None or len(rows) == 0:
            logger.info(f"fetched {page} pages")
            break
        logger.info(f"writing page:{page} rows: {len(rows)}")
        writer.write_csv(output_path=output_path, rows=rows)


def _fetch_page(
    export_adapter: Neo4jPatentExportAdapter, label: str, page: int, page_size: int
) -> list[Tuple[str, str, str]]:
    rows = None
    if label == FoundationalNodeEnum.CLINICAL_TRIAL.value[1]:
        df = export_adapter.find_all_related_patents_by_clinical_trial(page, page_size)
        rows = df.apply(_map_nct_row, axis=1)
    elif label == FoundationalNodeEnum.DRUG.value[1]:
        df = export_adapter.find_all_related_patents_by_drug(page, page_size)
        rows = df.apply(_map_drug_row, axis=1)
    if rows is None:
        logger.warning(f"page {page} return 0 results, moving on...")
        return []
    else:
        return [el for el in rows]


def _map_nct_row(row: Series) -> Tuple[str, str, str]:
    return (row["nct_id"], row["uspto_patent_id"], row["filing_date"])


def _map_drug_row(row: Series) -> Tuple[str, str, str]:
    return (row["drug_id"], row["uspto_patent_id"], row["filing_date"])


def _verify_label(relationship_label: str) -> str:
    if relationship_label == FoundationalNodeEnum.CLINICAL_TRIAL.value[1]:
        label = FoundationalNodeEnum.CLINICAL_TRIAL.value[1]
    elif relationship_label == FoundationalNodeEnum.DRUG.value[1]:
        label = FoundationalNodeEnum.DRUG.value[1]
    else:
        raise ValueError(f"Unexpected label {relationship_label}")
    return label


def build_args() -> Namespace:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Export patent relationships found in euGENE")
    parser.add_argument(
        "--relationship",
        type=str,
        default="ClinicalTrial",
        choices=["ClinicalTrial", "drug"],
        required=True,
        help="Map patent ids to all of the nodes in euGENE with the given label type",
    )

    parser.add_argument(
        "--out",
        type=str,
        default="./output/export/patent/patent_relationships.csv",
        required=False,
        help="csv file to export patent relationships",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
