#!/usr/bin/env bash

set -xou pipefail

force_deployment() {
    # Check if service name was provided
    if [ $# -eq 0 ]; then
        echo "Error: No service name provided"
        return 1
    fi

    local cluster_name=stage-eugene-uspto-cluster
    local service_name=$1
    aws ecs update-service --cluster "${cluster_name}" --service "${service_name}" --force-new-deployment
}


# services=("stage-eugene-search-ws" "stage-eugene-api-canaries" "stage-eugene-mcp-ws" "stage-eugene-agent-ws" "stage-eugene-agent-ui")
# services=("stage-eugene-search-ws" "stage-eugene-mcp-ws" "stage-eugene-agent-ws")
services=("stage-eugene-agent-ui")

for service in "${services[@]}"; do
	echo "redeploy service: $service"
	force_deployment $service
done

