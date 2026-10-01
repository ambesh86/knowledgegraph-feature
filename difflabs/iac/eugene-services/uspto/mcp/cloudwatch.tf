resource "aws_cloudwatch_log_group" "search_web_service_log_group" {
  name = "${var.resource_prefix}-eugene-mcp-log-group"
  retention_in_days = 365
  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-mcp-log-group"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  })
}