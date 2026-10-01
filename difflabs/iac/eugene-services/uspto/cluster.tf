resource "aws_ecs_cluster" "uspto_cluster" {
  name = "${var.resource_prefix}-${var.ecs_uspto_cluster_name}"

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-${var.ecs_uspto_cluster_name}"
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    costCenter                    = var.cost_center
    businessUnit                  = var.business_unit
    dataClassification            = var.data_classification
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsManaged                    = var.ams_managed
    costBudgetAmount              = var.cost_budget_amount
    patchSchedule                 = var.patch_schedule
    accountType                   = var.account_type
  })
}
