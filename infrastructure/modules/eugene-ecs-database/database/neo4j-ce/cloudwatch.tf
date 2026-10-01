resource "aws_cloudwatch_log_group" "eugene_database_service_log_group" {
  name = "${var.resource_prefix}-eugene-database"
  retention_in_days = 365

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-database"
    workloadName = var.workload_name
  })
}