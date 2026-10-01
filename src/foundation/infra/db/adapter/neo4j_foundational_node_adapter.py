import logging
import re

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError
from numpy import ndarray
import pandas as pd

from foundation.infra.db.util.pagination import Pagination
from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection, get_or_default_ndarray

logger = logging.getLogger(__name__)

# Lucene query-syntax reserved characters (escaped/stripped when we build a
# fulltext query from free user text).
_LUCENE_SPECIAL = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/]')


def _to_fulltext_fuzzy_query(value: str) -> str:
    """Turn free text into a safe Lucene fuzzy query for the `entity_names`
    fulltext index: strip reserved chars, then append `~` (edit-distance) to
    each token so near-matches and typos still resolve. e.g.
    "folic acid deficiency" -> "folic~ acid~ deficiency~".
    """
    cleaned = _LUCENE_SPECIAL.sub(" ", value or "")
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return value or ""
    return " ".join(f"{t}~" for t in tokens)


def _to_fulltext_phrase_query(value: str) -> str:
    """Turn a node name into a Lucene *phrase* query for an exact-name lookup.

    The exact path used to pass the raw value straight to the fulltext index. Lucene
    reads unquoted text as an implicit OR across tokens, so a five-word disease name
    asks the index for every node matching *any* of those words. Measured here:

        superficial multifocal basal cell carcinoma   ->  5464 candidates, 1 exact
        the same text quoted as a phrase              ->     1 candidate,  1 exact

    Every one of those 5463 extra nodes is loaded and then discarded by the
    `toLower(n.node_name) = toLower($node_name)` filter downstream. Across 500 random
    real node names the old form scanned 2,859,357 candidates to return 500 rows. That
    fan-out is what made the endpoint heavy-tailed — ~20ms at the median but 14s at the
    observed worst (`/node/find/Liquid Alpha1-PI`, 2026-08-14) — and a caller with a
    short timeout does not merely wait, it gives up on entity linkage entirely.

    **Why the value is quoted rather than sanitised.** Inside a Lucene phrase, reserved
    characters are literal, so the only escaping needed is `\\` and `"` — and the
    phrase text then reaches the *same analyzer* that indexed the name, producing the
    *same tokens in the same order*. That parity is what makes this safe: any node whose
    name is equal to the query necessarily analyses to that token sequence, so the
    phrase cannot fail to return a row the equality filter would have kept.

    Stripping the reserved characters instead — which is what the fuzzy path does, and
    what this function did first — breaks that parity and silently loses matches. This
    index analyses `2-oxoglutarate:oxygen` into a token that keeps the colon, so a
    stripped query searched for `oxoglutarate` and `oxygen`, neither of which exists in
    the index, and `gibberellin A19, 2-oxoglutarate:oxygen oxidoreductase activity`
    stopped resolving. Phrase slop (`~2`, `~5`) does not recover it; nothing does,
    because the tokens differ in identity rather than position.
    """
    if not value:
        return ""
    # Backslash first: escaping it after the quote would double-escape the one we add.
    return '"{}"'.format(value.replace("\\", "\\\\").replace('"', '\\"'))


class Neo4jFoundationalNodeAdapter:
    """
    Adapter to perform operations on eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_node_id_by_node_name(
        self, value: str, fuzzy_match: bool = False
    ) -> pd.DataFrame | None:
        if value is None:
            return None
        ensure_connection(self.driver)
        return self._find_node_id_by_node_name(value=value, fuzzy_match=fuzzy_match)

    def verify_exists_by_node_index(self, label: str, node_index: str) -> bool:
        if label is None or node_index is None:
            return False

        ensure_connection(self.driver)
        return self._verify_exists_by_node_index(label, node_index)

    def find_by_label(
        self, label: str, page: int, page_size: int
    ) -> pd.DataFrame | None:
        ensure_connection(self.driver)
        return self._find_by_label(label, page, page_size)

    def find_all_by_label(self, label: str) -> pd.DataFrame | None:
        ensure_connection(self.driver)
        return self._find_all_by_label(label)

    def upsert_embeddings(
        self, label: str, node_index: str, embeddings: ndarray
    ) -> str | None:
        # Python driver: https://neo4j.com/docs/api/python-driver/current/index.html
        # Cypher syntax: https://neo4j.com/docs/cypher-manual/current/
        # Cypher cheatsheet https://neo4j.com/docs/cypher-cheat-sheet/
        if label is None or node_index is None or embeddings is None:
            return

        upsert_node_embeddings = (
            """
            MERGE (n:`%s` {
                node_index: $node_index
            })
            ON MATCH
                SET n.embeddings = $embeddings
            RETURN n.node_index
            """
            % f"{normalize_node_label(label)}"
        )
        logger.debug(f"upsert: {upsert_node_embeddings}")
        try:
            record = self.driver.execute_query(
                upsert_node_embeddings,
                {
                    "node_index": node_index,
                    "embeddings": get_or_default_ndarray(embeddings),
                },
                database_=self.database,
                result_transformer_=neo4j.Result.single,
            )

            if record is None:
                return None

            logger.debug(f"upsert response: {record}")
            return record["n.node_index"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", upsert_node_embeddings, exception)
            raise

    def _find_all_by_label(self, label: str) -> pd.DataFrame | None:
        query = self._build_find_all_by_label(label)
        logger.debug(f"find all: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.to_df,
            )
            logger.debug(f"cypher response: {records}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _find_by_label(
        self, label: str, page: int, page_size: int
    ) -> pd.DataFrame | None:
        query = self._build_find_by_label(label, page, page_size)
        logger.debug(f"find all: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.to_df,
            )
            logger.debug(f"cypher response: {records}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_find_all_by_label(self, label: str) -> str:
        lookup_node_query = """MATCH (n:`%s`)
                RETURN n.node_id as node_id, n.node_name as node_name
                ORDER BY n.node_name
            """ % (
            normalize_node_label(label),
        )
        return lookup_node_query

    def _build_find_by_label(self, label: str, page: int, page_size: int) -> str:
        limit, offset = Pagination.calculate_limit_and_offset(page, page_size)
        lookup_node_query = """MATCH (n:`%s`)
                RETURN n.node_id as node_id, n.node_name as node_name
                ORDER BY node_name
                SKIP %s
                LIMIT %s
            """ % (
            normalize_node_label(label),
            offset,
            limit,
        )
        return lookup_node_query

    def _verify_exists_by_node_index(self, label: str, node_index: str) -> bool:
        query = self.build_verify_exists_by_node_index(label=label)
        logger.debug(f"exists query: {query}")
        try:
            record = self.driver.execute_query(
                query_=query,
                parameters_={"node_index": node_index},
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {record}")
            if record is not None and record["n.node_index"] is not None:
                return True
            else:
                return False
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def build_verify_exists_by_node_index(self, label: str) -> str:
        lookup_node_query = (
            """MATCH (n: %s { node_index: $node_index })
            RETURN n.node_index
            """
            % (normalize_node_label(label)).strip()
        )
        return lookup_node_query

    def _find_node_id_by_node_name(
        self, value: str, fuzzy_match: bool = False
    ) -> pd.DataFrame | None:
        query = (
            self.build_find_node_id_by_node_name()
            if not fuzzy_match
            else self.build_fuzzy_find_node_id_by_node_name(value)
        )
        params = (
            # Two parameters, deliberately: the index is asked for a quoted phrase to
            # keep the candidate set small, while the equality filter still compares
            # against the caller's original text. Reusing one parameter for both would
            # test node names against a string containing quote marks.
            {"phrase_query": _to_fulltext_phrase_query(value), "node_name": value}
            if not fuzzy_match
            else {"fuzzy_query": _to_fulltext_fuzzy_query(value)}
        )
        logger.info(f"find node id query: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                parameters_=params,
                result_transformer_=neo4j.Result.to_df,
            )
            if records is None:
                return None
            logger.debug(f"cypher response: {records.shape}")
            return records
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def build_find_node_id_by_node_name(self) -> str:
        # Exact name lookup via the `entity_names` fulltext index — avoids a
        # label-less property match that the planner can only satisfy with a
        # full AllNodesScan over the whole graph.
        #
        # The index is queried with a quoted phrase ($phrase_query) rather than the raw
        # text, so a multi-word name does not fan out into an OR across its tokens; see
        # `_to_fulltext_phrase_query`. The equality filter below still compares against
        # the caller's original string ($node_name), so the result is unchanged — only
        # the number of candidates it had to be selected from.
        lookup_node_query = """CALL db.index.fulltext.queryNodes('entity_names', $phrase_query)
        YIELD node AS n, score
        WHERE (n.is_hidden IS NULL OR NOT n.is_hidden)
          AND toLower(n.node_name) = toLower($node_name)
        RETURN n.node_id, n.node_name
        ORDER BY score DESC
        """
        return lookup_node_query

    def build_fuzzy_find_node_id_by_node_name(self, value: str) -> str:
        # Fuzzy name lookup via the `entity_names` fulltext index (Lucene fuzzy
        # `~` per token). Replaces a case-insensitive regex (`=~ '(?i).*x.*'`)
        # that forced a full scan of all nodes — ~12s on the full graph, and
        # worst when there were few/no matches (nothing to satisfy the LIMIT).
        # The query string is passed as a parameter ($fuzzy_query) — see
        # `_find_node_id_by_node_name` — so `value` is no longer interpolated.
        lookup_node_query = """CALL db.index.fulltext.queryNodes('entity_names', $fuzzy_query)
        YIELD node AS n, score
        WHERE n.is_hidden IS NULL OR NOT n.is_hidden
        RETURN n.node_id, n.node_name
        ORDER BY score DESC
        LIMIT 25
        """
        return lookup_node_query
