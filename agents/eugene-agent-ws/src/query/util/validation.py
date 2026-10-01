import logging
import os
import uuid

from query.model.chat_query_request import ChatQueryRequest

logger = logging.getLogger(__name__)

specials = ["%", "_", "$", ";", ":", "^", "*", "@"]


def validate_chat_query_request(chat_request: ChatQueryRequest) -> ChatQueryRequest:
    if chat_request is None:
        return chat_request

    # validate prompt
    prompt = chat_request.prompt
    if prompt is None:
        return chat_request

    prompt_len = len(prompt)
    # Configurable so deployments that attach document context (RAG/uploads) can
    # allow longer prompts. Default stays 2048 for backward compatibility.
    max = int(os.environ.get("EUGENE_MAX_PROMPT_CHARS", "2048"))
    if prompt_len > max:
        raise ValueError(
            f"Your prompt is too long. Prompt length: {prompt_len}, max: {max}"
        )

    if chat_request.conversation_id:
        ensure_valid_uuid_or_throw(chat_request.conversation_id)
    return chat_request


def validat_str(value: str) -> str:
    # these are regex like characters that do not show up in our prompt
    is_valid = not has_invalid_char(invalid_chars=specials, value=value)
    if not is_valid:
        raise ValueError(
            f"I'm unable to understand your query. Please rephrase your question using clear, well-formed language."
        )
    return value


def ensure_valid_uuid_or_throw(uuid_string):
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj) == uuid_string
    except ValueError:
        raise ValueError(f"Not recognized as a valid UUID value: {uuid_string}")


def has_invalid_char(value: str, invalid_chars: list[str] = specials) -> bool:
    if value is None:
        return False

    is_invalid = False
    for current in invalid_chars:
        if is_invalid:
            break
        if current in value:
            is_invalid = True
    return is_invalid
