from pydantic import BaseModel

from foundation.router.model.name_and_id import NameAndId


class NameAndIdListResponse(BaseModel):
    count: int
    results: list[NameAndId]
