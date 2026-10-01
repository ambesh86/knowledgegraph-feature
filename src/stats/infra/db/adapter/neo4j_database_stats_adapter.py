import logging
from typing import Tuple

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from stats.model.system_stats import DatabaseStats
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class Neo4jDatabaseStatsAdapter:
    """
    Adapter to perform stats count operations on eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def query_system_stats(self) -> DatabaseStats:
        ensure_connection(self.driver)

        node_count = self._count_all_nodes()
        rel_count = self._count_all_relationships()
        drug_count = self._count_all_by_label(FoundationalNodeEnum.DRUG.value[1])
        disease_count = self._count_all_by_label(FoundationalNodeEnum.DISEASE.value[1])
        gene_protein_count = self._count_all_by_label(
            FoundationalNodeEnum.GENE_PROTEIN.value[1]
        )
        uspto_count = self._count_all_by_label(
            FoundationalNodeEnum.PATENT_APPLICATION.value[1]
        )
        clinical_trail_count = self._count_all_by_label(
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1]
        )
        pubmed_count = self._count_all_by_label(FoundationalNodeEnum.RESEARCH.value[1])
        researcher_count = self._count_all_by_label(
            FoundationalNodeEnum.INVESTIGATORS.value[1]
        )
        organization_count = self._count_all_by_label(
            FoundationalNodeEnum.ORGANIZATION.value[1]
        )
        disambiguated_organization_count = self._count_disambiguated_organizations()

        (therapeutic_area_count, therapeutic_area_subgroup_count) = (
            self._count_theraputic_areas()
        )

        (min_uspto_date, max_uspto_date) = self._fetch_min_max_uspto_dates()
        return DatabaseStats(
            node_count=DatabaseStats.format_count(node_count),
            relationship_count=DatabaseStats.format_count(rel_count),
            drug_count=DatabaseStats.format_count(drug_count),
            disease_count=DatabaseStats.format_count(disease_count),
            gene_protein_count=DatabaseStats.format_count(gene_protein_count),
            drug_synonym_count=0,
            uspto_count=DatabaseStats.format_count(uspto_count),
            uspto_filing_date_min=min_uspto_date,
            uspto_filting_date_max=max_uspto_date,
            clinical_trial_count=DatabaseStats.format_count(clinical_trail_count),
            therapeutic_area_count=DatabaseStats.format_count(therapeutic_area_count),
            therapeutic_area_subgroup_count=DatabaseStats.format_count(
                therapeutic_area_subgroup_count
            ),
            pubmed_count=DatabaseStats.format_count(pubmed_count),
            pubmed_researcher_count=DatabaseStats.format_count(researcher_count),
            organization_count=DatabaseStats.format_count(organization_count),
            disambiguated_organization_count=DatabaseStats.format_count(
                disambiguated_organization_count
            ),
        )

    @log_time
    def _count_all_by_label(self, label: str) -> int:
        query = self._build_count_all_by_label(label)
        logger.info(f"count all: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return record["count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_all_by_label(self, label: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
            RETURN count(n) as count
            """ % (
            label,
        )
        return lookup_node_query

    @log_time
    def _count_all_relationships(self) -> int:
        query = self._build_count_all_relationships()
        logger.info(f"count all: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return record["relationship_count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_all_relationships(self) -> str:
        # Directed match so each relationship is counted ONCE. An undirected
        # `(n)-[r]-(n2)` pattern traverses every edge from both endpoints and
        # double-counts (e.g. reporting 8.1m for a 4.05m-edge graph).
        return """MATCH ()-[r]->()
            RETURN count(r) as relationship_count
            """

    @log_time
    def _count_all_nodes(self) -> int:
        query = self._build_count_all_nodes()
        logger.info(f"count all: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return record["node_count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_all_nodes(self) -> str:
        return """MATCH (n)
            RETURN count(n) as node_count
            """

    @log_time
    def _count_disambiguated_organizations(self) -> int:
        query = self._build_count_disambiguated_organizations()
        logger.info(f"count: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return record["disambiguated_org_count"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_disambiguated_organizations(self) -> str:
        return """MATCH (n:`%s`)
            RETURN count(distinct(n.organization_id)) as disambiguated_org_count
            """ % (
            FoundationalNodeEnum.ORGANIZATION.value[1]
        )

    @log_time
    def _count_theraputic_areas(self) -> Tuple[int, int]:
        query = self._build_count_theraputic_areas()
        logger.info(f"count: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return (
                record["theraputic_area_count"],
                record["theraputic_area_group_count"],
            )
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_count_theraputic_areas(self) -> str:
        return """MATCH (n:`%s`)
        RETURN COUNT(DISTINCT(n.therapeutic_area)) as theraputic_area_count,
            COUNT(DISTINCT(n.therapeutic_subgroup)) as theraputic_area_group_count
            """ % (
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1]
        )

    @log_time
    def _fetch_min_max_uspto_dates(self) -> Tuple[str, str]:
        query = self._build_min_max_uspto_dates()
        logger.info(f"min max dates: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            return (
                record["min_uspto_filing_date"],
                record["max_uspto_filing_date"],
            )
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_min_max_uspto_dates(self) -> str:
        return """MATCH (n:`%s`)
            RETURN toStringOrNull(min(n.filing_date)) as min_uspto_filing_date, toStringOrNull(max(n.filing_date)) as max_uspto_filing_date
            """ % (
            FoundationalNodeEnum.PATENT_APPLICATION.value[1]
        )

    # ── graph-wide aggregations (analytics) ────────────────────────────────
    @log_time
    def query_top_connected_proteins(self, limit: int = 20) -> list[dict]:
        """Gene/proteins ranked by overall degree, with a breakdown of how many
        diseases, other proteins, and drugs each connects to."""
        limit = max(1, min(int(limit), 100))
        query = (
            """
            MATCH (p:gene_protein)
            WITH p, apoc.node.degree(p) AS degree
            ORDER BY degree DESC
            LIMIT %d
            RETURN p.node_name AS protein,
                   p.node_id   AS node_id,
                   apoc.node.degree(p, 'disease_protein') AS diseases,
                   apoc.node.degree(p, 'protein_protein') AS proteins,
                   apoc.node.degree(p, 'drug_protein')    AS drugs,
                   degree AS total_degree
            """
            % limit
        )
        return self._run_list(query)

    @log_time
    def query_shared_gene_diseases(
        self, min_shared: int = 3, limit: int = 25
    ) -> list[dict]:
        """Pairs of diseases that share at least `min_shared` associated genes
        (common-neighbour aggregation over the disease_protein relationship)."""
        min_shared = max(2, min(int(min_shared), 1000))
        limit = max(1, min(int(limit), 100))
        # Undirected on the disease_protein edges (stored gene_protein->disease).
        query = (
            """
            MATCH (d1:disease)-[:disease_protein]-(g:gene_protein)-[:disease_protein]-(d2:disease)
            WHERE id(d1) < id(d2)
            WITH d1, d2, count(DISTINCT g) AS shared_genes
            WHERE shared_genes >= %d
            RETURN d1.node_name AS disease_a,
                   d2.node_name AS disease_b,
                   shared_genes
            ORDER BY shared_genes DESC
            LIMIT %d
            """
            % (min_shared, limit)
        )
        return self._run_list(query)

    def _run_list(self, query: str) -> list[dict]:
        logger.info(f"analytics query: {query}")
        try:
            return self.driver.execute_query(
                query_=query,
                result_transformer_=lambda result: [r.data() for r in result],
            )
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception
