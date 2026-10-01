#!/usr/bin/env bash

set -eou pipefail
set -x

script_dir=$(dirname "$0")
source "${script_dir}/env.sh"


platform="linux/amd64"


containers_root=difflabs/containers

docker build -f "${containers_root}"/eugene_mcp/Dockerfile . -t "${ecr_namespace}/eugene_mcp" --platform "${platform}"
docker build -f "${containers_root}"/eugene_api_canaries/Dockerfile . -t "${ecr_namespace}/api_canaries" --platform "${platform}"
docker build -f "${containers_root}"/eugene_ws/Dockerfile . -t "${ecr_namespace}/search_ws" --platform "${platform}"
docker build -f "${containers_root}"/eugene_agent_ws/Dockerfile . -t "${ecr_namespace}/agent_ws" --platform "${platform}"
docker build -f "${containers_root}"/eugene_agent_ui/Dockerfile . -t "${ecr_namespace}/agent_ui" --platform "${platform}"

# docker build -f "${containers_root}"/patent_search_trainer/Dockerfile . -t "${ecr_namespace}/patent_search_trainer" --platform "${platform}"
# docker build -f "${containers_root}"/eugene_neo4j_ce/Dockerfile . -t "${ecr_namespace}/neo4j_ce" --platform "${platform}"
# docker build -f "${containers_root}"/eugene_bastion/Dockerfile . -t "${ecr_namespace}/bastion" --platform "${platform}"
