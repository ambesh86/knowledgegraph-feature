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


class Neo4jPubmedQueryAdapter:
    """
    Adapter to query for related pubmed pmids found in eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def find_related_pubmed_by_drug(
        self, drug_id: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related pubmed by drug: {drug_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_pubmed_by_drug(
                    tx=tx, drug_id=drug_id, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} pubmed(s) for drug {drug_id}")
                return df

    @log_time
    def find_related_pubmed_by_clinicaltrail(
        self, nct_id: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related pubmed by nct_id: {nct_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_pubmed_by_clinicaltrail(
                    tx=tx, nct_id=nct_id, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} pubmed(s) for nct_id {nct_id}")
                return df

    @log_time
    def find_related_pubmed_by_gene(
        self, gene: str, page: int, page_size: int
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for related pubmed by gene: {gene}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                df = self._find_related_pubmed_by_gene(
                    tx=tx, gene=gene, page=page, page_size=page_size
                )
                logger.info(f"found {len(df)} pubmed(s) for gene {gene}")
                return df

    def _find_related_pubmed_by_drug(
        self, tx: Transaction, drug_id: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_pubmed_search_by_drug(page=page, page_size=page_size)
        params = {"drug_id": drug_id}
        logger.info("find_related_pubmed_by_drug")
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

    def _generate_pubmed_search_by_drug(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN n.node_id as drug_id, n.node_name as drug_name, n2.pmid as pmid
            ORDER BY pmid DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalRelationshipEnum.FEATURED_IN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
            offset,
            limit,
        )

    def _find_related_pubmed_by_clinicaltrail(
        self, tx: Transaction, nct_id: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_pubmed_search_by_clinicaltrail(
            page=page, page_size=page_size
        )
        params = {"nct_id": nct_id}
        logger.info("find_related_pubmed_by_drug")
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

    def _generate_pubmed_search_by_clinicaltrail(
        self, page: int, page_size: int
    ) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (start:`%s`)-[r]-(target:`%s`|`%s`)
            WHERE start.nct_id = $nct_id
            OPTIONAL MATCH (target)-[r2]-(end:`%s`)
            RETURN start.nct_id as nct_id, target.node_id as target_id, end.pmid as pmid
            ORDER BY nct_id, target_id, pmid DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
            offset,
            limit,
        )

    def _find_related_pubmed_by_gene(
        self, tx: Transaction, gene: str, page: int, page_size: int
    ) -> DataFrame:
        search = self._generate_pubmed_search_by_gene(page=page, page_size=page_size)
        params = {"gene": gene}
        logger.info("_find_related_pubmed_by_gene")
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

    def _generate_pubmed_search_by_gene(self, page: int, page_size: int) -> str:
        (limit, offset) = Pagination.calculate_limit_and_offset(
            page=page, page_size=page_size
        )
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN n.node_name as node_name, n2.pmid as pmid
            ORDER BY pmid DESC
            SKIP %s
            LIMIT %s
        """.strip() % (
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalRelationshipEnum.ANALYZED_IN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
            offset,
            limit,
        )
