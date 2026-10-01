#!/usr/bin/env bash

set -uxo pipefail

download_env() {
    python src/fetch_secrets.py                 \
        --secret-name "eugene/dev/agent_ui/env" \
        && ls -alh .env
}

download_env \
    && streamlit run src/eugene_agent_ui.py \
    --server.address=0.0.0.0                \
    --server.port=8000
    # --server.baseUrlPath=/agent-ui          \
    # --server.enableCORS=false
