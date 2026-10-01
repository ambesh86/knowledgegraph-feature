resource "aws_cloudwatch_log_group" "search_web_service_log_group" {
  name = "${var.resource_prefix}-eugene-uspto-search"
  retention_in_days = 365
  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-uspto-search"
    workloadName = var.workload_name
  })
}