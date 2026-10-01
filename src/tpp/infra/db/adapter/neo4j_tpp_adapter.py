import hashlib
import itertools
import logging

from ksuid import KsuidMs
from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.util import (
    ensure_connection,
    get_or_default,
    get_or_default_enum,
    get_or_default_ndarray,
)
from tpp.model.tpp_question import TppQuestion
from tpp.infra.db.const import (
    TPP_NODE_TYPE,
    TPP_QUESTION_NODE_TYPE,
    TPP_QUESTION_REL_TYPE,
)
from tpp.model.tpp import Tpp

logger = logging.getLogger(__name__)


class Neo4jTppAdapter:
    """
    Adapter to perform operations on a target product profile (tpp) and associated question nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def upsert(self, tpp: Tpp) -> str | None:
        ensure_connection(self.driver)

        self._ensure_ids(tpp)
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                node_id = self._upsert(
                    tx=tx,
                    tpp=tpp,
                )

        logger.info(f"upserted tpp and questions: {tpp.node_id}")
        return node_id

    def _upsert(self, tx: Transaction, tpp: Tpp) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert = self._generate_tpp_upsert()
        [link_upserts, question_params] = self._generate_tpp_question_upserts(
            tpp.questions
        )
        upsert_tx = "\n".join(
            list(
                itertools.chain.from_iterable(
                    [
                        [upsert],
                        link_upserts,
                        ["RETURN tpp.node_id, tpp.node_index, tpp.refresh_date"],
                    ]
                )
            )
        )

        params = {
            "node_id": tpp.node_id,
            "node_index": tpp.node_index,
            "threaputic_area": get_or_default_enum(tpp.threaputic_area),
            "product_description": get_or_default(tpp.product_description),
            "embeddings": get_or_default_ndarray(tpp.embeddings),
        } | question_params
        logger.debug(f"upsert: {upsert_tx}")
        logger.debug(f"{params}")
        try:
            record = tx.run(
                upsert_tx,
                params,
            ).single()
            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["tpp.node_id"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert, exception)
            raise

    def _generate_tpp_upsert(self) -> str:
        return """
            MERGE (tpp:`%s` {
                node_id: $node_id
            })
            ON MATCH
                SET tpp.threaputic_area = $threaputic_area,
                    tpp.product_description = $product_description,
                    tpp.refresh_date = datetime(),
                    tpp.embeddings = $embeddings
            ON CREATE
                SET tpp.threaputic_area = $threaputic_area,
                    tpp.product_description = $product_description,
                    tpp.refresh_date = datetime(),
                    tpp.node_index = $node_index,
                    tpp.embeddings = $embeddings,
                    tpp.is_csl = true
            """ % (
            TPP_NODE_TYPE
        )

    def _generate_tpp_question_upserts(
        self, tpp_questions: set[TppQuestion] | None
    ) -> tuple[list[str], dict[str, str]]:
        question_params = {}
        link_upserts = []
        if tpp_questions is None or len(tpp_questions) < 1:
            return (link_upserts, question_params)

        link_upserts = []
        count = 0
        for question in tpp_questions:
            question_params[f"question{count}_node_id"] = question.node_id
            question_params[f"question{count}_node_index"] = question.node_index
            question_params[f"question{count}_question_type"] = get_or_default_enum(
                question.question_type
            )
            question_params[f"question{count}_ideal"] = get_or_default(question.ideal)
            question_params[f"question{count}_acceptable"] = get_or_default(
                question.acceptable
            )
            question_params[f"question{count}_excluded"] = get_or_default(
                question.excluded
            )
            question_params[f"question{count}_embeddings"] = get_or_default_ndarray(
                question.embeddings
            )
            upsert = """
            WITH tpp
            MERGE (tpp_question:`%s` { node_id: %s })
            ON MATCH
                SET tpp_question.question_type = %s,
                    tpp_question.ideal = %s,
                    tpp_question.acceptable = %s,
                    tpp_question.excluded = %s,
                    tpp_question.refresh_date = datetime(),
                    tpp_question.embeddings = %s
            ON CREATE
                SET tpp_question.question_type = %s,
                    tpp_question.ideal = %s,
                    tpp_question.acceptable = %s,
                    tpp_question.excluded = %s,
                    tpp_question.refresh_date = datetime(),
                    tpp_question.embeddings = %s,
                    tpp_question.node_index = %s,
                    tpp_question.is_csl = true
            MERGE (tpp)-[r1:`%s` { is_csl: true }]-(tpp_question)
            """ % (
                TPP_QUESTION_NODE_TYPE,
                f"$question{count}_node_id",
                f"$question{count}_question_type",
                f"$question{count}_ideal",
                f"$question{count}_acceptable",
                f"$question{count}_excluded",
                f"$question{count}_embeddings",
                f"$question{count}_question_type",
                f"$question{count}_ideal",
                f"$question{count}_acceptable",
                f"$question{count}_excluded",
                f"$question{count}_embeddings",
                f"$question{count}_node_index",
                TPP_QUESTION_REL_TYPE,
            )
            link_upserts.append(upsert)
            count += 1
        return (link_upserts, question_params)

    def _ensure_ids(self, tpp: Tpp) -> None:
        """
        set node_id and node_index on objects is they are set to None
        """
        if tpp is None:
            return None
        if tpp.node_id is None:
            tpp.node_id = self._generate_tpp_composite_node_id(tpp)
            # WARNING: we only set node_index once on node creation
            if tpp.node_index is None:
                tpp.node_index = self._generate_node_index()

        if tpp.questions is not None:
            for question in tpp.questions:
                if question.node_id is None:
                    question.node_id = self._generate_tpp_question_composite_node_id(
                        question
                    )
                    # WARNING: we only set node_index once on node creation
                    if question.node_index is None:
                        question.node_index = self._generate_node_index()

    def _generate_node_index(self) -> str:
        ksuid = KsuidMs()
        return str(ksuid)

    def _generate_tpp_composite_node_id(self, tpp: Tpp) -> str:
        if tpp is None:
            return ""

        keys = []
        keys.append(tpp.product_description)
        if tpp.threaputic_area is not None:
            keys.append(tpp.threaputic_area.name)

        if tpp.questions is not None:
            for question in tpp.questions:
                keys.append(question.question_type.name)

        keys.sort()
        all_keys = " ".join(keys)

        logger.info(f"tpp node_id keys: {all_keys}")
        return hashlib.md5(all_keys.encode("utf-8")).hexdigest()

    def _generate_tpp_question_composite_node_id(
        self, tpp_question: TppQuestion
    ) -> str:
        if tpp_question is None:
            return ""

        keys = []
        keys.append(tpp_question.question_type.name)
        keys.append(tpp_question.ideal)
        keys.append(tpp_question.acceptable)
        keys.append(tpp_question.excluded)
        keys.sort()
        all_keys = " ".join(keys)
        logger.debug(f"question node_id keys: {all_keys}")
        return hashlib.md5(all_keys.encode("utf-8")).hexdigest()
