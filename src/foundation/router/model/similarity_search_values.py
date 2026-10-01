from typing import Annotated
from pydantic import BaseModel, Field


class SimilaritySearchValues(BaseModel):
    values: list[Annotated[str, Field(None, examples=["Lupus"])]]
