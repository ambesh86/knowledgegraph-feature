from typing import Annotated
from pydantic import BaseModel, Field


class NodeDetailsRequest(BaseModel):
    ids: list[Annotated[str, Field(None, examples=["C031180", "DB00846", "DB00436"])]]
