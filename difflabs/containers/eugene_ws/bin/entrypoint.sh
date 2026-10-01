#!/usr/bin/env bash

set -euxo pipefail

download_env() {
    python src/fetch_secrets.py \
        && ls -alh .env
}

download_env \
    && uvicorn eugene_ws:app --app-dir src --host 0.0.0.0 --port 8000
