locals {
  logs_bucket = "eugene-api-canaries-logs"
  current_aws_account_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/*"
  api_canaries_image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/eugene/api_canaries:latest"

  metrics_namespace = "CSL/euGENE"
  successful_metric_name = "SuccessfulCanaries"
  unsuccessful_metric_name = "UnsuccessfulCanaries"
}
