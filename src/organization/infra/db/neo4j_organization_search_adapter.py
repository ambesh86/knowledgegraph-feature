import logging
from typing import Any

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from util.regex_validation import sanitize_regex_pattern
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.infra.db.util.pagination import Pagination
from graph.util.util import ensure_connection
from organization.model.organization_node_enum import OrganizationNodeEnum

logger = logging.getLogger(__name__)


class Neo4jOrganizationSearchAdapter:
    """
    Adapter to search organizations and their relationships in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_companies_by_name_pattern(
        self, name_pattern: str, page: int = 0, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """
        Find companies matching a name pattern (case-insensitive regex)

        Args:
            name_pattern: Search pattern to match against organization_canonical_name.
                         Only * and ? wildcards are supported. All other regex special
                         characters are escaped for safety.
            page: current page
            page_size: Maximum number of records per page

        Returns:
            List of dicts with keys: org_id, org_name, org_type
        """
        ensure_connection(self.driver)

        logger.info(
            f"searching for organizations by name pattern: {name_pattern}, page: {page}, page_size: {page_size}"
        )
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                results = self._find_companies_by_name_pattern(
                    tx=tx, name_pattern=name_pattern, page=page, page_size=page_size
                )
                logger.info(
                    f"found {len(results)} organization(s) matching pattern '{name_pattern}'"
                )
                return results

    def _find_companies_by_name_pattern(
        self, tx: Transaction, name_pattern: str, page: int, page_size: int
    ) -> list[dict[str, Any]]:
        # Sanitize the pattern to prevent regex injection
        safe_pattern = sanitize_regex_pattern(name_pattern)

        (limit, skip) = Pagination.calculate_limit_and_offset(page, page_size)
        query = """
        MATCH (o:`%s`)
        WHERE o.organization_canonical_name =~ $pattern
        RETURN o.org_id as org_id, o.organization_canonical_name as org_name, o.organization_type as org_type
        SKIP $skip
        LIMIT $limit
        """.strip() % (
            OrganizationNodeEnum.ORGANIZATION_V3.value[1],
        )

        params = {"pattern": f"(?i){safe_pattern}", "skip": skip, "limit": limit}
        logger.info(f"query: {query}")
        logger.info(f"params: {params}")

        try:
            result = tx.run(query, params)
            records = [
                {
                    "org_id": record["org_id"],
                    "org_name": record["org_name"],
                    "org_type": record["org_type"],
                }
                for record in result
            ]
            logger.info(f"cypher response: found {len(records)} records")
            return records
        except (DriverError, Neo4jError) as exception:
            logger.error("%s raised an error: \n%s", query, exception)
            raise

    def find_assets_by_org_id(
        self, org_id: str, page: int = 0, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """
        Find drugs, diseases, trials related to an organization through clinical trials

        Args:
            org_id: Organization ID to search for
            page: current page
            page_size: Maximum number of records per page

        Returns:
            List of dicts with keys: org_type, org_name, rel, trial, rel2, entity_labels, entity_name
        """
        ensure_connection(self.driver)

        logger.info(
            f"searching for drugs and diseases for org_id: {org_id}, page: {page}, page_size: {page_size}"
        )
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                results = self._find_assets_by_org_id(
                    tx=tx, org_id=org_id, page=page, page_size=page_size
                )
                logger.info(f"found {len(results)} assets for org_id '{org_id}'")
                return results

    def _find_assets_by_org_id(
        self, tx: Transaction, org_id: str, page: int, page_size: int
    ) -> list[dict[str, Any]]:
        # todo: expand this query to show patents and pubmed docs too
        query = """
        MATCH (start:`%s`)-[rel1]-(ct:`%s`)-[rel2]-(end:%s)
        WHERE start.org_id = $org_id
        RETURN start.organization_type as org_type, start.organization_canonical_name as org_name,
               type(rel1) as org_to_ct_rel, ct.nct_id as trial, type(rel2) as ct_to_asset_rel, labels(end) as entity_labels, end.node_name as entity_name
        ORDER BY start.organization_canonical_name, trial desc
        SKIP $skip
        LIMIT $limit
        """.strip() % (
            OrganizationNodeEnum.ORGANIZATION_V3.value[1],
            FoundationalNodeEnum.CLINICAL_TRIAL.value[1],
            self._join_labels(
                [
                    FoundationalNodeEnum.DISEASE.value[1],
                    FoundationalNodeEnum.DRUG.value[1],
                ]
            ),
        )

        (limit, skip) = Pagination.calculate_limit_and_offset(page, page_size)
        params = {"org_id": org_id, "skip": skip, "limit": limit}
        logger.info(f"query: {query}")
        logger.info(f"params: {params}")

        try:
            join_delim = ", "
            result = tx.run(query, params)
            records = [
                {
                    "org_type": record["org_type"],
                    "org_name": record["org_name"],
                    "org_to_ct_rel": record["org_to_ct_rel"],
                    "trial": record["trial"],
                    "ct_to_asset_rel": record["ct_to_asset_rel"],
                    "entity_labels": join_delim.join(record["entity_labels"]),
                    "entity_name": record["entity_name"],
                }
                for record in result
            ]
            logger.info(f"cypher response: found {len(records)} records")
            return records
        except (DriverError, Neo4jError) as exception:
            logger.error("%s raised an error: \n%s", query, exception)
            raise

    def _join_labels(self, labels) -> str:
        escaped = [self._escape(label) for label in labels]
        return "|".join(escaped)

    def _escape(self, label: str) -> str:
        return f"`{label}`"
