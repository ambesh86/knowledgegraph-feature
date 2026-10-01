#!/usr/bin/env bash
# ============================================================================
# Eugene Local Docker Stack - Startup Script
# ============================================================================
# Usage:
#   bin/docker/local-up.sh          # Start all services
#   bin/docker/local-up.sh --build  # Rebuild and start
#   bin/docker/local-up.sh --detach # Start in background
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Check for docker.env
if [ ! -f "docker.env" ]; then
    echo ""
    echo "=========================================="
    echo "  docker.env not found!"
    echo "=========================================="
    echo ""
    echo "  Run these commands first:"
    echo ""
    echo "    cp docker.env.template docker.env"
    echo "    # Then edit docker.env with your credentials"
    echo ""
    echo "  The chat agent defaults to Bedrock Nova Lite."
    echo "  Configure AWS credentials and AWS_REGION (prefer an IAM role)."
    echo "  API keys are only needed for an explicitly selected fallback provider."
    echo ""
    echo "=========================================="
    echo ""

    read -p "Create docker.env from template now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp docker.env.template docker.env
        echo "Created docker.env — edit it with your credentials, then re-run this script."
        exit 0
    else
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "  Starting Eugene Local Stack"
echo "=========================================="
echo ""
echo "  Services:"
echo "    Neo4j Browser:    http://localhost:7474"
echo "    Core API Swagger: http://localhost:8000/docs"
echo "    Core API Login:   http://localhost:8000/login"
echo "    Agent API:        http://localhost:8001/docs"
echo "    Chat UI:          http://localhost:8501"
echo ""
echo "=========================================="
echo ""

# Parse arguments
BUILD_FLAG=""
DETACH_FLAG=""
for arg in "$@"; do
    case $arg in
        --build) BUILD_FLAG="--build" ;;
        --detach|-d) DETACH_FLAG="-d" ;;
    esac
done

docker compose up $BUILD_FLAG $DETACH_FLAG --remove-orphans

