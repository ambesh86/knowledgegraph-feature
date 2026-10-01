from pydantic import BaseModel


class SimilarNodes(BaseModel):
    score: float
    id1: str
    name1: str
    id2: str
    name2: str


class SimilarityResponse(BaseModel):
    count: int
    results: list[SimilarNodes]
