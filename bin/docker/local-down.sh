#!/usr/bin/env bash
# ============================================================================
# Eugene Local Docker Stack - Shutdown Script
# ============================================================================
# Usage:
#   bin/docker/local-down.sh          # Stop services (keep data)
#   bin/docker/local-down.sh --reset  # Stop + delete Neo4j data
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [[ "${1:-}" == "--reset" ]]; then
    echo "Stopping services and removing volumes (Neo4j data will be deleted)..."
    docker compose down --volumes --remove-orphans
else
    echo "Stopping services (Neo4j data preserved in volumes)..."
    docker compose down --remove-orphans
fi

echo "Done."
