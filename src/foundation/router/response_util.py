import logging

import pandas as pd

from foundation.router.model.list_response import ListResponse
from foundation.router.model.name_and_id import NameAndId
from foundation.router.model.name_id_list_response import NameAndIdListResponse
from foundation.router.model.similarity_response import SimilarNodes, SimilarityResponse

logger = logging.getLogger(__name__)


def to_list_response(
    dataframe: pd.DataFrame | None,
) -> ListResponse:
    if dataframe is None:
        return ListResponse(count=0, results=[])

    results = [el for el in dataframe["n.node_name"].tolist() if el is not None]
    results.sort()
    return ListResponse(count=len(results), results=results)


def to_id_list_response(
    dataframe: pd.DataFrame | None,
) -> NameAndIdListResponse:
    if dataframe is None or len(dataframe) == 0:
        return NameAndIdListResponse(count=0, results=[])

    results = [el for el in dataframe.apply(_to_name_and_id, axis=1) if el is not None]
    return NameAndIdListResponse(count=len(results), results=results)


def _to_name_and_id(row: pd.Series) -> NameAndId | None:
    name_key = "node_name"
    id_key = "node_id"
    if row is None or name_key not in row or row[name_key] is None:
        return None
    return NameAndId(name=row[name_key], id=row[id_key])


def to_similarity_response(
    dataframe: pd.DataFrame | None,
) -> SimilarityResponse:
    if dataframe is None:
        return SimilarityResponse(count=0, results=[])

    results = []
    for index, row in dataframe.iterrows():
        row = SimilarNodes(
            score=row["similarity"],
            id1=row["id1"],
            id2=row["id2"],
            name1=row["name1"],
            name2=row["name2"],
        )
        results.append(row)

    return SimilarityResponse(count=len(results), results=results)
