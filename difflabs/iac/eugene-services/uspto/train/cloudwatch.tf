resource "aws_cloudwatch_log_group" "training_service_log_group" {
  name = "${var.resource_prefix}-eugene-uspto-trainer"
  retention_in_days = 365
  tags = merge(var.base_tags, {
    Name =  "${var.resource_prefix}-eugene-uspto-trainer"
    workloadName = var.workload_name
  })
}