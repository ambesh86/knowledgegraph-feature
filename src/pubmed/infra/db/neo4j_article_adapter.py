import logging
from typing import Any

from neo4j import Driver, Transaction
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from pubmed.model.article import Article
from pubmed.infra.db.const import (
    PUBMED_ARTICLE_EXTRACTION_REL_TYPE,
    PUBMED_ARTICLE_NODE_TYPE,
)
from graph.util.node_util import normalize_node_label, normalize_node_name
from graph.util.util import (
    ensure_connection,
    get_or_default,
    get_or_default_list,
    get_or_default_ndarray,
    get_or_default_set,
)
from clinicaltrail.infra.db.const import CLINICAL_TRIAL_NODE_TYPE

logger = logging.getLogger(__name__)


class Neo4jArticleAdapter:
    """
    Adapter to perform operations on the pubmed article nodes in the neo4j eugene(genieve) graph
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_index(self, entity: str, entity_type: str) -> str | None:
        ensure_connection(self.driver)
        return self._find_node_index(entity, entity_type)

    def upsert_article(self, article: Article | None) -> str | None:
        if article is None:
            return None
        ensure_connection(self.driver)

        pmcid = None
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                pmcid = self._upsert_article(tx, article)

        logger.info(f"merged article pmcid: {pmcid}")

    def link_article_and_node(self, pmcid: str | None, node_index: str | None) -> None:
        if pmcid is None or node_index is None:
            return None
        ensure_connection(self.driver)

        # merge to add new relationship between
        #   (pubmed doc with given pmcid)-[:has_extraction]-(entity with given node_index
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                pmcid = self._link_article_and_node(
                    tx, pmcid=pmcid, node_index=node_index
                )

        logger.debug(f"linked node: {node_index} to article pmcid: {pmcid}")

    def link_article_and_clinical_trial(
        self, pmcid: str | None, node_id: str | None
    ) -> None:
        if pmcid is None or node_id is None:
            return None
        ensure_connection(self.driver)

        # merge to add new relationship between
        # clinical trial nodes do not have a node_index, only a node_id
        #   (pubmed doc with given pmcid)-[:has_extraction]-(entity with given node_id)
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                pmcid = self._link_article_and_clinical_trial(
                    tx, pmcid=pmcid, node_id=node_id
                )

        logger.debug(f"linked clincal trial: {node_id} to article pmcid: {pmcid}")

    def _find_node_index(self, entity: str, entity_type: str) -> str | None:
        query = self._build_find_by_node_index_query(
            entity_type=entity_type, entity=entity
        )
        logger.debug(f"query: {query} node_name: {entity}")
        # {"label": normalize_node_label(entity_type), "node_name": entity},
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

    def _build_find_by_node_index_query(self, entity_type: str, entity: str) -> str:
        # example query
        # MATCH (p:gene_protein)
        #     WHERE p.node_name = 'DFFB'
        # RETURN p.node_name, p.node_index
        # { node_name: $node_name }

        lookup_node_query = """MATCH (n:`%s`)
                WHERE n.node_name =~ '(?i)%s'
                RETURN n.node_name, n.node_index
            """ % (
            normalize_node_label(entity_type),
            normalize_node_name(entity),
        )
        return lookup_node_query

    def _upsert_article(self, tx: Transaction, article: Article) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/

        upsert_article = (
            """
            MERGE (doc1:`%s` {
                pmcid: $pmcid
            })
            ON MATCH
                SET doc1.doi = $doi,
                    doc1.pmid = $pmid,
                    doc1.refresh_date = datetime(),
                    doc1.title = $title,
                    doc1.keywords = $keywords,
                    doc1.title_embeddings = $title_embeddings,
                    doc1.keyword_embeddings = $keyword_embeddings,
                    doc1.merged_embeddings = $merged_embeddings,
                    doc1.epub_date = $pub_date,
                    doc1.pdf_uri = $pdf_uri
            ON CREATE
                SET doc1.pmcid = $pmcid,
                    doc1.is_pubmed = true,
                    doc1.refresh_date = datetime(),
                    doc1.doi = $doi,
                    doc1.pmid = $pmid,
                    doc1.keywords = $keywords,
                    doc1.title_embeddings = $title_embeddings,
                    doc1.keyword_embeddings = $keyword_embeddings,
                    doc1.merged_embeddings = $merged_embeddings,
                    doc1.title = $title,
                    doc1.epub_date = $pub_date,
                    doc1.pdf_uri = $pdf_uri
            RETURN doc1.pmcid
            """
            % f"{normalize_node_label(PUBMED_ARTICLE_NODE_TYPE)}"
        )
        logger.debug(f"upsert: {upsert_article}")
        try:
            record = tx.run(
                upsert_article,
                {
                    "doi": get_or_default(article.doi),
                    "pmcid": get_or_default(article.pmcid),
                    "pmid": get_or_default(article.pmid),
                    "title": get_or_default(article.title),
                    "keywords": get_or_default_list(article.keywords),
                    "nct_ids": get_or_default_set(article.nct_ids),
                    "title_embeddings": get_or_default_ndarray(
                        article.title_embeddings
                    ),
                    "keyword_embeddings": get_or_default_ndarray(
                        article.keywords_embeddings
                    ),
                    "merged_embeddings": get_or_default_ndarray(
                        article.merged_embeddings
                    ),
                    "pub_date": get_or_default(article.pub_date),
                    "pdf_uri": get_or_default(article.pdf_uri),
                },
            ).single()
            logger.debug(f"upsert article cypher response: {record}")

            if record is None:
                return None

            return record["doc1.pmcid"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert_article, exception)
            raise

    def _link_article_and_node(
        self, tx: Transaction, pmcid: str | None, node_index: str | None
    ) -> str | None:
        """
        link article and node
        """
        if pmcid is None or node_index is None:
            return None

        link_article = """
            OPTIONAL MATCH (doc:%s { pmcid: $pmcid })
            OPTIONAL MATCH (entity { node_index: $node_index })
            MERGE (doc)-[r:%s { is_pubmed: true }]-(entity)
            RETURN doc.pmcid, type(r), entity.node_index
            """ % (
            PUBMED_ARTICLE_NODE_TYPE,
            PUBMED_ARTICLE_EXTRACTION_REL_TYPE,
        )
        logger.info(f"linking pmcid: {pmcid} node_index: {node_index}")
        logger.debug(f"upsert: {link_article}")
        try:
            record = tx.run(
                link_article,
                {"pmcid": int(pmcid), "node_index": node_index},
            ).single()
            logger.info(f"cypher response: {record}")

            if record is None:
                return None

            return record["doc.pmcid"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", link_article, exception)
            raise

    def _link_article_and_clinical_trial(
        self, tx: Transaction, pmcid: str | None, node_id: str | None
    ) -> str | None:
        """
        link article and node
        """
        if pmcid is None or node_id is None:
            return None

        link_article = """
            OPTIONAL MATCH (doc:%s { pmcid: $pmcid })
            OPTIONAL MATCH (entity:%s { node_id: $node_id })
            MERGE (doc)-[r:%s { is_pubmed: true }]-(entity)
            RETURN doc.pmcid, type(r), entity.node_index
            """ % (
            PUBMED_ARTICLE_NODE_TYPE,
            CLINICAL_TRIAL_NODE_TYPE,
            PUBMED_ARTICLE_EXTRACTION_REL_TYPE,
        )
        logger.info(f"linking pmcid: {pmcid} node_index: {node_id}")
        try:
            record = tx.run(
                link_article,
                {"pmcid": pmcid, "node_id": node_id},
            ).single()

            if record is None:
                return None

            logger.debug(f"cypher response: {record}")
            return record["doc.pmcid"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", link_article, exception)
            raise
