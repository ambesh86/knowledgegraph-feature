import logging
from neo4j import Driver, Session
from neo4j.exceptions import DriverError, Neo4jError
from helper.driver_helper import ensure_connection
from helper.drug_statement_helper import build_batch_statement
from model.drug_feature import DrugFeature

logger = logging.getLogger(__name__)


class DrugFeatureNeo4jAdapter:
    """
    update graph to include drug feature meta data
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def update_drug_features(
        self, drug_features: list[DrugFeature], step=1_000, batch_commit_size: int = 100
    ) -> int:
        ensure_connection(self.driver)
        count = 0
        apoc_batches = 0
        apoc_total = 0
        apoc_errors = []
        with self.driver.session() as session:
            total = len(drug_features)
            start = 0
            end = step
            while start < total:
                logger.info(
                    f"starting batch step {count} start = {start}, end = {end}..."
                )
                batch = drug_features[start:end]
                result = self._merge(session, batch, batch_commit_size)
                apoc_batches += result["batches"]
                apoc_total += result["total"]
                apoc_errors.append(result["errorMessages"])
                count += 1
                start = count * step
                end = (count + 1) * step

        apoc_error_count = len([err for err in apoc_errors if len(err) > 0])
        if apoc_error_count > 0:
            for error in apoc_errors:
                logger.info(f"{error}")
        logger.info(f"updated nodes in {count} iterations with steps of {step}")
        logger.info(
            f"apoc batches = {apoc_batches}, apoc total = {apoc_total} apoc errors = {apoc_error_count}"
        )
        return count

    def _merge(
        self, session: Session, drug_features: list[DrugFeature], batch_commit_size: int
    ) -> dict[str, any]:
        result = self._merge_and_return(session, drug_features, batch_commit_size)
        return result

    def _merge_and_return(
        self, session: Session, drug_features: list[DrugFeature], batch_commit_size: int
    ) -> dict[str, any]:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        update_statement = build_batch_statement(
            drug_features=drug_features, batch_size=batch_commit_size
        )
        logger.debug(f"update statement: {update_statement}")
        try:
            record = session.run(update_statement).single()
            logger.debug(f"cypher response: {record}")
            return {
                "batches": record["batches"],
                "total": record["total"],
                "errorMessages": record["errorMessages"],
            }
        # Capture any errors along with the query and data for traceability
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", update_statement, exception)
            raise
