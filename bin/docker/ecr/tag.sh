#!/usr/bin/env bash

set -eou pipefail
set -x

script_dir=$(dirname "$0")
source "${script_dir}/env.sh"


function fetch_tag {
	local image_name=$1
	echo $(docker images "${image_name}" -q | head -1)
}


function tag_image {
	local aws_acct=$1
	local aws_region=$2
	local ecr_repo=$3
	local image_id=$4
	local tag=$5
	$(docker tag "${image_id}" "${aws_acct}.dkr.ecr.${aws_region}.amazonaws.com/${ecr_repo}:${tag}")
}

#trainer_id=${1:-"latest"}
#search_ws_id=${2:-"latest"}
#neo4j_ce_id=${3:-"latest"}
#bastion_id=${4:-"latest"}
#api_canaries_id=${5:-"latest"}


eugene_mcp_id=$(fetch_tag "${ecr_namespace}/eugene_mcp")
api_canaries_id=$(fetch_tag "${ecr_namespace}/api_canaries")
search_ws_id=$(fetch_tag "${ecr_namespace}/search_ws")
agent_ws_id=$(fetch_tag "${ecr_namespace}/agent_ws")
agent_ui_id=$(fetch_tag "${ecr_namespace}/agent_ui")

# trainer_id=$(fetch_tag "${ecr_namespace}/patent_search_trainer")
# neo4j_ce_id=$(fetch_tag "${ecr_namespace}/neo4j_ce")
# bastion_id=$(fetch_tag "${ecr_namespace}/bastion")
echo "pass in trainer, search, and database image ids"


tag_image $aws_acct $aws_region "${ecr_namespace}/eugene_mcp" "${eugene_mcp_id}" $tag
tag_image $aws_acct $aws_region "${ecr_namespace}/api_canaries" "${api_canaries_id}" $tag
tag_image $aws_acct $aws_region "${ecr_namespace}/search_ws" "${search_ws_id}" $tag
tag_image $aws_acct $aws_region "${ecr_namespace}/agent_ws" "${agent_ws_id}" $tag
tag_image $aws_acct $aws_region "${ecr_namespace}/agent_ui" "${agent_ui_id}" $tag

# tag_image $aws_acct $aws_region "${ecr_namespace}/patent_search_trainer" "${trainer_id}" $tag
# tag_image $aws_acct $aws_region "${ecr_namespace}/neo4j_ce" "${neo4j_ce_id}" $tag
# tag_image $aws_acct $aws_region "${ecr_namespace}/bastion" "${bastion_id}" $tag
