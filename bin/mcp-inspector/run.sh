#!/usr/bin/env bash

set -ou pipefail


# https://pubmed.mcp.claude.com/mcp
# https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com:8443/mcp

# allow connections to self signed certs
export NODE_TLS_REJECT_UNAUTHORIZED=0
npx @modelcontextprotocol/inspector 
