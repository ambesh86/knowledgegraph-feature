resource "aws_cloudwatch_log_group" "eugene_bastion_service_log_group" {
  name = "${var.resource_prefix}-eugene-bastion"
  retention_in_days = 365
  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-bastion"
    workloadName = var.workload_name
  })
}