#!/usr/bin/env bash
# =============================================================================
# Eugene UI — re-deploy a new image to the running EC2 without `terraform apply`
# =============================================================================
# Pulls a new tag of the eugene-agent-ui-next image and restarts the
# systemd service on the EC2 provisioned by infrastructure/environments/ui-only-ec2.
#
# REQUIRES
#   - aws CLI logged in with SSM Session Manager permission on the target EC2.
#   - The Session Manager plugin installed (`session-manager-plugin --version`).
#
# USAGE
#   bin/redeploy_ui.sh <instance-id> <image-tag>
#
#   bin/redeploy_ui.sh i-0abcdef1234567890 sha-abc1234
#   bin/redeploy_ui.sh i-0abcdef1234567890 latest
#
# OPTIONAL ENV
#   AWS_REGION   default: us-east-1
#   IMAGE_REPO   default: ghcr.io/aisemanticexpert/eugene-agent-ui-next
# =============================================================================

set -Eeuo pipefail

INSTANCE_ID="${1:-}"
IMAGE_TAG="${2:-latest}"
AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/aisemanticexpert/eugene-agent-ui-next}"

if [[ -z "$INSTANCE_ID" ]]; then
  echo "usage: $0 <instance-id> [image-tag]" >&2
  exit 2
fi

IMAGE="$IMAGE_REPO:$IMAGE_TAG"
echo "Re-deploying $IMAGE on $INSTANCE_ID ($AWS_REGION)"

# Pre-flight: confirm the instance is reachable via SSM
aws ssm describe-instance-information \
  --region "$AWS_REGION" \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --query 'InstanceInformationList[0].PingStatus' \
  --output text | grep -q Online || {
    echo "Instance $INSTANCE_ID is not reachable via SSM (not Online)" >&2
    exit 1
  }

# Build the remote command. We rewrite the systemd unit's image and bounce it.
read -r -d '' REMOTE_CMD <<EOF || true
set -Eeuo pipefail
echo ">> updating image to $IMAGE"
sudo sed -i 's|ExecStartPre=/usr/bin/docker pull .*|ExecStartPre=/usr/bin/docker pull $IMAGE|' /etc/systemd/system/eugene-ui.service
sudo sed -i 's|$IMAGE_REPO:[a-zA-Z0-9_.-]*|$IMAGE|g' /etc/systemd/system/eugene-ui.service
sudo systemctl daemon-reload
sudo systemctl restart eugene-ui.service
sleep 3
sudo systemctl status eugene-ui.service --no-pager | head -20
echo ">> image now running:"
sudo docker ps --filter name=eugene-ui --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
EOF

COMMAND_ID=$(aws ssm send-command \
  --region "$AWS_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"$(printf %s "$REMOTE_CMD" | sed 's/"/\\"/g')\"]" \
  --query 'Command.CommandId' --output text)

echo "Submitted SSM command $COMMAND_ID, waiting for completion ..."
aws ssm wait command-executed --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" --region "$AWS_REGION"

echo ""
echo "----- stdout -----"
aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
  --region "$AWS_REGION" --query StandardOutputContent --output text
echo ""
echo "----- stderr -----"
aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
  --region "$AWS_REGION" --query StandardErrorContent --output text

echo ""
echo "Done. Confirm the UI loads in your browser."
