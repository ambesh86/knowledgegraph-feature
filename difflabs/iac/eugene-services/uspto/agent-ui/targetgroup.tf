resource "aws_lb_target_group" "eugene_agent_ui_alb_ip_target_group" {
  name        = "${var.resource_prefix}-eugene-agent-ui-lb-tg"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    interval            = 30
    path                = "/"
    port                = "8000"
    protocol            = "HTTP"
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-agent-ui-lb-tg"
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
