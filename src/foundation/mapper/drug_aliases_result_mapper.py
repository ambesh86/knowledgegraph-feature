import logging

from pandas import DataFrame, Series

from foundation.model.drug.drug_alias_search_result import DrugAliasSearchResult
from foundation.model.drug.drug_result_element import DrugResultElement
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class DrugAliasesResultMapper:
    """
    map responses from a drug alias eugene query
    """

    @log_time
    def map(
        self, drug_search: str, df: DataFrame | None
    ) -> DrugAliasSearchResult | None:
        if df is None:
            return None

        logger.info(f"mapping dataframe: {df.shape}")
        results = self._build_rows(df)
        return DrugAliasSearchResult(
            drug=drug_search, count=len(results), results=results
        )

    def _build_rows(self, df: DataFrame) -> list[DrugResultElement]:
        logger.info("building results...")
        return [el for el in df.apply(self._map_element, axis=1)]

    def _map_element(self, row: Series) -> DrugResultElement:
        return DrugResultElement(
            id=row["node_id"], name=row["name"], is_canonical=row["is_canonical"]
        )
