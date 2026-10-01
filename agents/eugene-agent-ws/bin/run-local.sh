#!/usr/bin/env bash

set -ou pipefail

# be sure to source the correct venv
# source .venv/bin/activate

uvicorn eugene_chat_ws:app \
    	--app-dir src       \
    	--host 127.0.0.1    \
    	--port 8000		\
	--reload
