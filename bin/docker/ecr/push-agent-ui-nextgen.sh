#!/usr/bin/env bash
# =============================================================================
# Build + push ONLY the Next.js "nextgen" agent UI to ECR.
# =============================================================================
# Self-contained (does not touch the multi-image build/tag/push scripts).
# Builds linux/amd64 (Fargate), tags :latest, pushes to eugene/agent_ui_nextgen.
#
# USAGE
#   AWS_PROFILE=eugene-deploy bin/docker/ecr/push-agent-ui-nextgen.sh [tag]
#
#   bin/docker/ecr/push-agent-ui-nextgen.sh            # tag = latest
#   bin/docker/ecr/push-agent-ui-nextgen.sh sha-abc123 # explicit tag
#
# PREREQS
#   - Docker running
#   - AWS creds valid (aws sts get-caller-identity must succeed)
# =============================================================================
set -Eeuo pipefail
set -x

script_dir=$(dirname "$0")
source "${script_dir}/env.sh"   # provides aws_acct, aws_region, ecr_namespace, tag

# allow tag override from arg 1
tag="${1:-${tag}}"

repo="${ecr_namespace}/agent_ui_nextgen"
registry="${aws_acct}.dkr.ecr.${aws_region}.amazonaws.com"
remote="${registry}/${repo}:${tag}"
platform="linux/amd64"

# ALB path prefix the app is served under. Must match the ALB listener rule
# (default /nextgen/*) and the target-group health-check path (/nextgen).
# Set NEXT_BASE_PATH="" to serve at root.
next_base_path="${NEXT_BASE_PATH-/nextgen}"

# repo root = two levels up from bin/docker/ecr
repo_root=$(cd "${script_dir}/../../.." && pwd)
dockerfile="${repo_root}/docker/eugene_agent_ui_next/Dockerfile"

# 1. ensure the ECR repository exists
aws ecr describe-repositories --repository-names "${repo}" --region "${aws_region}" >/dev/null 2>&1 \
  || aws ecr create-repository \
       --repository-name "${repo}" \
       --image-scanning-configuration scanOnPush=true \
       --region "${aws_region}" >/dev/null

# 2. docker login to ECR
aws ecr get-login-password --region "${aws_region}" \
  | docker login --username AWS --password-stdin "${registry}"

# 3. build (context = repo root; Dockerfile COPYs agents/eugene-agent-ui-next/)
docker build --platform "${platform}" \
  --build-arg "NEXT_BASE_PATH=${next_base_path}" \
  -f "${dockerfile}" "${repo_root}" -t "${repo}:${tag}"

# 4. tag + push
docker tag "${repo}:${tag}" "${remote}"
docker push "${remote}"

set +x
echo ""
echo "Pushed: ${remote}"
