from typing import Annotated
from pydantic import BaseModel, Field

from query.model.tool_request_enum import ToolRequestEnum


class ChatQueryRequest(BaseModel):
    prompt: Annotated[
        str,
        Field(
            None,
            examples=[
                "What assets does eugene know about companies with names like biogen"
            ],
        ),
    ]
    conversation_id: Annotated[
        str, Field(None, examples=["0872c36f-7efa-438e-ac3a-d76a96dc2ad1"])
    ]
    include_tools: Annotated[
        list[ToolRequestEnum],
        Field(None, examples=[["eugene", "http", "pubmed"]]),
    ]
