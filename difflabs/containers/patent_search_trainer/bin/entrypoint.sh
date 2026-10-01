#!/usr/bin/env bash

set -euxo pipefail

download_env() {
    python src/fetch_secrets.py
    ls -alh .env 
}

download_env \
    && python src/train_for_search.py --dimension-size 768
