from pydantic import BaseModel


class ListResponse(BaseModel):
    count: int
    results: list[str]
