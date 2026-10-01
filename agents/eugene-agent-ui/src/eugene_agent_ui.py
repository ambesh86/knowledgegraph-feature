import asyncio
import logging
import os
from typing import AsyncGenerator
import httpx
import streamlit as st
from streamlit_pills import pills
import uuid

from conf.conf import api_endpoint_or_default, load_env

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


load_env()
api_endpoint = api_endpoint_or_default()


def build_main_header() -> None:
    # Set up the page
    st.title("Agentic Chat Interface")

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []


def build_sidebar() -> None:
    # Initialize session state for conversation ID
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())

    # Set the sidebar width in config (before any other st. commands)
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

    tool_options = ["eugene", "pubmed", "http"]
    # Sidebar
    with st.sidebar:
        st.header("Conversation Information")
        st.write(f"Conversation ID: `{st.session_state.conversation_id}`")
        if st.button("New Conversation"):
            st.session_state.conversation_id = str(uuid.uuid4())
            st.rerun()

        st.header("Agentic Datasources")
        selected_tools = []
        for tool in tool_options:
            default_value = tool == "eugene"
            is_checked = st.checkbox(tool, value=default_value, key=tool)
            if is_checked:
                selected_tools.append(tool)
        st.session_state.selected_tools = selected_tools

        st.header("Authentication")
        # Login URL is configurable so the same UI image works in local
        # Docker (http://localhost:18000/login) and in AWS (internal ALB).
        login_url = os.environ.get(
            "EUGENE_LOGIN_URL",
            "http://localhost:18000/login",
        )
        st.markdown(
            f'<a href="{login_url}" target="_blank">Get OAuth Token (opens in new tab)</a>',
            unsafe_allow_html=True,
        )
        oauth_token = st.text_input(
            "OAuth Access Token",
            type="password",
            placeholder="Paste your OAuth access token here",
            help="Enter your Bearer token for API authentication",
        )
        st.session_state.oauth_token = oauth_token

        if oauth_token:
            greet_prompt = "Greet the user by name using their identity"
            response = asyncio.run(
                display_streamed_response(api_endpoint, greet_prompt)
            )
            # if response:
            #     st.session_state.messages.append({"role": "assistant", "content": response})
            #     st.session_state.last_processed_selection = None


async def stream_response(
    api_endpoint: str,
    prompt: str,
    conversation_id: str,
    include_tools: list[str],
    oauth_token: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream response from API endpoint"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if oauth_token:
        headers["Authorization"] = f"Bearer {oauth_token}"

    async with httpx.AsyncClient(verify=False) as client:
        async with client.stream(
            "POST",
            api_endpoint,
            json={
                "prompt": prompt.strip(),
                "conversation_id": conversation_id,
                "include_tools": include_tools,
            },
            headers=headers,
            timeout=60 * 2,
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(
                    f"API request failed with status {response.status_code}: {error_text}"
                )

            # Stream the response line by line
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk


async def display_streamed_response(api_endpoint: str, prompt: str):
    """Display streamed response in Streamlit chat format"""
    full_response = ""

    # Create a chat message container for the assistant
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        try:
            async for chunk in stream_response(
                api_endpoint,
                prompt,
                st.session_state.conversation_id,
                st.session_state.selected_tools,
                st.session_state.get("oauth_token"),
            ):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")

            # Remove cursor and show final response
            message_placeholder.markdown(full_response)
            return full_response

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            message_placeholder.error(error_msg)
            return None


def display_message_history():
    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


if __name__ == "__main__":
    build_sidebar()
    build_main_header()
    display_message_history()

    default_msg = "What assets does Eugene know about companies with names like biogen."

    # Initialize last processed selection tracker
    if "last_processed_selection" not in st.session_state:
        st.session_state.last_processed_selection = None

    # Only show suggestion pills if no messages have been sent yet
    selected_suggestion = None
    # if len(st.session_state.messages) <= 1:
    # Suggestion pills
    suggestions = [
        # eugene questions
        "List drug aliases for Adderall",
        "Generate a table of drugs, diseases and clinical trial researched by Biogen Inc",
        default_msg,
        "Does Mycophenolate mofetil have any relationships to PTRH2? If so explain",
        # pubmed questions
        "What recent pubmed studies mention ABL1?",
        "What organizations are related to pmid 41402159?",
        "What facts does eugene know about Sickle cell anemia?",
    ]

    selected_suggestion = pills(
        "Try these suggestions:",
        suggestions,
        key="suggestion_pills",
        label_visibility="collapsed",
        index=None,
        clearable=True,
    )

    # Handle pill selection or chat input
    prompt = None

    # Always render chat input
    user_input = st.chat_input(default_msg)

    # Check for new pill selection (only if it hasn't been processed yet)
    if (
        selected_suggestion
        and selected_suggestion != st.session_state.last_processed_selection
    ):
        prompt = selected_suggestion
        st.session_state.last_processed_selection = selected_suggestion
    elif user_input:
        prompt = user_input
        st.session_state.last_processed_selection = None

    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get and display assistant response
        response = asyncio.run(display_streamed_response(api_endpoint, prompt))

        # Add assistant response to chat history
        if response:
            st.session_state.messages.append({"role": "assistant", "content": response})
