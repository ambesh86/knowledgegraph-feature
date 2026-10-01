locals {
  logs_bucket = "eugene-agent-logs"
  current_aws_account_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/*"
  agent_ws_image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/eugene/agent_ws:latest"
}
