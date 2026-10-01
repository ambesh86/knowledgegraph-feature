resource "aws_cloudwatch_event_rule" "canaries_rule_1" {
  name                = "${var.resource_prefix}-eugene-canaries-rule-1"
  description         = "api canaries rule, will test the api endpoints and do a sanity check"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED" 


  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-canaries-rule-1"
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

resource "aws_cloudwatch_event_target" "canaries_event_ecs_target" {
  arn      = var.ecs_uspto_cluster_arn
  rule     = aws_cloudwatch_event_rule.canaries_rule_1.name
  role_arn = var.uspto_event_bridge_role_arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.api_canaries_task.arn
    network_configuration {
      subnets         = toset([for s in data.aws_subnet.uspto_subnets : s.id])
      security_groups = [aws_security_group.eugene_canaries_container_sg.id]
    }
    launch_type = "FARGATE"
  }
}