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


class Neo4jPatentQueryAdapter:
    """
    Adapter to query for related patents found in eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def find_related_patents_by_drug(
        self, drug_id: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related patents by drug: {drug_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_patents_by_drug(
                    tx=tx, drug_id=drug_id, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} patent(s) for drug {drug_id}")
                return df

    @log_time
    def count_related_patents_by_drug(self, drug_id: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related patents by drug: {drug_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_patents_by_drug(tx=tx, drug_id=drug_id)
                logger.info(f"counted {count} patent(s) for drug {drug_id}")
                return count

    @log_time
    def find_related_patents_by_clinicaltrail(
        self, nct_id: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related patents by nct_id: {nct_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_patents_by_clinicaltrail(
                    tx=tx, nct_id=nct_id, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} patent(s) for nct_id {nct_id}")
                return df

    @log_time
    def count_related_patents_by_clinicaltrail(self, nct_id: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related patents by nct_id: {nct_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_patents_by_clinicaltrail(
                    tx=tx, nct_id=nct_id
                )
                logger.info(f"counted {count} patent(s) for nct_id {nct_id}")
                return count

    @log_time
    def find_related_patents_by_gene(
        self, gene: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related patents by gene: {gene}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_patents_by_gene(
                    tx=tx, gene=gene, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} patent(s) for gene {gene}")
                return df

    @log_time
    def count_related_patents_by_gene(self, gene: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related patents by gene: {gene}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_patents_by_gene(tx=tx, gene=gene)
                logger.info(f"counted {count} patent(s) for gene {gene}")
                return count

    def _find_related_patents_by_drug(
        self, tx: Transaction, drug_id: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_patent_search_by_drug(page=page, page_size=page_size)
        params = {"drug_id": drug_id}
        logger.info("find_related_patents_by_drug")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            records = tx.run(
                search,
                params,
            ).to_df()
            logger.debug(f"cypher response has {len(records)} row(s)")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_search_by_drug(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN n.node_id as drug_id, n.node_name as drug_name, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalRelationshipEnum.DISCLOSED_IN.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
            offset,
            limit,
        )

    def _find_related_patents_by_clinicaltrail(
        self, tx: Transaction, nct_id: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_patent_search_by_clinicaltrail(
            page=page, page_size=page_size
        )
        params = {"nct_id": nct_id}
        logger.info("find_related_patents_by_drug")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            records = tx.run(
                search,
                params,
            ).to_df()
            logger.debug(f"cypher response has {len(records)} row(s)")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_search_by_clinicaltrail(
        self, page: int, page_size: int
    ) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.nct_id = $nct_id
            RETURN n.nct_id as nct_id, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            FoundationalRelationshipEnum.SUPPORTS_PATENT_APPLICATION.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
            offset,
            limit,
        )

    def _find_related_patents_by_gene(
        self, tx: Transaction, gene: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_patent_search_by_gene(page=page, page_size=page_size)
        params = {"gene": gene}
        logger.info("_find_related_patents_by_gene")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            records = tx.run(
                search,
                params,
            ).to_df()
            logger.debug(f"cypher response has {len(records)} row(s)")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_search_by_gene(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN n.node_name as node_name, n2.patent_id as patent_id
            ORDER BY patent_id DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalRelationshipEnum.PATENT_APP_TARGET.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
            offset,
            limit,
        )

    def _count_related_patents_by_drug(
        self,
        tx: Transaction,
        drug_id: str,
    ) -> int:
        search = self._generate_patent_count_by_drug_id()
        params = {"drug_id": drug_id}
        logger.info("count_related_patents_by_drug")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            result = tx.run(
                search,
                params,
            ).single()
            logger.debug(f"cypher response: {result}")
            if result is None:
                return 0
            return result["count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_count_by_drug_id(self) -> str:
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN count(n2) as count
        """.strip() % (
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalRelationshipEnum.DISCLOSED_IN.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
        )

    def _count_related_patents_by_clinicaltrail(
        self,
        tx: Transaction,
        nct_id: str,
    ) -> int:
        search = self._generate_patent_count_by_clinicaltrail()
        params = {"nct_id": nct_id}
        logger.info("count_related_patents_by_clinicaltrail")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            result = tx.run(
                search,
                params,
            ).single()
            logger.debug(f"cypher response: {result}")
            if result is None:
                return 0
            return result["count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_count_by_clinicaltrail(self) -> str:
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.nct_id = $nct_id
            RETURN count(n2) as count
        """.strip() % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            FoundationalRelationshipEnum.SUPPORTS_PATENT_APPLICATION.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
        )

    def _count_related_patents_by_gene(
        self,
        tx: Transaction,
        gene: str,
    ) -> int:
        search = self._generate_patent_count_by_gene()
        params = {"gene": gene}
        logger.info("count_related_patents_by_gene")
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            result = tx.run(
                search,
                params,
            ).single()
            logger.debug(f"cypher response: {result}")
            if result is None:
                return 0
            return result["count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_patent_count_by_gene(self) -> str:
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN count(n2) as count
        """.strip() % (
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalRelationshipEnum.PATENT_APP_TARGET.value[1],
            FoundationalNodeEnum.PATENT_APPLICATION.value[1],
        )
