import logging

from neo4j import Driver, Transaction
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label, normalize_node_name
from graph.util.util import (
    ensure_connection,
    get_or_default,
    get_or_default_list,
)
from centree.infra.db.const import CENTREE_PROJECT_NODE_TYPE
from centree.model.stage0_project import Stage0Project

logger = logging.getLogger(__name__)


class Neo4jCentreeProjectIngestAdapter:
    """
    Adapter to perform ingest on centree nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_index(self, entity: str, entity_type: str) -> str | None:
        ensure_connection(self.driver)
        return self._find_node_index(entity, entity_type)

    def upsert_project(self, project: Stage0Project | None) -> str | None:
        if project is None:
            return None
        ensure_connection(self.driver)

        pmcid = None
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                pmcid = self._upsert_project(tx, project)

        logger.info(f"merged project: {project}")

    def _find_node_index(self, entity: str, entity_type: str) -> str | None:
        query = self._build_find_by_node_index_query(entity=entity)
        logger.debug(f"query: {query} node_name: {entity}")
        try:
            record = self.driver.execute_query(
                query,
                database_=self.database,
                result_transformer_=neo4j.Result.single,
            )
            if record is None:
                return record
            node_name = str(record["n.node_name"])
            node_index = str(record["n.node_index"])
            logger.debug(f"cypher response: {node_name} {node_index}")
            return node_index
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise

    def _build_find_by_node_index_query(self, entity: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
                WHERE n.node_name =~ '(?i)%s'
                RETURN n.node_name, n.node_index
            """ % (
            normalize_node_label(CENTREE_PROJECT_NODE_TYPE),
            normalize_node_name(entity),
        )
        return lookup_node_query

    def _upsert_project(self, tx: Transaction, project: Stage0Project) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert_project = (
            # merge on the primary id from centree
            # insert node_id only on create not merge
            """
            MERGE (proj:`%s` {
                source: $primary_id
            })
            ON MATCH
                SET proj.source = $primary_id,
                    proj.node_name = $primary_label,
                    proj.primary_label = $primary_label,
                    proj.collaborators = $collaborators,
                    proj.project_source = $project_source,
                    proj.project_science_coordinators = $project_science_coordinators,
                    proj.project_type = $project_type,
                    proj.project_aim = $project_aim,
                    proj.is_active_project = $is_active_project,
                    proj.eln_rd_codes = $eln_rd_codes,
                    proj.has_therapeutic_areas = $has_therapeutic_areas,
                    proj.refresh_date = datetime()
            ON CREATE
            SET proj.node_id = $node_id,
                    proj.source = $primary_id,
                    proj.node_name = $primary_label,
                    proj.primary_label = $primary_label,
                    proj.collaborators = $collaborators,
                    proj.project_source = $project_source,
                    proj.project_science_coordinators = $project_science_coordinators,
                    proj.project_type = $project_type,
                    proj.project_aim = $project_aim,
                    proj.is_active_project = $is_active_project,
                    proj.eln_rd_codes = $eln_rd_codes,
                    proj.has_therapeutic_areas = $has_therapeutic_areas,
                    proj.is_csl_confidential = true,
                    proj.refresh_date = datetime()
            RETURN proj.node_id
            """
            % f"{normalize_node_label(CENTREE_PROJECT_NODE_TYPE)}"
        )
        logger.debug(f"upsert: {upsert_project}")
        try:
            record = tx.run(
                upsert_project,
                {
                    "node_id": self._gen_uuid(),
                    "primary_label": get_or_default(project.primary_label),
                    "primary_id": get_or_default(project.primary_id),
                    "collaborators": get_or_default(project.collaborators),
                    "project_source": get_or_default(project.project_source),
                    "project_science_coordinators": get_or_default_list(
                        project.project_science_coordinators
                    ),
                    "project_type": get_or_default(project.project_type),
                    "project_aim": get_or_default(project.project_aim),
                    "is_active_project": get_or_default(project.is_active_project),
                    "eln_rd_codes": get_or_default_list(project.eln_rd_codes),
                    "has_therapeutic_areas": get_or_default_list(
                        project.has_therapeutic_areas
                    ),
                },
            ).single()
            logger.debug(f"upsert article cypher response: {record}")

            if record is None:
                return None

            return record["proj.node_id"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert_project, exception)
            raise

    def _gen_uuid(self) -> str:
        import uuid

        return str(uuid.uuid4())
