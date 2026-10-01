import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError
from pandas import DataFrame

from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.infra.db.util.pagination import Pagination
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class Neo4jPatentExportAdapter:
    """
    Adapter to export for related patents found in eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def find_all_related_patents_by_drug(self, page: int, page_size: int) -> DataFrame:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_all_related_patents_by_drug(
                    tx=tx, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} drug and patent relationship(s)")
                return df

    @log_time
    def find_all_related_patents_by_clinical_trial(
        self, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_all_related_patents_by_clinical_trials(
                    tx=tx, page=page, page_size=page_size
                )
                logger.info(
                    f"found {len(df)} clinical trial and patent relationship(s)"
                )
                return df

    def _find_all_related_patents_by_drug(
        self,
        tx: Transaction,
        page: int,
        page_size: int,
    ) -> DataFrame:
        search = self._generate_patent_ids_by_drug_id(page, page_size)
        logger.info("_find_all_related_patents_by_drug")
        logger.info(f"search: {search}")
        try:
            results = tx.run(
                search,
            ).to_df()
            logger.debug(f"cypher response: {len(results)} results")
            return results
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _find_all_related_patents_by_clinical_trials(
        self,
        tx: Transaction,
        page: int,
        page_size: int,
    ) -> DataFrame:
        search = self._generate_patent_ids_by_clinical_trials(page, page_size)
        logger.info("_find_all_related_patents_by_clinical_trials")
        logger.info(f"search: {search}")
        try:
            results = tx.run(
                search,
            ).to_df()
            logger.debug(f"cypher response: {len(results)} results")
            return results
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_ids_by_drug_id(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(page, page_size)
        return """
            MATCH (ct:`%s`)-[r:`%s`]-(p:`%s`)
            RETURN ct.node_id as drug_id, p.patent_id as uspto_patent_id, date(p.filing_date) as filing_date
            ORDER BY ct.node_id
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalRelationshipEnum.DISCLOSED_IN.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
            offset,
            limit,
        )

    def _generate_patent_ids_by_clinical_trials(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(page, page_size)
        return """
            MATCH (ct:`%s`)-[r:`%s`]-(p:`%s`)
            RETURN ct.nct_id as nct_id, p.patent_id as uspto_patent_id, date(p.filing_date) as filing_date
            ORDER BY nct_id
            SKIP %s
            LIMIT %s
        """ % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            FoundationalRelationshipEnum.SUPPORTS_PATENT_APPLICATION.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
            offset,
            limit,
        )
