import logging

from pandas import DataFrame

from annotation.timer_annotation import log_time
from foundation.model.generic_node_details import GenericNodeDetails


logger = logging.getLogger(__name__)


class NodeDetailsMapper:
    """
    map responses for a generic set of eugene neo4j node properties, used for the ui details view
    """

    @log_time
    def map(self, df: DataFrame | None) -> list[GenericNodeDetails] | None:
        if df is None:
            return None

        return self._map_response_rows(df)

    def _map_response_rows(self, df: DataFrame) -> list[GenericNodeDetails]:
        if df is None:
            return None

        results = [
            el for el in df.apply(self._map_response_row, axis=1) if el is not None
        ]
        return results

    def _map_response_row(self, row) -> GenericNodeDetails | None:
        if row is None:
            return None
        return GenericNodeDetails(
            labels=row["labels"],
            id=row["id"],
            value=row["value"],
            source=row["source"],
            description=row["description"],
        )
