#!/usr/bin/env bash

set -eou pipefail
set -x

script_dir=$(dirname "$0")
source "${script_dir}/env.sh"


# WARN: before running this command, manually create the private repo in ECR
# see the containers terraform folder

function push_image {
	local aws_acct=$1
	local aws_region=$2
	local ecr_repo=$3
	local tag=$4
	docker push "${aws_acct}.dkr.ecr.${aws_region}.amazonaws.com/${ecr_repo}:${tag}"
}

push_image $aws_acct $aws_region "${ecr_namespace}/eugene_mcp" $tag
push_image $aws_acct $aws_region "${ecr_namespace}/api_canaries" $tag
push_image $aws_acct $aws_region "${ecr_namespace}/search_ws" $tag
push_image $aws_acct $aws_region "${ecr_namespace}/agent_ws" $tag
push_image $aws_acct $aws_region "${ecr_namespace}/agent_ui" $tag

# push_image $aws_acct $aws_region "${ecr_namespace}/patent_search_trainer" $tag
# push_image $aws_acct $aws_region "${ecr_namespace}/neo4j_ce" $tag
# push_image $aws_acct $aws_region "${ecr_namespace}/bastion" $tag
