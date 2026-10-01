locals {
  logs_bucket = "eugene-search-logs"
  current_aws_account_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/*"
  search_ws_image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/eugene/search_ws:${var.image_hash}"
}
