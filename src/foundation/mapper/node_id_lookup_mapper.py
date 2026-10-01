import logging
from typing import Tuple

from pandas import DataFrame

from annotation.timer_annotation import log_time
from foundation.model.id_and_value import IdAndValue
from foundation.model.node_id_lookup import NodeIdLookup


logger = logging.getLogger(__name__)


class NodeIdLookupMapper:
    """
    map responses for a node id lookup eugene query
    """

    @log_time
    def map(self, value: str, fuzzy_match: bool, df: DataFrame | None) -> NodeIdLookup:
        if df is None:
            return NodeIdLookup(
                query=value, count=0, fuzzy_match=fuzzy_match, results=()
            )
        results = self._map_response_rows(df)

        return NodeIdLookup(
            results=results, count=len(results), query=value, fuzzy_match=fuzzy_match
        )

    def _map_response_rows(self, df: DataFrame) -> Tuple[IdAndValue, ...]:
        if df is None:
            return None
        return tuple(df.apply(self._map_response_row, axis=1))

    def _map_response_row(self, row) -> IdAndValue | None:
        if row is None:
            return None
        return IdAndValue(
            id=row["n.node_id"],
            value=row["n.node_name"],
        )
