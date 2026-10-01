#!/usr/bin/env bash

set -uxo pipefail

download_env() {
    python src/fetch_secrets.py                 \
        --secret-name "eugene/dev/eugene_mcp/env" \
        && ls -alh .env
}

download_env \
    && python src/eugene_mcp.py \
        --host 0.0.0.0


