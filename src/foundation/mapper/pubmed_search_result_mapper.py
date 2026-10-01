import logging

from pandas import DataFrame, Series

from foundation.model.pubmed.pubmed_search_result import PubmedSearchResult
from foundation.model.pubmed.pubmed_search_result_row import PubmedSearchResultRow
from foundation.model.pubmed.pubmed_and_gene_search_result import (
    PubmedAndGeneSearchResult,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class PubmedSearchResultMapper:

    @log_time
    def map_drug_response(
        self, search_id: str, dataframe: DataFrame
    ) -> PubmedSearchResult:
        if dataframe is None or len(dataframe) == 0:
            return PubmedSearchResult(search_id=search_id, count=0, results=[])

        drug_id = dataframe.iloc[0]["drug_id"]
        self._check_id_and_log(search_id=search_id, id=drug_id)

        results = [el for el in dataframe.apply(self._to_row, axis=1) if el is not None]
        return PubmedSearchResult(
            search_id=search_id, count=len(results), results=results
        )

    @log_time
    def map_clinicaltrail_response(
        self, search_id: str, dataframe: DataFrame
    ) -> PubmedSearchResult:
        if dataframe is None or len(dataframe) == 0:
            return PubmedSearchResult(search_id=search_id, count=0, results=[])

        nct_id = dataframe.iloc[0]["nct_id"]
        self._check_id_and_log(search_id=search_id, id=nct_id)

        results = [el for el in dataframe.apply(self._to_row, axis=1) if el is not None]
        return PubmedSearchResult(
            search_id=search_id, count=len(results), results=results
        )

    @log_time
    def map_gene_response(
        self, gene_protein: str, dataframe: DataFrame
    ) -> PubmedAndGeneSearchResult:
        if dataframe is None or len(dataframe) == 0:
            return PubmedAndGeneSearchResult(
                gene_protein=gene_protein, count=0, results=[]
            )

        value = dataframe.iloc[0]["node_name"]
        self._check_id_and_log(search_id=gene_protein, id=value)

        results = [el for el in dataframe.apply(self._to_row, axis=1) if el is not None]
        return PubmedAndGeneSearchResult(
            gene_protein=gene_protein, count=len(results), results=results
        )

    def _to_row(self, row: Series) -> PubmedSearchResultRow | None:
        key = "pmid"
        if row is None or key not in row or row[key] is None:
            return None
        id = str(row[key])
        return PubmedSearchResultRow(pmid=id)

    def _check_id_and_log(self, search_id: str, id: str) -> None:
        if id != search_id:
            logger.warning(
                f"search id is not the same as the id {id} returned from the db in the pubmed query results! This might be an issue!"
            )
