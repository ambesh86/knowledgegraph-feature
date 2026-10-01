from pydantic import BaseModel


class NameAndId(BaseModel):
    name: str
    id: str
