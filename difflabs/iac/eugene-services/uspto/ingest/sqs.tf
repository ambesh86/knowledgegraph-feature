resource "aws_sqs_queue" "uspto_application_queue" {
  name                        = "${var.resource_prefix}-${var.sqs_uspto_application_queue_name}"
  delay_seconds               = 90
  message_retention_seconds    = 86400
  receive_wait_time_seconds   = 10

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-${var.sqs_uspto_application_queue_name}"
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
  }
}

resource "aws_sqs_queue" "uspto_pgpub_queue" {
  name                        = "${var.resource_prefix}-${var.sqs_uspto_pgpub_queue_name}"
  delay_seconds               = 90
  message_retention_seconds    = 86400
  receive_wait_time_seconds   = 10

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-${var.sqs_uspto_pgpub_queue_name}"
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
  }
}
