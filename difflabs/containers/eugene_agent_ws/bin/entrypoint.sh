#!/usr/bin/env bash

set -uxo pipefail

download_env() {
    python src/fetch_secrets.py                 \
        --secret-name "eugene/dev/agent_ws/env" \
        && ls -alh .env
}

download_env \
    && uvicorn eugene_chat_ws:app \
        --app-dir src             \
        --host 0.0.0.0            \
        --port 8000

