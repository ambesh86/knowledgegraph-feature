from pydantic import BaseModel


class GenericListResponse(BaseModel):
    count: int
    results: list[dict]
