from uuid import UUID
from pydantic import BaseModel


class ChatQueryResponse(BaseModel):
    prompt: str
    message: str
    conversation_id: UUID
    is_complete: bool

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "What assets does eugene know about companies with names like biogen",
                "message": "Eugene knows about 450 assets for biogen across 202 unique clinical trials",
                "conversation_id": "0872c36f-7efa-438e-ac3a-d76a96dc2ad1",
                "is_complete": "true",
            }
        }
