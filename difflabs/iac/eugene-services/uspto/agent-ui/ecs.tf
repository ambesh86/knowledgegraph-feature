# Create ECS task definition for web service
# WARN: if this is a private vpc you may need to setup endpoints
# TODO: setup endpoint automatically
# https://repost.aws/knowledge-center/ecs-fargate-pull-container-error
resource "aws_ecs_task_definition" "ui_agent_task" {
  family                = "${var.resource_prefix}-eugene-agent-ui-task"
  cpu                    = 1024
  memory                = 2048
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.uspto_ecs_task_execution_role_arn
  task_role_arn           = var.uspto_ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "agent_ui"
      image      = local.agent_ui_image
      cpu        = 1024
      memory    = 2048
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol       = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.agent_ui_log_group.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "date || exit 0"]
        interval = 90
        timeout = 5
        retries = 3
      }

      environment = [
      ]
    }
  ])

  tags = merge(var.base_tags, {
    Name                          = "${var.resource_prefix}-eugene-agent-ui-task"
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

resource "aws_ecs_service" "agent_ui" {
  name            = "${var.resource_prefix}-eugene-agent-ui"
  cluster         = var.ecs_uspto_cluster_name
  task_definition = aws_ecs_task_definition.ui_agent_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  # deployment_minimum_healthy_percent = 50
  force_new_deployment = true

  for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.eugene_agent_ui_container_sg.id]
    subnets          = toset([one([each.value])])
    assign_public_ip = false
  }

  wait_for_steady_state = true

  load_balancer {
    target_group_arn = "${aws_lb_target_group.eugene_agent_ui_alb_ip_target_group.arn}"
    container_name   = "agent_ui"
    container_port   = 8000
  }

  tags = merge(var.base_tags, {
    Name =  "${var.resource_prefix}-eugene-agent-ui"
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
