#!/usr/bin/env bash

set -ou pipefail

# source the correct venv
#  source .venv/bin/activate

# uvicorn eugene_mcp:app --app-dir src --host 0.0.0.0 --port 8000 --reload
uv --directory $PWD/src run eugene_mcp.py --port 8001
