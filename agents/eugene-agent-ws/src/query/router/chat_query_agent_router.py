import logging
from time import perf_counter
from typing import Annotated, AsyncGenerator
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import AfterValidator

from annotation.timer_annotation import log_time
from router.auth.auth import get_current_token, get_current_user
from query.model.chat_query_request import ChatQueryRequest
from query.model.chat_query_response import ChatQueryResponse
from query.util.validation import validate_chat_query_request
from query.util.intent_classifier import classify_intent
from query.model.tool_request_enum import ToolRequestEnum
from query.conf.conf import eugene_data_agent
from query.util.response import unwrap_agent_result

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["query"],
)


eugene_agent = eugene_data_agent()


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    response_model_exclude_none=True,
)
async def chat_query_agent(
    chat_request: Annotated[
        ChatQueryRequest, AfterValidator(validate_chat_query_request)
    ],
    request: Request,
    token: str = Depends(get_current_token),
    user: dict = Depends(get_current_user),
):
    request_id = request.headers.get("x-request-id", "unavailable")[:128]
    started_at = perf_counter()
    try:
        logger.info(f"chat query user: {user["upn"]}")
        conversation_id = _manage_conversation_id(chat_request)
        logger.info(
            "query.stage=accepted request_id=%s conversation_id=%s source_count=%d",
            request_id,
            conversation_id,
            len(chat_request.include_tools or []),
        )
        # todo: audit log
        logger.info(
            f"chat query agent, conversation_id: {conversation_id} request: {chat_request}"
        )

        prompt = chat_request.prompt.strip()
        # Clarity gate: no source selected → ask the user to choose one.
        if not chat_request.include_tools:
            return ChatQueryResponse(
                prompt=chat_request.prompt,
                message=_clarity_message(prompt),
                conversation_id=conversation_id,
                is_complete=True,
            )
        tools = _add_default_tools(chat_request.include_tools)
        logger.info(
            "query.stage=agent_execute.start request_id=%s conversation_id=%s",
            request_id,
            conversation_id,
        )
        execute_started_at = perf_counter()
        response = eugene_agent.execute(
            token=token,
            user_prompt=prompt,
            conversation_id=chat_request.conversation_id,
            include_tools=tools,
        )
        logger.info(
            "query.stage=agent_execute.complete request_id=%s conversation_id=%s elapsed_ms=%.0f",
            request_id,
            conversation_id,
            (perf_counter() - execute_started_at) * 1000,
        )
        response_message = unwrap_agent_result(response)

        # # todo: audit log success
        response = ChatQueryResponse(
            prompt=chat_request.prompt,
            message=response_message,
            conversation_id=conversation_id,
            is_complete=True,
        )
        logger.info(f"{response}")
        logger.info(
            "query.stage=complete request_id=%s conversation_id=%s elapsed_ms=%.0f",
            request_id,
            conversation_id,
            (perf_counter() - started_at) * 1000,
        )
        return response
    except Exception:
        # todo: audit log error
        logger.exception(
            "query.stage=failed request_id=%s elapsed_ms=%.0f",
            request_id,
            (perf_counter() - started_at) * 1000,
        )
        raise


@router.post(
    "/query/stream",
    responses={
        200: {
            "content": {"text/event-stream": {}},
        }
    },
)
async def chat_query_agent_as_stream(
    chat_request: Annotated[
        ChatQueryRequest, AfterValidator(validate_chat_query_request)
    ],
    token: str = Depends(get_current_token),
    user: dict = Depends(get_current_user),
):
    try:
        logger.info(f"streaming chat query user: {user["upn"]}")
        logger.info(
            f"chat query agent request: {chat_request}"
        )
        content_type = "text/event-stream"
        return StreamingResponse(
            generate_chat_response(token, chat_request),
            media_type=content_type,
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as e:
        # todo: audit log error
        logger.warning(e)
        raise e


@log_time
async def generate_chat_response(
    token: str,
    chat_request: ChatQueryRequest,
) -> AsyncGenerator[str, None]:
    import json

    prompt = chat_request.prompt.strip()

    # Clarity gate: if the user selected NO data source, do not silently answer
    # from a default. Ask them to choose one (with an intent-based suggestion).
    if not chat_request.include_tools:
        conv = chat_request.conversation_id or ""
        logger.info("no datasource selected — emitting clarity prompt")
        yield json.dumps({"type": "session", "session_id": conv, "content": ""}) + "\n"
        yield json.dumps(
            {"type": "content", "content": _clarity_message(prompt), "session_id": conv},
            ensure_ascii=False,
        ) + "\n"
        yield json.dumps({"type": "done", "content": "", "session_id": conv}) + "\n"
        return

    user_selected = _add_default_tools(chat_request.include_tools)
    intent = classify_intent(prompt, user_selected)
    tools = intent.tools
    logger.info(
        f"intent: tools={[t.value for t in tools]} reason={intent.reason}"
    )
    async for chunk in eugene_agent.execute_stream(
        token=token,
        user_prompt=prompt,
        conversation_id=chat_request.conversation_id,
        include_tools=tools,
    ):
        # Preserve the full envelope (type, tool, tool_input, etc.) so the UI
        # can render tool-call traces and materialize a live context graph.
        # Use newline-delimited JSON — our UI streamParser splits on newlines.
        yield json.dumps(chunk, ensure_ascii=False, default=str) + "\n"

    logger.info(
        f"Completed streaming response for conversation {chat_request.conversation_id}"
    )


@log_time
def _manage_conversation_id(chat_query_request: ChatQueryRequest) -> uuid.UUID:
    is_in_conversation = (
        chat_query_request.conversation_id is not None
        and not chat_query_request.conversation_id == ""
    )
    conversation_id = (
        uuid.uuid4()
        if not is_in_conversation
        else uuid.UUID(chat_query_request.conversation_id)
    )
    return conversation_id


def _clarity_message(prompt: str) -> str:
    """Clarity-agent response shown when the user picked NO data source.

    We do not silently answer from a default source. Instead we ask the user to
    choose, and use the intent classifier to suggest the best-fit source for
    their question.
    """
    inferred = set(classify_intent(prompt, None).tools)
    if ToolRequestEnum.PUBMED in inferred:
        suggestion = "**PubMed** — your question mentions literature / papers"
    elif ToolRequestEnum.HTTP in inferred:
        suggestion = "**Web** — your question mentions the latest / web / patents"
    else:
        suggestion = "**Eugene KG** — this looks like a knowledge-graph question"
    return (
        "Before I answer, please choose a data source — none is selected yet. "
        "Tap one of the buttons below the message box and re-send your question:\n\n"
        "- **All Sources** — searches everything in order: the Eugene graph first, then "
        "ClinicalTrials.gov, then PubMed. Pick this if you're not sure.\n"
        "- **Eugene KG** — the internal CSL Behring knowledge graph "
        "(drugs, diseases, genes/proteins, clinical trials, patents, organizations).\n"
        "- **Web** — the live public internet (Google Patents, ClinicalTrials.gov, web pages).\n"
        "- **PubMed** — biomedical literature (PubMed / Europe PMC).\n\n"
        f"Suggested for this question: {suggestion}."
    )


def _add_default_tools(request_tools: list) -> list:
    default_tools = frozenset(
        {
            # ToolRequestEnum.BIORXIV,
            # ToolRequestEnum.CHEMBL,
            # ToolRequestEnum.CLINICAL_TRIALS,
            # ToolRequestEnum.PUBMED
        }
    )
    request = set(request_tools or [])
    return list(request.union(default_tools))
