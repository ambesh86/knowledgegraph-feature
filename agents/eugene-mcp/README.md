# EUGENE Model Context Protocol Webservice

Model Context Protocol (MCP) server to wrap Eugene webservice calls and other chat interactions


## To Run

`uv --directory $PWD/src run eugene_mcp.py`

## To Lint

`uv run black src`

## To Debug

To debug the MCP server you can start a local mcp inspector

```
#!/usr/bin/env bash

set -ou pipefail

export NODE_TLS_REJECT_UNAUTHORIZED=0
npx @modelcontextprotocol/inspector 
```

Change the URL to something like `https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com:8443/mcp`

