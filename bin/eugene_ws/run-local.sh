#!/usr/bin/env bash

set -ou pipefail

# be sure to be in the correct env
# source venv_eugene_ws

uvicorn eugene_ws:app 	\
	--app-dir src  	\
	--host 127.0.01 \
	--port 8000 	\
	--reload
