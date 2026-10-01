import itertools
import logging

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError
from pandas import DataFrame

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection, get_or_default
from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.model.foundational_relationship_enum import FoundationalRelationshipEnum
from foundation.model.drug_aliases import DrugAliases
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class Neo4jDrugAliasesAdapter:
    """
    Adapter to update drug aliases found for eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    @log_time
    def find_drug_aliases_by_drug_name(
        self, drug_name: str, fuzzy_match: bool = False
    ) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for drug aliases. drug: {drug_name}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                aliases = self._find_drug_aliases_by_drug_name(
                    tx=tx, drug_name=drug_name, fuzzy_match=fuzzy_match
                )
                logger.info(f"found {len(aliases)} alias(es) for drug {drug_name}")
                return aliases

    @log_time
    def find_drug_aliases_by_drug_id(self, drug_id: str) -> DataFrame:
        ensure_connection(self.driver)

        logger.info(f"searching for drug aliases. drug: {drug_id}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                aliases = self._find_drug_aliases_by_drug_id(tx=tx, drug_id=drug_id)
                logger.info(f"found {len(aliases)} alias(es) for drug {drug_id}")
                return aliases

    @log_time
    def upsert_drug_aliases(self, drugs: list[DrugAliases] = []) -> str | None:
        ensure_connection(self.driver)

        logger.info(f"upserting aliases for {len(drugs)} drug(s)")
        count = 0
        for drug in drugs:
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    self._upsert_drug_aliases(tx=tx, drug=drug)
                    count += 1
                    if count % 100 == 0:
                        logger.info(f"updated drugs {count}")

    def _upsert_drug_aliases(self, tx: Transaction, drug: DrugAliases) -> str | None:
        search = """
        OPTIONAL MATCH (drug:%s { node_id: $drug_bank_id })
        """ % (
            normalize_node_label(FoundationalNodeEnum.DRUG.value[1])
        )

        [
            link_upserts,
            query_params,
        ] = self._generate_drug_alias_upserts(drug=drug)

        if len(link_upserts) < 1:
            drug_bank_id = drug.drug_bank_id
            logger.warning(f"{drug_bank_id} missing aliases, skipping...")
            return drug_bank_id

        step_size = 200
        stepper = range(0, len(link_upserts), step_size)
        for step in stepper:
            limit = (
                (step + step_size)
                if (step + step_size) < stepper.stop
                else stepper.stop
            )
            logger.info(f"upserting alias range {step}:{limit}")
            current_tx = link_upserts[step:limit]

            upsert_tx = "\n".join(
                list(
                    itertools.chain.from_iterable(
                        [
                            [search],
                            current_tx,
                            ["\tRETURN drug.node_id"],
                        ]
                    )
                )
            )

            logger.debug(f"{drug.drug_bank_id}")
            logger.debug(f"{drug.product_names}")
            logger.debug(f"{drug.synonyms}")
            logger.info(
                f"upserting {len(current_tx)}/{len(link_upserts)} alias(es) for drug: {drug.drug_bank_id}"
            )
            params = {"drug_bank_id": drug.drug_bank_id} | query_params
            logger.debug(f"upsert: {upsert_tx}")
            logger.debug(f"params: {params}")
            try:
                record = tx.run(
                    upsert_tx,
                    params,
                ).single()
                logger.info(f"cypher response: {record}")

            except (DriverError, Neo4jError) as exception:
                logging.error("%s raised an error: \n%s", upsert_tx, exception)
                raise

        return drug.drug_bank_id

    def _find_drug_aliases_by_drug_name(
        self, tx: Transaction, drug_name: str, fuzzy_match: bool = False
    ) -> DataFrame:
        search = self._generate_drug_alias_search_by_value(
            fuzzy_match_term=drug_name if fuzzy_match else None
        )
        params = {} if fuzzy_match else {"drug_name": drug_name}
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            records = tx.run(
                search,
                params,
            ).to_df()
            logger.debug(f"cypher response: {len(records)} record(s)")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _find_drug_aliases_by_drug_id(self, tx: Transaction, drug_id: str) -> DataFrame:
        search = self._generate_drug_alias_search_by_id()
        params = {"drug_id": drug_id}
        logger.info(f"search: {search}")
        logger.info(f"params: {params}")
        try:
            records = tx.run(
                search,
                params,
            ).to_df()
            logger.debug(f"cypher response: {len(records)} record(s)")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def _generate_drug_alias_upserts(
        self, drug: DrugAliases
    ) -> tuple[list[str], dict[str, str]]:
        question_params = {}
        link_upserts = []
        if drug is None:
            return (link_upserts, question_params)

        product_aliases = (
            drug.product_names if drug.product_names is not None else set()
        )
        product_count = len(product_aliases)
        synonym_aliases = drug.synonyms if drug.synonyms is not None else set()
        synonym_count = len(synonym_aliases)
        if product_count < 1 and synonym_count < 1:
            return (link_upserts, question_params)

        link_upserts = []
        [product_upserts, product_question_params] = (
            self._generate_product_name_upserts(
                drug_bank_id=drug.drug_bank_id, product_names=drug.product_names
            )
        )
        [synonym_upserts, synonym_question_params] = self._generate_synonyms_upserts(
            drug_bank_id=drug.drug_bank_id, synonyms=drug.synonyms
        )

        link_upserts.extend(product_upserts)
        link_upserts.extend(synonym_upserts)
        question_params = (
            question_params | product_question_params | synonym_question_params
        )
        return (link_upserts, question_params)

    def _generate_product_name_upserts(
        self, drug_bank_id: str, product_names: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        question_params = {}
        link_upserts = []
        sorted_aliases = self._sort(product_names)
        aliases = sorted_aliases if sorted_aliases is not None else []
        if drug_bank_id is None:
            return (link_upserts, question_params)

        alias_count = len(aliases)
        if alias_count < 1:
            return (link_upserts, question_params)

        link_upserts = []
        count = 0
        for alias in aliases:
            node_id_key = f"product{count}_node_id"
            drug_bank_key = f"product{count}_drug_bank_id"
            node_name_key = f"product{count}_node_name"
            question_params[node_id_key] = (
                f"drug_{drug_bank_id.lower()}_product_{count}"
            )
            question_params[drug_bank_key] = drug_bank_id
            question_params[node_name_key] = get_or_default(alias)
            upsert = """
            WITH drug
            MERGE (product:`%s` { node_id: %s })
            ON MATCH
                SET product.refresh_date = datetime()
            ON CREATE
                SET product.refresh_date = datetime(),
                    product.node_id = %s,
                    product.drug_bank_id = %s,
                    product.node_name = %s
            MERGE (drug)-[r1:`%s`]-(product)
            """.strip() % (
                normalize_node_label(FoundationalNodeEnum.DRUG_PRODUCT.value[1]),
                "$drug_bank_id",
                f"${node_id_key}",
                f"${drug_bank_key}",
                f"${node_name_key}",
                FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1],
            )
            link_upserts.append(upsert)
            count += 1
        return (link_upserts, question_params)

    def _generate_synonyms_upserts(
        self, drug_bank_id: str, synonyms: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        question_params = {}
        link_upserts = []
        sorted_aliases = self._sort(synonyms)
        aliases = sorted_aliases if sorted_aliases is not None else []
        if drug_bank_id is None:
            return (link_upserts, question_params)

        alias_count = len(aliases)
        if alias_count < 1:
            return (link_upserts, question_params)

        link_upserts = []
        count = 0
        for alias in aliases:
            node_id_key = f"synonym{count}_node_id"
            drug_bank_key = f"synonym{count}_drug_bank_id"
            node_name_key = f"synonym{count}_node_name"
            question_params[node_id_key] = (
                f"drug_{drug_bank_id.lower()}_synonym_{count}"
            )
            question_params[drug_bank_key] = drug_bank_id
            question_params[node_name_key] = get_or_default(alias)
            upsert = """
            WITH drug
            MERGE (synonym:`%s` { node_id: %s })
            ON MATCH
                SET synonym.refresh_date = datetime()
            ON CREATE
                SET synonym.refresh_date = datetime(),
                    synonym.node_id = %s,
                    synonym.drug_bank_id = %s,
                    synonym.node_name = %s
            MERGE (drug)-[r1:`%s`]-(synonym)
            """.strip() % (
                normalize_node_label(FoundationalNodeEnum.DRUG_SYNONYM.value[1]),
                "$drug_bank_id",
                f"${node_id_key}",
                f"${drug_bank_key}",
                f"${node_name_key}",
                FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1],
            )
            link_upserts.append(upsert)
            count += 1
        return (link_upserts, question_params)

    def _generate_drug_alias_search_by_value(
        self, fuzzy_match_term: str | None = None
    ) -> str:
        match_clause = (
            f"WHERE n.node_name =~ '(?i).*{fuzzy_match_term}.*'"
            if fuzzy_match_term is not None
            else "WHERE n.node_name = $drug_name"
        )
        return self._generate_drug_alias_search(match_clause)

    def _generate_drug_alias_search_by_id(self) -> str:
        match_clause = "WHERE n.node_id = $drug_id"
        return self._generate_drug_alias_search(match_clause)

    def _generate_drug_alias_search(self, match_clause: str) -> str:
        return """
        MATCH (n)
        %s AND (n.is_hidden IS NULL OR NOT n.is_hidden)
        CALL apoc.path.subgraphNodes([n], {relationshipFilter: "%s"}) YIELD node
        RETURN DISTINCT node.node_name as name, toStringOrNull(node.node_id) as node_id, 
            toStringOrNull(node.drug_bank_id) as drug_bank_id, toBoolean("drug" in labels(node)) as is_canonical 
        """.strip() % (
            match_clause,
            FoundationalRelationshipEnum.HAS_DRUG_ALIAS.value[1],
        )

    def _sort(self, aliases: set[str] | None) -> list[str] | None:
        if aliases is None:
            return None

        return sorted(aliases, key=lambda alias: alias.lower())
