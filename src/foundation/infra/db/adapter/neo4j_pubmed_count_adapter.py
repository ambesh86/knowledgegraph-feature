import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import (
    FoundationalRelationshipEnum,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class Neo4jPubmedCountAdapter:
    """
    Adapter to query and count for related pubmed pmids found in eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def count_related_pubmed_by_drug(self, drug_id: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related pubmed by drug: {drug_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_pubmed_by_drug(tx=tx, drug_id=drug_id)
                logger.info(f"counted {count} pubmed(s) for drug {drug_id}")
                return count

    @log_time
    def count_related_pubmed_by_clinicaltrail(self, nct_id: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related pubmed by nct_id: {nct_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_pubmed_by_clinicaltrail(
                    tx=tx, nct_id=nct_id
                )
                logger.info(f"counted {count} pubmed(s) for nct_id {nct_id}")
                return count

    @log_time
    def count_related_pubmed_by_gene(self, gene: str) -> int:
        ensure_connection(self.driver)

        logger.info(f"counting related pubmed by gene: {gene}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                count = self._count_related_pubmed_by_gene(tx=tx, gene=gene)
                logger.info(f"counted {count} pubmed(s) for gene {gene}")
                return count

    def _count_related_pubmed_by_drug(
        self,
        tx: Transaction,
        drug_id: str,
    ) -> int:
        search = self._generate_pubmed_count_by_drug_id()
        params = {"drug_id": drug_id}
        logger.info("count_related_pubmed_by_drug")
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

    def _generate_pubmed_count_by_drug_id(self) -> str:
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_id = $drug_id
            RETURN count(n2) as count
        """.strip() % (
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalRelationshipEnum.FEATURED_IN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
        )

    def _count_related_pubmed_by_clinicaltrail(
        self,
        tx: Transaction,
        nct_id: str,
    ) -> int:
        search = self._generate_pubmed_count_by_clinicaltrail()
        params = {"nct_id": nct_id}
        logger.info("count_related_pubmed_by_clinicaltrail")
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

    def _generate_pubmed_count_by_clinicaltrail(self) -> str:
        return """
            MATCH (start:`%s`)-[r]-(target:`%s`|`%s`)
            WHERE start.nct_id = $nct_id
            OPTIONAL MATCH (target)-[r2]-(end:`%s`)
            RETURN count(end.pmid) as count
        """.strip() % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            FoundationalNodeEnum.DRUG.value[1],
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
        )

    def _count_related_pubmed_by_gene(
        self,
        tx: Transaction,
        gene: str,
    ) -> int:
        search = self._generate_pubmed_count_by_gene()
        params = {"gene": gene}
        logger.info("count_related_pubmed_by_gene")
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

    def _generate_pubmed_count_by_gene(self) -> str:
        return """
            MATCH (n:`%s`)-[r:`%s`]-(n2:`%s`)
            WHERE n.node_name = $gene
            RETURN count(n2) as count
        """.strip() % (
            FoundationalNodeEnum.GENE_PROTEIN.value[1],
            FoundationalRelationshipEnum.ANALYZED_IN.value[1],
            FoundationalNodeEnum.RESEARCH.value[1],
        )
